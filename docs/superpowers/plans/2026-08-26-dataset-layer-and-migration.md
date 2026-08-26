# Atlas Eval Harness — Dataset Layer and Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the offline half of the Atlas Eval Harness — frozen question banks, deterministic scoring, run records, migration of the existing audit history, and the SME spreadsheet round trip — so a reviewer can be handed a spreadsheet and their verdicts imported as tracked git diffs.

**Architecture:** Typed models (pydantic v2) describe banks and run records. `dataset.py` loads and hashes banks and resolves run order; `scoring.py` does literal, non-semantic matching and never calls a model; `review.py` round-trips an xlsx; `runs.py` writes the uniform run record and regenerates the flat rollup. Adapters are out of scope for this plan, so nothing here touches the network.

**Tech Stack:** Python 3.11+, pydantic v2, ruamel.yaml (round-trip YAML editing preserving formatting), openpyxl, pytest, playwright (spike only).

## Global Constraints

- **Ground truth is the thing AI may not validate.** The question and answer sets were AI-assisted, so `verification.status: verified` requires a human SME. Grading is unaffected: the existing process, where an LLM drafts rubric scores against the answer key and a human reviews them, continues. Every rubric records `scored_by` and `confirmed_by` so a report can be restricted to human-confirmed rows.
- **`atlas_eval/scoring.py` itself stays model-free.** It computes deterministic checks and defines the `Rubric` datatype; it does not call a model. LLM drafting happens in the audit workflow that fills rubric values, not inside the scorer, so the deterministic layer cannot drift.
- **Matching is literal.** Case-insensitive, whitespace-normalized substring matching. No semantic similarity, no stemming, no fuzzy matching. A scorer whose behavior can shift silently rewrites history.
- **`question_sha256` covers only `(id, text)` pairs**, sorted by id so it is independent of file position. Ground truth and checks stay editable after freezing.
- **Import never writes `ground_truth`.** Reviewer corrections land in `verification.notes` only.
- **Rubric column order in the rollup is fixed** and must match the legacy file exactly: `run_finished,agent,agent_id,bank_version,question_id,type,citations,correctness,gap_honesty,scope_discipline,clarity,total,conversation_id,notes`. New columns append after `notes`.
- **Rubric dimensions are exactly:** `citations`, `correctness`, `gap_honesty`, `scope_discipline`, `clarity`, each 0-2, `total` 0-10.
- Source material to migrate lives at `/Users/michaelangeli/projects/aws_transform_output/quick_chat_audits/`. Never modify anything under that path; read only.
- The 916 MB `SharePoint - Current System Documentation`, `Tech Specs`, `Product Briefs`, and `v5_reference` must never enter git.

---

### Task 1: Project scaffolding and typed models

**Files:**
- Create: `pyproject.toml`
- Create: `atlas_eval/__init__.py`
- Create: `atlas_eval/models.py`
- Create: `.gitignore`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `QuestionType`, `Stance`, `VerificationStatus` (str enums); `Checks`, `Verification`, `Question`, `Bank` (pydantic `BaseModel`). Field names and defaults exactly as written in Step 3 — every later task depends on them.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
import pytest
from pydantic import ValidationError

from atlas_eval.models import (
    Bank, Checks, Question, QuestionType, Stance, Verification, VerificationStatus,
)


def _q(**over):
    base = dict(
        id="v1-Q1",
        text="How does the weekly certification batch process flow?",
        type=QuestionType.RETRIEVAL,
        expected_stance=Stance.ANSWER,
        ground_truth="End-to-end flow across jobs and programs.",
    )
    base.update(over)
    return Question(**base)


def test_question_defaults_are_empty_not_shared():
    a, b = _q(), _q(id="v1-Q2")
    a.checks.forbidden.append("ETA-227")
    assert b.checks.forbidden == [], "default lists must not be shared between instances"
    assert a.verification.status is VerificationStatus.UNVERIFIED
    assert a.verification.verified_by is None
    assert a.after is None
    assert a.type_note is None


def test_question_rejects_unknown_type():
    with pytest.raises(ValidationError):
        _q(type="retrieval (multi-hop chain)")


def test_question_rejects_unknown_field():
    with pytest.raises(ValidationError):
        _q(expected_stace=Stance.ANSWER)


def test_all_thirteen_types_and_four_stances_exist():
    assert {t.value for t in QuestionType} == {
        "retrieval", "rule_logic", "data_flow", "gap_probe", "hallucination_bait",
        "absence_probe", "term_redirect", "acronym_check", "scope_boundary",
        "out_of_kb", "cross_space", "generation_probe", "handoff_probe",
    }
    assert {s.value for s in Stance} == {"answer", "hedge", "refuse", "redirect"}
    assert {v.value for v in VerificationStatus} == {
        "unverified", "verified", "rejected", "needs-sme",
    }


def test_bank_holds_questions_and_optional_freeze():
    bank = Bank(
        version="v1", agent="engineering_onboarding_specialist",
        corpus="quick_space_ca7_daily_s3", questions=[_q()],
    )
    assert bank.frozen_on is None and bank.question_sha256 is None
    assert bank.questions[0].id == "v1-Q1"


def test_checks_accept_all_four_lists():
    c = Checks(required_all=["ACP"], required_any=["Accelerated Collection Process"],
               forbidden=["ETA-227"], expect_citations=["UIMB0730"])
    assert c.expect_citations == ["UIMB0730"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas_eval'`

- [ ] **Step 3: Write the implementation**

```toml
# pyproject.toml
[project]
name = "atlas-eval"
version = "0.1.0"
description = "Auditing harness for NJDOL Atlas chat agents"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.6",
    "ruamel.yaml>=0.18",
    "openpyxl>=3.1",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "playwright>=1.44"]

[project.scripts]
atlas-eval = "atlas_eval.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

```python
# atlas_eval/__init__.py
"""Auditing harness for the NJDOL Atlas chat agents."""

__all__ = ["models"]
```

```python
# atlas_eval/models.py
"""Typed models for question banks and their verification state.

Field names here are load-bearing: they are the YAML keys in data/banks/*.yaml
and the column sources for the SME review spreadsheet.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class QuestionType(str, Enum):
    """Controlled vocabulary so scores aggregate by type.

    The legacy banks used free text and drifted to 30 distinct strings; the
    original label is preserved verbatim in Question.type_note.
    """

    RETRIEVAL = "retrieval"
    RULE_LOGIC = "rule_logic"
    DATA_FLOW = "data_flow"
    GAP_PROBE = "gap_probe"
    HALLUCINATION_BAIT = "hallucination_bait"
    ABSENCE_PROBE = "absence_probe"
    TERM_REDIRECT = "term_redirect"
    ACRONYM_CHECK = "acronym_check"
    SCOPE_BOUNDARY = "scope_boundary"
    OUT_OF_KB = "out_of_kb"
    CROSS_SPACE = "cross_space"
    GENERATION_PROBE = "generation_probe"
    HANDOFF_PROBE = "handoff_probe"


class Stance(str, Enum):
    """Coarse behavioural expectation, independent of content correctness."""

    ANSWER = "answer"
    HEDGE = "hedge"
    REFUSE = "refuse"
    REDIRECT = "redirect"


class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    REJECTED = "rejected"
    NEEDS_SME = "needs-sme"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False)


class Checks(_Strict):
    """Deterministic, literal match targets. Empty lists mean "no check"."""

    required_all: list[str] = Field(default_factory=list)
    required_any: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    expect_citations: list[str] = Field(default_factory=list)


class Verification(_Strict):
    status: VerificationStatus = VerificationStatus.UNVERIFIED
    verified_by: str | None = None
    verified_on: date | None = None
    notes: str | None = None


class Question(_Strict):
    id: str
    text: str
    type: QuestionType
    type_note: str | None = None
    provenance: str | None = None
    expected_stance: Stance
    ground_truth: str
    partial_credit: str | None = None
    after: str | None = None
    checks: Checks = Field(default_factory=Checks)
    verification: Verification = Field(default_factory=Verification)


class Bank(_Strict):
    version: str
    frozen_on: date | None = None
    question_sha256: str | None = None
    agent: str
    corpus: str
    sourcing: str | None = None
    questions: list[Question] = Field(default_factory=list)
```

```
# .gitignore
__pycache__/
*.py[cod]
.venv/
venv/
*.egg-info/
.pytest_cache/
.DS_Store
# Playwright session state — contains SSO tokens, never commit
.auth/
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pip install -e '.[dev]' && python -m pytest tests/test_models.py -v`
Expected: PASS, 5 passed

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore atlas_eval/ tests/test_models.py
git commit -m "feat: add typed models for question banks and verification state"
```

---

### Task 2: Playwright reconnaissance spike

De-risks the transport before any runner code assumes a DOM shape. This task is a spike: its deliverable is committed fixtures and a findings note, not production code, so it has no red/green cycle.

**Files:**
- Create: `tools/recon_quick_dom.py`
- Create: `docs/recon/2026-08-26-quick-chat-dom.md`
- Create: `tests/fixtures/quick/README.md`
- Create (captured, not authored): `tests/fixtures/quick/conversation_complete.html`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `tests/fixtures/quick/conversation_complete.html` (saved DOM of one finished multi-question conversation) and a findings note naming the selectors. Plan 2's Playwright tasks consume both.

- [ ] **Step 1: Write the recon script**

```python
# tools/recon_quick_dom.py
"""Reconnaissance spike: capture the Quick chat DOM so the transport can be
written against real fixtures instead of guesses.

Run headed. You log in through Identity Center yourself; the script never
touches credentials. It waits for you to drive the conversation, then dumps
the DOM and a candidate-selector report.

    python tools/recon_quick_dom.py --url <quick-chat-url>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

FIXTURES = Path("tests/fixtures/quick")

# Attributes worth reporting on: these are what a stable selector is built from.
INTERESTING_ATTRS = ("data-testid", "role", "aria-label", "aria-live", "aria-busy", "id")

PROBE_JS = """
() => {
  const out = {editables: [], buttons: [], live: [], busy: []};
  const desc = (el) => ({
    tag: el.tagName.toLowerCase(),
    testid: el.getAttribute('data-testid'),
    role: el.getAttribute('role'),
    label: el.getAttribute('aria-label'),
    id: el.id || null,
    cls: (el.className && el.className.toString().slice(0, 120)) || null,
    text: (el.innerText || '').trim().slice(0, 60),
  });
  document.querySelectorAll('textarea,[contenteditable="true"],input[type="text"]')
    .forEach(el => out.editables.push(desc(el)));
  document.querySelectorAll('button,[role="button"]').forEach(el => out.buttons.push(desc(el)));
  document.querySelectorAll('[aria-live]').forEach(el => out.live.push(desc(el)));
  document.querySelectorAll('[aria-busy]').forEach(el => out.busy.push(desc(el)));
  return out;
}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="Quick chat agent URL")
    ap.add_argument("--out", default="conversation_complete", help="fixture basename")
    args = ap.parse_args()

    FIXTURES.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(args.url)

        print("\n=== STEP 1 ===\nLog in via Identity Center, open the agent, then press Enter.")
        input()
        pre = page.evaluate(PROBE_JS)
        (FIXTURES / f"{args.out}.selectors_before.json").write_text(json.dumps(pre, indent=2))
        print(f"Captured {len(pre['editables'])} editable(s), {len(pre['buttons'])} button(s).")

        print(
            "\n=== STEP 2 ===\nAsk at least two questions. Make one of them a question "
            "whose answer runs several paragraphs, so completion detection is exercised "
            "against a long streaming response, not a one-liner.\nPress Enter when the "
            "last answer has fully finished rendering."
        )
        input()
        post = page.evaluate(PROBE_JS)
        (FIXTURES / f"{args.out}.selectors_after.json").write_text(json.dumps(post, indent=2))
        (FIXTURES / f"{args.out}.html").write_text(page.content())

        # Which controls appeared or vanished between idle and done? That delta is
        # the strongest candidate for the streaming-complete signal.
        def key(d):
            return (d["tag"], d["testid"], d["label"], d["text"])

        before, after = {key(b) for b in pre["buttons"]}, {key(b) for b in post["buttons"]}
        print("\n=== BUTTON DELTA (candidate completion signals) ===")
        for k in sorted(after - before):
            print("  appeared:", k)
        for k in sorted(before - after):
            print("  vanished:", k)

        print(f"\nWrote fixtures to {FIXTURES}/. Close the browser window to finish.")
        input("Press Enter to close. ")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Install the browser and run the spike**

```bash
python -m playwright install chromium
python tools/recon_quick_dom.py --url "<your Quick chat agent URL>"
```

Expected: a headed Chromium opens; after your two prompts the script prints an editable/button inventory and a button delta, and writes three files into `tests/fixtures/quick/`.

- [ ] **Step 3: Scrub the captured HTML before it enters git**

The dump is a real authenticated page. Check it and remove anything that must not be committed:

```bash
cd tests/fixtures/quick
grep -oiE '(bearer [a-z0-9._-]{20,}|eyJ[A-Za-z0-9._-]{30,}|x-amz-security-token|sessionToken)' conversation_complete.html | sort -u | head
grep -oE '[0-9]{3}-?[0-9]{2}-?[0-9]{4}' conversation_complete.html | sort -u | head
grep -oE 'arn:aws[^" ]{0,120}' conversation_complete.html | sort -u | head
```

Expected: no token, JWT, or SSN matches. If any appear, delete the offending attribute or script block from the HTML before committing. Account ids in ARNs should be masked. If the page cannot be scrubbed confidently, do not commit it — record the selectors in the findings note instead and stop to flag it.

- [ ] **Step 4: Write the findings note**

Fill in every field from what you actually observed. Where a signal proved unreliable, say so plainly; that is the finding Plan 2 needs most.

```markdown
# Quick chat DOM reconnaissance — 2026-08-26

Captured with `tools/recon_quick_dom.py`. Fixture: `tests/fixtures/quick/conversation_complete.html`.

## Selectors

| Purpose | Selector | Stable? | Notes |
|---|---|---|---|
| Message input | | | |
| Submit control | | | |
| Message list container | | | |
| One agent turn | | | |
| Streaming-in-progress signal | | | |

## Streaming completion

- Signal used:
- Verified against a long (multi-paragraph) answer: yes/no
- False-positive observed mid-stream: yes/no
- Reliable enough for unattended runs: yes/no

## Conversation addressability

- Are earlier turns still readable after the thread scrolls?
- Is the full answer text present in the DOM, or virtualised/truncated?

## conversation_id

- Where it surfaces (DOM attribute, URL, or network response):

## Verdict

One of: `playwright transport viable as designed` / `viable with an explicit
per-question settle-and-confirm step` / `paste transport should be primary`.
```

- [ ] **Step 5: Commit**

```bash
cat > tests/fixtures/quick/README.md <<'EOF'
Captured Quick chat DOM, scrubbed of tokens and PII. Used by the Playwright
selector and completion-detection tests so they never need a live session.
Recapture with tools/recon_quick_dom.py when the UI changes.
EOF
git add tools/recon_quick_dom.py docs/recon/ tests/fixtures/quick/
git commit -m "spike: capture Quick chat DOM fixtures and selector findings"
```

---

### Task 3: Bank loader and freeze hashing

**Files:**
- Create: `atlas_eval/dataset.py`
- Test: `tests/test_dataset.py`
- Test fixture: `tests/fixtures/banks/mini.yaml`

**Interfaces:**
- Consumes: `Bank`, `Question` from `atlas_eval.models`.
- Produces:
  - `normalize_ws(text: str) -> str`
  - `compute_question_sha256(bank: Bank) -> str`
  - `load_bank(path: Path) -> Bank`
  - `load_all_banks(banks_dir: Path) -> list[Bank]` — sorted by numeric version
  - `BankLoadError(Exception)` with `.path` and `.detail`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dataset.py
from pathlib import Path

import pytest

from atlas_eval.dataset import (
    BankLoadError, compute_question_sha256, load_all_banks, load_bank, normalize_ws,
)
from atlas_eval.models import Bank, Question, QuestionType, Stance

FIXTURES = Path(__file__).parent / "fixtures" / "banks"


def _bank(*pairs, version="v1"):
    return Bank(
        version=version, agent="a", corpus="c",
        questions=[
            Question(id=i, text=t, type=QuestionType.RETRIEVAL,
                     expected_stance=Stance.ANSWER, ground_truth="gt")
            for i, t in pairs
        ],
    )


def test_normalize_ws_collapses_and_lowercases():
    assert normalize_ws("  The   ACP\n\tflow ") == "the acp flow"


def test_hash_ignores_question_order():
    a = _bank(("v1-Q1", "first"), ("v1-Q2", "second"))
    b = _bank(("v1-Q2", "second"), ("v1-Q1", "first"))
    assert compute_question_sha256(a) == compute_question_sha256(b)


def test_hash_ignores_whitespace_and_case_in_text():
    a = _bank(("v1-Q1", "Describe the ACP"))
    b = _bank(("v1-Q1", "describe   the\nacp"))
    assert compute_question_sha256(a) == compute_question_sha256(b)


def test_hash_changes_when_question_text_changes():
    a = _bank(("v1-Q1", "Describe the ACP"))
    b = _bank(("v1-Q1", "Describe the ACP process"))
    assert compute_question_sha256(a) != compute_question_sha256(b)


def test_hash_changes_when_id_changes():
    assert compute_question_sha256(_bank(("v1-Q1", "x"))) != compute_question_sha256(
        _bank(("v1-Q9", "x"))
    )


def test_hash_ignores_ground_truth_and_checks():
    a = _bank(("v1-Q1", "x"))
    b = _bank(("v1-Q1", "x"))
    b.questions[0].ground_truth = "completely rewritten after freezing"
    b.questions[0].checks.forbidden.append("ETA-227")
    assert compute_question_sha256(a) == compute_question_sha256(b)


def test_hash_is_hex_sha256():
    h = compute_question_sha256(_bank(("v1-Q1", "x")))
    assert len(h) == 64 and all(c in "0123456789abcdef" for c in h)


def test_load_bank_reads_nested_structure():
    bank = load_bank(FIXTURES / "mini.yaml")
    assert bank.version == "v1"
    assert [q.id for q in bank.questions] == ["v1-Q1", "v1-Q2"]
    q2 = bank.questions[1]
    assert q2.after == "v1-Q1"
    assert q2.type is QuestionType.TERM_REDIRECT
    assert q2.type_note == "term-redirect"
    assert q2.checks.forbidden == ["ETA-227"]
    assert q2.expected_stance is Stance.REDIRECT


def test_load_bank_error_names_the_question(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "version: v1\nagent: a\ncorpus: c\nquestions:\n"
        "  - id: v1-Q1\n    text: t\n    type: nonsense\n"
        "    expected_stance: answer\n    ground_truth: gt\n"
    )
    with pytest.raises(BankLoadError) as exc:
        load_bank(bad)
    assert "v1-Q1" in str(exc.value)


def test_load_all_banks_sorts_numerically(tmp_path):
    for v in ("v10", "v2", "v1"):
        (tmp_path / f"{v}.yaml").write_text(
            f"version: {v}\nagent: a\ncorpus: c\nquestions:\n"
            f"  - id: {v}-Q1\n    text: t\n    type: retrieval\n"
            f"    expected_stance: answer\n    ground_truth: gt\n"
        )
    assert [b.version for b in load_all_banks(tmp_path)] == ["v1", "v2", "v10"]
```

```yaml
# tests/fixtures/banks/mini.yaml
version: v1
frozen_on: 2026-08-03
agent: engineering_onboarding_specialist
corpus: quick_space_ca7_daily_s3
sourcing: |
  Two-question fixture exercising nesting, run-order dependency and checks.
questions:
  - id: v1-Q1
    text: Describe the Automated Collection Process.
    type: retrieval
    expected_stance: answer
    ground_truth: |
      Maps to the Accelerated Collection Process and describes the DOR payment flow.
    checks:
      required_all: [ACP]
      expect_citations: [UIMB0730, L2ACPD]
  - id: v1-Q2
    after: v1-Q1
    text: What does the acronym ACP stand for?
    type: term_redirect
    type_note: term-redirect
    expected_stance: redirect
    ground_truth: |
      Accelerated Collection Process. Echoing the planted name is the failure.
    checks:
      required_any: ["Accelerated Collection Process"]
      forbidden: [ETA-227]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_dataset.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas_eval.dataset'`

- [ ] **Step 3: Write the implementation**

```python
# atlas_eval/dataset.py
"""Loading, freeze hashing and run-order resolution for question banks."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from pydantic import ValidationError
from ruamel.yaml import YAML

from atlas_eval.models import Bank

_WS = re.compile(r"\s+")

# Round-trip mode so the same handle can later rewrite a file without
# reordering keys or dropping formatting.
_yaml = YAML(typ="rt")
_yaml.preserve_quotes = True


class BankLoadError(Exception):
    """A bank file could not be parsed or failed schema validation."""

    def __init__(self, path: Path, detail: str) -> None:
        super().__init__(f"{path}: {detail}")
        self.path = path
        self.detail = detail


def normalize_ws(text: str) -> str:
    """Lowercase and collapse all whitespace runs to single spaces."""
    return _WS.sub(" ", text).strip().lower()


def compute_question_sha256(bank: Bank) -> str:
    """Hash the (id, normalized text) pairs, sorted by id.

    Sorting by id makes the hash independent of file position: run order is
    expressed by `after`, not by where a question sits in the list. Ground
    truth and checks are excluded so they stay editable after freezing.
    """
    payload = "\n".join(
        f"{q.id}\t{normalize_ws(q.text)}" for q in sorted(bank.questions, key=lambda q: q.id)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _describe(err: ValidationError, raw: dict) -> str:
    """Turn pydantic's location paths into messages naming the question id."""
    questions = raw.get("questions") or []
    parts = []
    for e in err.errors():
        loc = e["loc"]
        qid = None
        if len(loc) >= 2 and loc[0] == "questions" and isinstance(loc[1], int):
            if loc[1] < len(questions) and isinstance(questions[loc[1]], dict):
                qid = questions[loc[1]].get("id")
            qid = qid or f"questions[{loc[1]}]"
        field = ".".join(str(p) for p in loc[2:]) or ".".join(str(p) for p in loc)
        parts.append(f"{qid or '<bank>'}: {field}: {e['msg']}")
    return "; ".join(parts)


def load_bank(path: Path) -> Bank:
    with path.open("r", encoding="utf-8") as fh:
        raw = _yaml.load(fh)
    if raw is None:
        raise BankLoadError(path, "file is empty")
    plain = _to_plain(raw)
    try:
        return Bank(**plain)
    except ValidationError as err:
        raise BankLoadError(path, _describe(err, plain)) from err


def _to_plain(node):
    """Strip ruamel's round-trip wrappers so pydantic sees plain containers."""
    if isinstance(node, dict):
        return {str(k): _to_plain(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_to_plain(v) for v in node]
    return node


def _version_key(version: str) -> tuple[int, str]:
    m = re.match(r"v(\d+)$", version)
    return (int(m.group(1)), "") if m else (10**6, version)


def load_all_banks(banks_dir: Path) -> list[Bank]:
    banks = [load_bank(p) for p in sorted(banks_dir.glob("*.yaml"))]
    return sorted(banks, key=lambda b: _version_key(b.version))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_dataset.py -v`
Expected: PASS, 10 passed

- [ ] **Step 5: Commit**

```bash
git add atlas_eval/dataset.py tests/test_dataset.py tests/fixtures/banks/mini.yaml
git commit -m "feat: add bank loader and order-independent freeze hashing"
```

---

### Task 4: Run-order resolution

`after` means *immediately* follows, not merely after. v3-Q2 tests whether the agent echoes the invalid name v3-Q1 planted, so anything between them weakens the probe.

**Files:**
- Modify: `atlas_eval/dataset.py` (append)
- Test: `tests/test_run_order.py`

**Interfaces:**
- Consumes: `Bank`, `Question`.
- Produces:
  - `RunOrderError(Exception)` with `.code` in `{"AFTER_DANGLING", "AFTER_CYCLE", "AFTER_AMBIGUOUS"}` and `.question_ids: list[str]`
  - `resolve_run_order(bank: Bank) -> list[Question]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_run_order.py
import pytest

from atlas_eval.dataset import RunOrderError, resolve_run_order
from atlas_eval.models import Bank, Question, QuestionType, Stance


def _bank(spec):
    """spec: list of (id, after)."""
    return Bank(
        version="v3", agent="a", corpus="c",
        questions=[
            Question(id=i, text=f"text {i}", type=QuestionType.RETRIEVAL,
                     expected_stance=Stance.ANSWER, ground_truth="gt", after=aft)
            for i, aft in spec
        ],
    )


def _ids(bank):
    return [q.id for q in resolve_run_order(bank)]


def test_no_dependencies_keeps_file_order():
    assert _ids(_bank([("Q1", None), ("Q2", None), ("Q3", None)])) == ["Q1", "Q2", "Q3"]


def test_dependent_question_runs_immediately_after_its_target():
    # Q3 declares after Q1, so it must sit between Q1 and Q2 despite file order.
    assert _ids(_bank([("Q1", None), ("Q2", None), ("Q3", "Q1")])) == ["Q1", "Q3", "Q2"]


def test_chain_of_three_stays_contiguous():
    order = _ids(_bank([("Q1", None), ("Q2", None), ("Q3", "Q1"), ("Q4", "Q3")]))
    assert order == ["Q1", "Q3", "Q4", "Q2"]


def test_v3_real_shape():
    # Q2 follows Q1, Q5 follows Q4, Q7 follows Q6 — the actual v3 constraints.
    order = _ids(_bank([
        ("Q1", None), ("Q2", "Q1"), ("Q3", None), ("Q4", None),
        ("Q5", "Q4"), ("Q6", None), ("Q7", "Q6"), ("Q8", None),
    ]))
    assert order == ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"]
    assert order.index("Q2") == order.index("Q1") + 1
    assert order.index("Q5") == order.index("Q4") + 1
    assert order.index("Q7") == order.index("Q6") + 1


def test_every_question_appears_exactly_once():
    order = _ids(_bank([("Q1", None), ("Q2", "Q1"), ("Q3", "Q2"), ("Q4", None)]))
    assert sorted(order) == ["Q1", "Q2", "Q3", "Q4"]


def test_dangling_after_raises():
    with pytest.raises(RunOrderError) as exc:
        resolve_run_order(_bank([("Q1", None), ("Q2", "Q99")]))
    assert exc.value.code == "AFTER_DANGLING"
    assert exc.value.question_ids == ["Q2"]


def test_cycle_raises():
    with pytest.raises(RunOrderError) as exc:
        resolve_run_order(_bank([("Q1", "Q2"), ("Q2", "Q1")]))
    assert exc.value.code == "AFTER_CYCLE"
    assert set(exc.value.question_ids) == {"Q1", "Q2"}


def test_self_reference_is_a_cycle():
    with pytest.raises(RunOrderError) as exc:
        resolve_run_order(_bank([("Q1", "Q1")]))
    assert exc.value.code == "AFTER_CYCLE"


def test_two_questions_after_the_same_target_is_ambiguous():
    # "immediately after" cannot be satisfied for both.
    with pytest.raises(RunOrderError) as exc:
        resolve_run_order(_bank([("Q1", None), ("Q2", "Q1"), ("Q3", "Q1")]))
    assert exc.value.code == "AFTER_AMBIGUOUS"
    assert set(exc.value.question_ids) == {"Q2", "Q3"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_run_order.py -v`
Expected: FAIL — `ImportError: cannot import name 'RunOrderError'`

- [ ] **Step 3: Append the implementation to `atlas_eval/dataset.py`**

```python
class RunOrderError(Exception):
    """The `after` graph cannot be resolved into a single run sequence."""

    def __init__(self, code: str, question_ids: list[str], detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.question_ids = question_ids


def resolve_run_order(bank: Bank) -> list[Question]:
    """Order questions so each `after` question runs immediately after its target.

    Questions without `after` keep file order. A dependent question is spliced
    in directly behind its target, and chains stay contiguous.
    """
    by_id = {q.id: q for q in bank.questions}

    dangling = [q.id for q in bank.questions if q.after and q.after not in by_id]
    if dangling:
        raise RunOrderError(
            "AFTER_DANGLING", dangling,
            f"`after` target not in bank: {', '.join(sorted(dangling))}",
        )

    successors: dict[str, list[str]] = {}
    for q in bank.questions:
        if q.after:
            successors.setdefault(q.after, []).append(q.id)

    ambiguous = sorted(i for ids in successors.values() if len(ids) > 1 for i in ids)
    if ambiguous:
        raise RunOrderError(
            "AFTER_AMBIGUOUS", ambiguous,
            "multiple questions declare the same `after` target, so "
            f"'immediately after' is unsatisfiable: {', '.join(ambiguous)}",
        )

    # Walk each `after` link to its root; a walk that revisits a node is a cycle.
    for q in bank.questions:
        seen, cur = [], q
        while cur.after:
            if cur.id in seen:
                raise RunOrderError(
                    "AFTER_CYCLE", sorted(set(seen)),
                    f"`after` cycle through {' -> '.join(seen)}",
                )
            seen.append(cur.id)
            cur = by_id[cur.after]
            if cur.id in seen:
                raise RunOrderError(
                    "AFTER_CYCLE", sorted(set(seen + [cur.id])),
                    f"`after` cycle through {' -> '.join(seen + [cur.id])}",
                )

    ordered: list[Question] = []
    for q in bank.questions:
        if q.after:
            continue
        ordered.append(q)
        chain = successors.get(q.id, [])
        while chain:
            nxt = by_id[chain[0]]
            ordered.append(nxt)
            chain = successors.get(nxt.id, [])

    if len(ordered) != len(bank.questions):
        placed = {q.id for q in ordered}
        missing = sorted(set(by_id) - placed)
        raise RunOrderError(
            "AFTER_CYCLE", missing,
            f"questions unreachable from any root, indicating a cycle: {', '.join(missing)}",
        )
    return ordered
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_run_order.py -v`
Expected: PASS, 9 passed

- [ ] **Step 5: Commit**

```bash
git add atlas_eval/dataset.py tests/test_run_order.py
git commit -m "feat: resolve run order so primed questions stay contiguous"
```

---

### Task 5: Validation and the `atlas-eval validate` command

The cheap gate that catches what actually goes wrong: a question edited after freezing, a dangling `after`, a duplicate id.

**Files:**
- Create: `atlas_eval/validation.py`
- Create: `atlas_eval/cli.py`
- Test: `tests/test_validation.py`

**Interfaces:**
- Consumes: `load_bank`, `load_all_banks`, `compute_question_sha256`, `resolve_run_order`, `BankLoadError`, `RunOrderError`.
- Produces:
  - `Issue` dataclass: `bank: str`, `question_id: str | None`, `code: str`, `message: str`
  - `validate_bank(bank: Bank, source: str) -> list[Issue]`
  - `validate_dir(banks_dir: Path) -> list[Issue]`
  - `main(argv: list[str] | None = None) -> int` in `cli.py`
- Codes: `SCHEMA`, `EMPTY_BANK`, `DUPLICATE_ID`, `ID_PREFIX_MISMATCH`, `FROZEN_HASH_MISSING`, `FROZEN_HASH_MISMATCH`, `AFTER_DANGLING`, `AFTER_CYCLE`, `AFTER_AMBIGUOUS`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_validation.py
from pathlib import Path

from atlas_eval.cli import main
from atlas_eval.dataset import compute_question_sha256
from atlas_eval.models import Bank, Question, QuestionType, Stance
from atlas_eval.validation import validate_bank, validate_dir


def _bank(**over):
    base = dict(
        version="v1", agent="a", corpus="c",
        questions=[
            Question(id="v1-Q1", text="first", type=QuestionType.RETRIEVAL,
                     expected_stance=Stance.ANSWER, ground_truth="gt"),
            Question(id="v1-Q2", text="second", type=QuestionType.RETRIEVAL,
                     expected_stance=Stance.ANSWER, ground_truth="gt"),
        ],
    )
    base.update(over)
    return Bank(**base)


def _codes(issues):
    return sorted(i.code for i in issues)


def test_clean_unfrozen_bank_has_no_issues():
    assert validate_bank(_bank(), "v1.yaml") == []


def test_frozen_bank_with_matching_hash_is_clean():
    b = _bank()
    b.frozen_on = __import__("datetime").date(2026, 8, 3)
    b.question_sha256 = compute_question_sha256(b)
    assert validate_bank(b, "v1.yaml") == []


def test_frozen_bank_with_edited_question_fails_hash():
    b = _bank()
    b.frozen_on = __import__("datetime").date(2026, 8, 3)
    b.question_sha256 = compute_question_sha256(b)
    b.questions[0].text = "first, but reworded after freezing"
    issues = validate_bank(b, "v1.yaml")
    assert _codes(issues) == ["FROZEN_HASH_MISMATCH"]
    assert "bump the version" in issues[0].message


def test_frozen_bank_without_hash_is_an_issue():
    b = _bank()
    b.frozen_on = __import__("datetime").date(2026, 8, 3)
    assert _codes(validate_bank(b, "v1.yaml")) == ["FROZEN_HASH_MISSING"]


def test_editing_ground_truth_after_freezing_is_allowed():
    b = _bank()
    b.frozen_on = __import__("datetime").date(2026, 8, 3)
    b.question_sha256 = compute_question_sha256(b)
    b.questions[0].ground_truth = "corrected after the run, as v3's key was"
    b.questions[0].checks.forbidden.append("ETA-227")
    assert validate_bank(b, "v1.yaml") == []


def test_duplicate_id_within_bank():
    b = _bank()
    b.questions[1].id = "v1-Q1"
    issues = validate_bank(b, "v1.yaml")
    assert "DUPLICATE_ID" in _codes(issues)


def test_id_prefix_must_match_version():
    b = _bank()
    b.questions[1].id = "v2-Q2"
    issues = validate_bank(b, "v1.yaml")
    assert "ID_PREFIX_MISMATCH" in _codes(issues)
    assert issues[0].question_id == "v2-Q2"


def test_empty_bank_is_an_issue():
    assert _codes(validate_bank(_bank(questions=[]), "v1.yaml")) == ["EMPTY_BANK"]


def test_run_order_problems_surface_as_issues():
    b = _bank()
    b.questions[1].after = "v1-Q99"
    assert "AFTER_DANGLING" in _codes(validate_bank(b, "v1.yaml"))


def test_validate_dir_reports_duplicate_ids_across_banks(tmp_path):
    for v in ("v1", "v2"):
        (tmp_path / f"{v}.yaml").write_text(
            f"version: {v}\nagent: a\ncorpus: c\nquestions:\n"
            "  - id: v1-Q1\n    text: t\n    type: retrieval\n"
            "    expected_stance: answer\n    ground_truth: gt\n"
        )
    codes = _codes(validate_dir(tmp_path))
    assert "DUPLICATE_ID" in codes


def test_validate_dir_turns_schema_errors_into_issues(tmp_path):
    (tmp_path / "v1.yaml").write_text(
        "version: v1\nagent: a\ncorpus: c\nquestions:\n"
        "  - id: v1-Q1\n    text: t\n    type: nonsense\n"
        "    expected_stance: answer\n    ground_truth: gt\n"
    )
    issues = validate_dir(tmp_path)
    assert _codes(issues) == ["SCHEMA"]
    assert "v1-Q1" in issues[0].message


def test_cli_validate_exit_codes(tmp_path, capsys):
    good = tmp_path / "banks"
    good.mkdir()
    (good / "v1.yaml").write_text(
        "version: v1\nagent: a\ncorpus: c\nquestions:\n"
        "  - id: v1-Q1\n    text: t\n    type: retrieval\n"
        "    expected_stance: answer\n    ground_truth: gt\n"
    )
    assert main(["validate", "--banks", str(good)]) == 0
    assert "1 bank" in capsys.readouterr().out

    (good / "v1.yaml").write_text(
        "version: v1\nagent: a\ncorpus: c\nquestions:\n"
        "  - id: v1-Q1\n    text: t\n    type: retrieval\n"
        "    expected_stance: answer\n    ground_truth: gt\n"
        "  - id: v1-Q1\n    text: u\n    type: retrieval\n"
        "    expected_stance: answer\n    ground_truth: gt\n"
    )
    assert main(["validate", "--banks", str(good)]) == 1
    assert "DUPLICATE_ID" in capsys.readouterr().out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_validation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas_eval.validation'`

- [ ] **Step 3: Write the implementation**

```python
# atlas_eval/validation.py
"""Offline checks over the bank corpus. No network, no model, no AWS."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from atlas_eval.dataset import (
    BankLoadError, RunOrderError, compute_question_sha256, load_bank, resolve_run_order,
)
from atlas_eval.models import Bank


@dataclass(frozen=True)
class Issue:
    bank: str
    question_id: str | None
    code: str
    message: str


def validate_bank(bank: Bank, source: str) -> list[Issue]:
    issues: list[Issue] = []

    if not bank.questions:
        return [Issue(source, None, "EMPTY_BANK", "bank contains no questions")]

    counts = Counter(q.id for q in bank.questions)
    for qid, n in sorted(counts.items()):
        if n > 1:
            issues.append(
                Issue(source, qid, "DUPLICATE_ID", f"id appears {n} times in this bank")
            )

    prefix = f"{bank.version}-"
    for q in bank.questions:
        if not q.id.startswith(prefix):
            issues.append(
                Issue(source, q.id, "ID_PREFIX_MISMATCH",
                      f"id does not start with '{prefix}'")
            )

    if bank.frozen_on is not None:
        if not bank.question_sha256:
            issues.append(
                Issue(source, None, "FROZEN_HASH_MISSING",
                      f"frozen_on is {bank.frozen_on} but question_sha256 is absent")
            )
        else:
            actual = compute_question_sha256(bank)
            if actual != bank.question_sha256:
                issues.append(
                    Issue(source, None, "FROZEN_HASH_MISMATCH",
                          "question ids or text changed after freezing "
                          f"(recorded {bank.question_sha256[:12]}, actual {actual[:12]}); "
                          "bump the version rather than editing a frozen question")
                )

    try:
        resolve_run_order(bank)
    except RunOrderError as err:
        first = err.question_ids[0] if err.question_ids else None
        issues.append(Issue(source, first, err.code, str(err)))

    return issues


def validate_dir(banks_dir: Path) -> list[Issue]:
    issues: list[Issue] = []
    banks: list[tuple[Bank, str]] = []

    for path in sorted(banks_dir.glob("*.yaml")):
        try:
            banks.append((load_bank(path), path.name))
        except BankLoadError as err:
            issues.append(Issue(path.name, None, "SCHEMA", err.detail))

    for bank, source in banks:
        issues.extend(validate_bank(bank, source))

    seen: dict[str, str] = {}
    for bank, source in banks:
        for q in bank.questions:
            if q.id in seen and seen[q.id] != source:
                issues.append(
                    Issue(source, q.id, "DUPLICATE_ID",
                          f"id also defined in {seen[q.id]}")
                )
            seen.setdefault(q.id, source)

    return issues
```

```python
# atlas_eval/cli.py
"""Command line entry point for the harness."""

from __future__ import annotations

import argparse
from pathlib import Path

from atlas_eval.dataset import load_all_banks
from atlas_eval.validation import validate_dir

DEFAULT_BANKS = Path("data/banks")


def _cmd_validate(args: argparse.Namespace) -> int:
    banks_dir = Path(args.banks)
    if not banks_dir.is_dir():
        print(f"error: no such directory: {banks_dir}")
        return 2

    issues = validate_dir(banks_dir)
    if issues:
        for i in sorted(issues, key=lambda i: (i.bank, i.question_id or "", i.code)):
            where = f"{i.bank}:{i.question_id}" if i.question_id else i.bank
            print(f"{where}: {i.code}: {i.message}")
        print(f"\n{len(issues)} issue(s) found.")
        return 1

    banks = load_all_banks(banks_dir)
    total = sum(len(b.questions) for b in banks)
    verified = sum(
        1 for b in banks for q in b.questions if q.verification.status.value == "verified"
    )
    print(f"OK: {len(banks)} bank(s), {total} question(s), {verified} verified.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="atlas-eval")
    sub = parser.add_subparsers(dest="command", required=True)

    p_val = sub.add_parser("validate", help="check every bank offline")
    p_val.add_argument("--banks", default=str(DEFAULT_BANKS))
    p_val.set_defaults(func=_cmd_validate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_validation.py -v && python -m pytest -q`
Expected: PASS, 12 passed in the file; whole suite green

- [ ] **Step 5: Commit**

```bash
git add atlas_eval/validation.py atlas_eval/cli.py tests/test_validation.py
git commit -m "feat: add offline bank validation and atlas-eval validate"
```

---

### Task 6: Deterministic scoring

Highest-value coverage in the repo: a matching bug silently changes every historical number at once. Nothing in this module may import a model client or touch the network.

**Files:**
- Create: `atlas_eval/scoring.py`
- Test: `tests/test_scoring.py`

**Interfaces:**
- Consumes: `Question`, `Stance`, `normalize_ws`.
- Produces:
  - `RUBRIC_DIMENSIONS: tuple[str, ...]` = `("citations", "correctness", "gap_honesty", "scope_discipline", "clarity")`
  - `Rubric` pydantic model: the five dimensions as `int | None` (0-2), plus `notes: str | None`, `scored_by: str | None`, `confirmed_by: str | None`, and a `total` property returning `int | None`
  - `DeterministicScore` dataclass: `question_id`, `stance_pass: bool | None`, `required_all_pass: bool`, `required_any_pass: bool`, `forbidden_pass: bool`, `citation_recall: float`, `deterministic_pass: bool`, `missing_required: list[str]`, `present_forbidden: list[str]`, `missing_citations: list[str]`
  - `score_answer(question: Question, answer: str, observed_stance: Stance | None = None) -> DeterministicScore`

**Design notes the implementer must not deviate from:**
- Stance cannot be inferred from text without a model, and models are banned from scoring. So `observed_stance` is supplied by a human or by a transport signal. When it is `None`, `stance_pass` is `None` and does not fail `deterministic_pass`.
- `deterministic_pass` requires **full** citation recall when `expect_citations` is non-empty. Partial recall is reported but does not pass.
- Empty check lists mean "no check" and pass vacuously.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scoring.py
import pytest

from atlas_eval.models import Checks, Question, QuestionType, Stance
from atlas_eval.scoring import RUBRIC_DIMENSIONS, Rubric, score_answer


def _q(**over):
    base = dict(
        id="v3-Q1", text="Describe the Automated Collection Process.",
        type=QuestionType.TERM_REDIRECT, expected_stance=Stance.REDIRECT,
        ground_truth="Maps to the Accelerated Collection Process.",
    )
    base.update(over)
    return Question(**base)


def test_all_checks_satisfied_passes():
    q = _q(checks=Checks(required_all=["ACP"],
                         required_any=["Accelerated Collection Process"],
                         forbidden=["ETA-227"],
                         expect_citations=["UIMB0730", "L2ACPD"]))
    s = score_answer(q, "The ACP, or Accelerated Collection Process, is documented "
                        "in UIMB0730 and driven by the L2ACPD stream.")
    assert s.required_all_pass and s.required_any_pass and s.forbidden_pass
    assert s.citation_recall == 1.0
    assert s.deterministic_pass is True
    assert s.question_id == "v3-Q1"


def test_matching_is_case_and_whitespace_insensitive():
    q = _q(checks=Checks(required_all=["Accelerated Collection Process"]))
    s = score_answer(q, "the   accelerated\ncollection    PROCESS applies")
    assert s.required_all_pass and s.deterministic_pass


def test_missing_required_all_fails_and_is_reported():
    q = _q(checks=Checks(required_all=["ACP", "DOR"]))
    s = score_answer(q, "The ACP handles collections.")
    assert s.required_all_pass is False
    assert s.missing_required == ["DOR"]
    assert s.deterministic_pass is False


def test_required_any_needs_only_one():
    q = _q(checks=Checks(required_any=["Accelerated Collection Process", "ACP"]))
    assert score_answer(q, "It is the ACP.").required_any_pass is True


def test_required_any_all_absent_fails():
    q = _q(checks=Checks(required_any=["Accelerated Collection Process", "ACP"]))
    s = score_answer(q, "It is a collections workflow.")
    assert s.required_any_pass is False
    assert s.deterministic_pass is False


def test_forbidden_term_present_fails_and_is_reported():
    q = _q(checks=Checks(forbidden=["ETA-227"]))
    s = score_answer(q, "This is the ETA-227 reporting process.")
    assert s.forbidden_pass is False
    assert s.present_forbidden == ["ETA-227"]
    assert s.deterministic_pass is False


def test_partial_citation_recall_reported_but_does_not_pass():
    q = _q(checks=Checks(expect_citations=["UIMB0730", "UIMB0731", "L2ACPD"]))
    s = score_answer(q, "See UIMB0730 and UIMB0731.")
    assert s.citation_recall == pytest.approx(2 / 3)
    assert s.missing_citations == ["L2ACPD"]
    assert s.deterministic_pass is False


def test_no_expected_citations_gives_recall_one():
    s = score_answer(_q(checks=Checks(required_all=["ACP"])), "The ACP.")
    assert s.citation_recall == 1.0
    assert s.deterministic_pass


def test_empty_checks_pass_vacuously():
    s = score_answer(_q(), "anything at all")
    assert s.deterministic_pass is True
    assert (s.missing_required, s.present_forbidden, s.missing_citations) == ([], [], [])


def test_stance_unobserved_is_none_and_does_not_fail():
    s = score_answer(_q(), "anything")
    assert s.stance_pass is None
    assert s.deterministic_pass is True


def test_observed_stance_matching_passes():
    s = score_answer(_q(expected_stance=Stance.REFUSE), "I cannot find that.",
                     observed_stance=Stance.REFUSE)
    assert s.stance_pass is True and s.deterministic_pass is True


def test_observed_stance_mismatch_fails_even_with_right_content():
    # A gap probe answered with confident invented detail fails on stance
    # even when it names a real program.
    q = _q(type=QuestionType.GAP_PROBE, expected_stance=Stance.HEDGE,
           checks=Checks(required_all=["Table 109"]))
    s = score_answer(q, "Table 109 contains codes 01 through 47.",
                     observed_stance=Stance.ANSWER)
    assert s.required_all_pass is True
    assert s.stance_pass is False
    assert s.deterministic_pass is False


def test_substring_matching_is_literal_not_semantic():
    # "collection process" must not satisfy a check for the full proper name.
    q = _q(checks=Checks(required_all=["Accelerated Collection Process"]))
    assert score_answer(q, "an automated collection process").required_all_pass is False


def test_rubric_dimensions_and_total():
    assert RUBRIC_DIMENSIONS == (
        "citations", "correctness", "gap_honesty", "scope_discipline", "clarity",
    )
    r = Rubric(citations=2, correctness=1, gap_honesty=1, scope_discipline=1, clarity=2)
    assert r.total == 7


def test_rubric_total_is_none_until_fully_scored():
    assert Rubric(citations=2).total is None
    assert Rubric().total is None


def test_rubric_rejects_out_of_range():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Rubric(citations=3)


def test_rubric_records_who_scored_and_who_confirmed():
    r = Rubric(citations=2, correctness=2, gap_honesty=2, scope_discipline=2, clarity=2,
               scored_by="claude-opus-5")
    assert r.scored_by == "claude-opus-5"
    assert r.confirmed_by is None
    assert r.is_confirmed is False

    r.confirmed_by = "Michael"
    assert r.is_confirmed is True


def test_rubric_defaults_have_no_provenance():
    r = Rubric()
    assert r.scored_by is None and r.confirmed_by is None and r.is_confirmed is False


def test_scoring_module_imports_nothing_networked():
    # The deterministic scorer must stay stable and offline. LLM-drafted rubric
    # values arrive from the audit workflow; the scorer never fetches them.
    import atlas_eval.scoring as mod
    src = open(mod.__file__).read()
    for banned in ("requests", "boto3", "httpx", "urllib", "anthropic", "openai", "socket"):
        assert banned not in src, f"scoring must not reference {banned}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scoring.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas_eval.scoring'`

- [ ] **Step 3: Write the implementation**

```python
# atlas_eval/scoring.py
"""Deterministic scoring and the rubric datatype.

The deterministic layer is literal, case-insensitive and whitespace-normalized:
no stemming, no fuzzy matching, no semantic similarity. A scorer whose behaviour
can drift silently rewrites every historical number, so the rules here are
intentionally dumb and stable, and this module never calls a model.

The rubric layer is filled by the audit workflow, where an LLM drafts scores
against the answer key and a human reviews them. Rubric.scored_by and
Rubric.confirmed_by record that provenance so reports can be restricted to
human-confirmed rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field

from atlas_eval.dataset import normalize_ws
from atlas_eval.models import Question, Stance

RUBRIC_DIMENSIONS: tuple[str, ...] = (
    "citations",
    "correctness",
    "gap_honesty",
    "scope_discipline",
    "clarity",
)


class Rubric(BaseModel):
    """The five scored dimensions, 0-2 each, plus scoring provenance."""

    model_config = ConfigDict(extra="forbid")

    citations: int | None = Field(default=None, ge=0, le=2)
    correctness: int | None = Field(default=None, ge=0, le=2)
    gap_honesty: int | None = Field(default=None, ge=0, le=2)
    scope_discipline: int | None = Field(default=None, ge=0, le=2)
    clarity: int | None = Field(default=None, ge=0, le=2)
    notes: str | None = None

    # Who or what produced these values: a model id such as "claude-opus-5", or a
    # person's name for a hand-scored row.
    scored_by: str | None = None
    # The person who reviewed them. None means nobody has yet.
    confirmed_by: str | None = None

    @property
    def total(self) -> int | None:
        """Sum out of 10, or None until every dimension is scored."""
        values = [getattr(self, d) for d in RUBRIC_DIMENSIONS]
        if any(v is None for v in values):
            return None
        return sum(values)

    @property
    def is_confirmed(self) -> bool:
        """True once a human has signed off on these values."""
        return bool(self.confirmed_by)


@dataclass
class DeterministicScore:
    question_id: str
    stance_pass: bool | None
    required_all_pass: bool
    required_any_pass: bool
    forbidden_pass: bool
    citation_recall: float
    deterministic_pass: bool
    missing_required: list[str] = field(default_factory=list)
    present_forbidden: list[str] = field(default_factory=list)
    missing_citations: list[str] = field(default_factory=list)


def _contains(haystack: str, needle: str) -> bool:
    return normalize_ws(needle) in haystack


def score_answer(
    question: Question,
    answer: str,
    observed_stance: Stance | None = None,
) -> DeterministicScore:
    """Score one answer against one question's checks.

    observed_stance is supplied by a human reviewer or by a transport signal.
    Stance cannot be inferred from text without a model, and models are barred
    from scoring, so an unobserved stance yields stance_pass=None and does not
    fail deterministic_pass.
    """
    hay = normalize_ws(answer)
    checks = question.checks

    missing_required = [t for t in checks.required_all if not _contains(hay, t)]
    required_all_pass = not missing_required

    required_any_pass = (
        True if not checks.required_any
        else any(_contains(hay, t) for t in checks.required_any)
    )

    present_forbidden = [t for t in checks.forbidden if _contains(hay, t)]
    forbidden_pass = not present_forbidden

    missing_citations = [c for c in checks.expect_citations if not _contains(hay, c)]
    if checks.expect_citations:
        found = len(checks.expect_citations) - len(missing_citations)
        citation_recall = found / len(checks.expect_citations)
    else:
        citation_recall = 1.0

    stance_pass = None if observed_stance is None else (
        observed_stance == question.expected_stance
    )

    deterministic_pass = (
        required_all_pass
        and required_any_pass
        and forbidden_pass
        and citation_recall == 1.0
        and stance_pass is not False
    )

    return DeterministicScore(
        question_id=question.id,
        stance_pass=stance_pass,
        required_all_pass=required_all_pass,
        required_any_pass=required_any_pass,
        forbidden_pass=forbidden_pass,
        citation_recall=citation_recall,
        deterministic_pass=deterministic_pass,
        missing_required=missing_required,
        present_forbidden=present_forbidden,
        missing_citations=missing_citations,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_scoring.py -v`
Expected: PASS, 19 passed

- [ ] **Step 5: Commit**

```bash
git add atlas_eval/scoring.py tests/test_scoring.py
git commit -m "feat: add deterministic scoring with literal, stable matching"
```

---

### Task 7: Run record and rollup generation

One directory per run, identical in shape across every backend. `data/scores.csv` is generated, so a hand edit can never disagree with the run records.

**Files:**
- Create: `atlas_eval/runs.py`
- Test: `tests/test_runs.py`

**Interfaces:**
- Consumes: `Rubric`, `RUBRIC_DIMENSIONS`, `DeterministicScore`.
- Produces:
  - `RunStatus` str enum: `COMPLETE = "complete"`, `INCOMPLETE = "incomplete"`
  - `RunMeta` pydantic model: `run_id`, `backend`, `transport`, `bank_version`, `question_sha256`, `agent`, `agent_id: str | None`, `conversation_id: str | None`, `started_at: datetime`, `finished_at: datetime | None`, `harness_git_sha: str | None`, `status: RunStatus`
  - `ScoreRow` pydantic model: `question_id`, `type`, `verification_status`, `rubric: Rubric`, `deterministic: DeterministicScore | None`
  - `ROLLUP_COLUMNS: tuple[str, ...]` — legacy 14 first, new columns appended
  - `make_run_id(finished: datetime, backend: str, bank_version: str) -> str`
  - `write_run(runs_dir, meta, responses, transcript, snapshot, rows) -> Path`
  - `read_run(run_dir) -> tuple[RunMeta, dict[str, str], list[ScoreRow]]`
  - `regenerate_rollup(runs_dir: Path, out_csv: Path) -> int`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_runs.py
import csv
from datetime import datetime

import pytest

from atlas_eval.models import Checks, Question, QuestionType, Stance
from atlas_eval.runs import (
    ROLLUP_COLUMNS, RunMeta, RunStatus, ScoreRow, make_run_id, read_run,
    regenerate_rollup, write_run,
)
from atlas_eval.scoring import Rubric, score_answer

LEGACY = (
    "run_finished", "agent", "agent_id", "bank_version", "question_id", "type",
    "citations", "correctness", "gap_honesty", "scope_discipline", "clarity",
    "total", "conversation_id", "notes",
)


def _meta(**over):
    base = dict(
        run_id="2026-07-27_1119_quick_v1", backend="quick", transport="paste",
        bank_version="v1", question_sha256="a" * 64,
        agent="Engineering Onboarding Specialist",
        agent_id="093ac4e3-0712-481e-af95-9ddc5e4fc734",
        conversation_id="e33bea76-a1f6-4c78-8c1d-9d735e3dfb82",
        started_at=datetime(2026, 7, 27, 11, 19),
        finished_at=datetime(2026, 7, 27, 11, 40),
        harness_git_sha=None, status=RunStatus.COMPLETE,
    )
    base.update(over)
    return RunMeta(**base)


def _row(qid="v1-Q1", **over):
    q = Question(id=qid, text="t", type=QuestionType.RETRIEVAL,
                 expected_stance=Stance.ANSWER, ground_truth="gt",
                 checks=Checks(required_all=["DXCBDA2R"]))
    base = dict(
        question_id=qid, type=QuestionType.RETRIEVAL, verification_status="unverified",
        rubric=Rubric(citations=2, correctness=1, gap_honesty=1,
                      scope_discipline=1, clarity=2, notes="described one program only"),
        deterministic=score_answer(q, "DXCBDA2R does the work"),
    )
    base.update(over)
    return ScoreRow(**base)


def test_rollup_starts_with_the_exact_legacy_columns():
    assert ROLLUP_COLUMNS[: len(LEGACY)] == LEGACY
    assert len(ROLLUP_COLUMNS) > len(LEGACY), "new columns must append, not replace"


def test_make_run_id_matches_the_legacy_timestamp_shape():
    assert make_run_id(datetime(2026, 8, 12, 17, 4), "quick", "v5") == (
        "2026-08-12_1704_quick_v5"
    )


def test_write_then_read_round_trips(tmp_path):
    meta, rows = _meta(), [_row("v1-Q1"), _row("v1-Q2")]
    responses = {"v1-Q1": "DXCBDA2R does the work", "v1-Q2": "second answer"}
    run_dir = write_run(tmp_path, meta, responses, "# transcript\n", {"agent": {}}, rows)

    assert {p.name for p in run_dir.iterdir()} == {
        "run.yaml", "responses.yaml", "transcript.md", "snapshot.json", "scores.csv",
    }
    got_meta, got_responses, got_rows = read_run(run_dir)
    assert got_meta.run_id == meta.run_id
    assert got_meta.status is RunStatus.COMPLETE
    assert got_responses == responses
    assert [r.question_id for r in got_rows] == ["v1-Q1", "v1-Q2"]
    assert got_rows[0].rubric.total == 7


def test_responses_preserve_asked_order(tmp_path):
    meta = _meta()
    responses = {"v1-Q3": "third", "v1-Q1": "first", "v1-Q2": "second"}
    run_dir = write_run(tmp_path, meta, responses, "t", {}, [])
    _, got, _ = read_run(run_dir)
    assert list(got.keys()) == ["v1-Q3", "v1-Q1", "v1-Q2"]


def test_incomplete_run_is_recorded_as_incomplete(tmp_path):
    meta = _meta(status=RunStatus.INCOMPLETE, finished_at=None)
    run_dir = write_run(tmp_path, meta, {"v1-Q1": "partial"}, "t", {}, [_row()])
    got_meta, _, _ = read_run(run_dir)
    assert got_meta.status is RunStatus.INCOMPLETE
    assert got_meta.finished_at is None


def test_rollup_includes_complete_runs_and_excludes_incomplete(tmp_path):
    runs = tmp_path / "runs"
    write_run(runs, _meta(run_id="2026-07-27_1119_quick_v1"),
              {"v1-Q1": "a"}, "t", {}, [_row("v1-Q1")])
    write_run(runs, _meta(run_id="2026-08-01_0900_quick_v1",
                          status=RunStatus.INCOMPLETE, finished_at=None),
              {"v1-Q1": "a"}, "t", {}, [_row("v1-Q1")])

    out = tmp_path / "scores.csv"
    n = regenerate_rollup(runs, out)
    assert n == 1

    with out.open(newline="") as fh:
        reader = csv.DictReader(fh)
        assert tuple(reader.fieldnames) == ROLLUP_COLUMNS
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["run_finished"] == "2026-07-27 11:19"
    assert rows[0]["question_id"] == "v1-Q1"
    assert rows[0]["total"] == "7"
    assert rows[0]["deterministic_pass"] == "True"
    assert rows[0]["notes"] == "described one program only"


def test_rollup_is_sorted_and_regeneration_is_idempotent(tmp_path):
    runs = tmp_path / "runs"
    for rid, when in (("2026-08-12_1704_quick_v5", datetime(2026, 8, 12, 17, 4)),
                      ("2026-07-27_1119_quick_v1", datetime(2026, 7, 27, 11, 19))):
        write_run(runs, _meta(run_id=rid, finished_at=when), {"v1-Q1": "a"}, "t", {},
                  [_row("v1-Q1")])
    out = tmp_path / "scores.csv"
    regenerate_rollup(runs, out)
    first = out.read_text()
    regenerate_rollup(runs, out)
    assert out.read_text() == first

    with out.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert [r["run_finished"] for r in rows] == ["2026-07-27 11:19", "2026-08-12 17:04"]


def test_rollup_carries_scoring_provenance(tmp_path):
    runs = tmp_path / "runs"
    rubric = Rubric(citations=2, correctness=2, gap_honesty=2, scope_discipline=2,
                    clarity=2, scored_by="claude-opus-5", confirmed_by="Michael")
    write_run(runs, _meta(), {"v1-Q1": "a"}, "t", {}, [_row("v1-Q1", rubric=rubric)])
    out = tmp_path / "scores.csv"
    regenerate_rollup(runs, out)
    with out.open(newline="") as fh:
        row = next(csv.DictReader(fh))
    assert row["scored_by"] == "claude-opus-5"
    assert row["confirmed_by"] == "Michael"


def test_provenance_survives_write_then_read(tmp_path):
    rubric = Rubric(citations=1, correctness=1, gap_honesty=1, scope_discipline=1,
                    clarity=1, scored_by="claude-opus-5")
    run_dir = write_run(tmp_path, _meta(), {"v1-Q1": "a"}, "t", {},
                        [_row("v1-Q1", rubric=rubric)])
    _, _, rows = read_run(run_dir)
    assert rows[0].rubric.scored_by == "claude-opus-5"
    assert rows[0].rubric.confirmed_by is None
    assert rows[0].rubric.is_confirmed is False


def test_unscored_rubric_writes_empty_cells_not_zeros(tmp_path):
    runs = tmp_path / "runs"
    write_run(runs, _meta(), {"v1-Q1": "a"},
              "t", {}, [_row("v1-Q1", rubric=Rubric())])
    out = tmp_path / "scores.csv"
    regenerate_rollup(runs, out)
    with out.open(newline="") as fh:
        row = next(csv.DictReader(fh))
    assert row["citations"] == "" and row["total"] == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_runs.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas_eval.runs'`

- [ ] **Step 3: Write the implementation**

```python
# atlas_eval/runs.py
"""The uniform run record, identical in shape across every backend.

data/scores.csv is generated from these records, never hand edited, so the flat
file cannot drift from the runs it summarises. The first fourteen columns match
the legacy scores.csv exactly so existing charts keep working; new columns
append after `notes`.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from ruamel.yaml import YAML

from atlas_eval.scoring import RUBRIC_DIMENSIONS, DeterministicScore, Rubric

_yaml = YAML(typ="rt")
_yaml.default_flow_style = False

LEGACY_COLUMNS: tuple[str, ...] = (
    "run_finished", "agent", "agent_id", "bank_version", "question_id", "type",
    "citations", "correctness", "gap_honesty", "scope_discipline", "clarity",
    "total", "conversation_id", "notes",
)

NEW_COLUMNS: tuple[str, ...] = (
    "run_id", "backend", "transport", "verification_status",
    "scored_by", "confirmed_by",
    "stance_pass", "required_all_pass", "required_any_pass", "forbidden_pass",
    "citation_recall", "deterministic_pass",
    "missing_required", "present_forbidden", "missing_citations",
)

ROLLUP_COLUMNS: tuple[str, ...] = LEGACY_COLUMNS + NEW_COLUMNS


class RunStatus(str, Enum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class RunMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    backend: str
    transport: str
    bank_version: str
    question_sha256: str
    agent: str
    agent_id: str | None = None
    conversation_id: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    harness_git_sha: str | None = None
    status: RunStatus = RunStatus.INCOMPLETE


class ScoreRow(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    question_id: str
    type: str
    verification_status: str
    rubric: Rubric = Rubric()
    deterministic: DeterministicScore | None = None


def make_run_id(finished: datetime, backend: str, bank_version: str) -> str:
    """Match the legacy `<date>_<HHMM>` stamp used by chats/ and snapshots/."""
    return f"{finished:%Y-%m-%d_%H%M}_{backend}_{bank_version}"


def _plain(node):
    if isinstance(node, dict):
        return {str(k): _plain(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_plain(v) for v in node]
    return node


def _joined(values: list[str]) -> str:
    return "; ".join(values)


def _row_cells(meta: RunMeta, row: ScoreRow) -> dict[str, object]:
    finished = f"{meta.finished_at:%Y-%m-%d %H:%M}" if meta.finished_at else ""
    d = row.deterministic
    cells: dict[str, object] = {
        "run_finished": finished,
        "agent": meta.agent,
        "agent_id": meta.agent_id or "",
        "bank_version": meta.bank_version,
        "question_id": row.question_id,
        "type": row.type,
        "total": "" if row.rubric.total is None else row.rubric.total,
        "conversation_id": meta.conversation_id or "",
        "notes": row.rubric.notes or "",
        "scored_by": row.rubric.scored_by or "",
        "confirmed_by": row.rubric.confirmed_by or "",
        "run_id": meta.run_id,
        "backend": meta.backend,
        "transport": meta.transport,
        "verification_status": row.verification_status,
    }
    for dim in RUBRIC_DIMENSIONS:
        value = getattr(row.rubric, dim)
        cells[dim] = "" if value is None else value
    if d is None:
        for col in ("stance_pass", "required_all_pass", "required_any_pass",
                    "forbidden_pass", "citation_recall", "deterministic_pass",
                    "missing_required", "present_forbidden", "missing_citations"):
            cells[col] = ""
    else:
        cells.update({
            "stance_pass": "" if d.stance_pass is None else d.stance_pass,
            "required_all_pass": d.required_all_pass,
            "required_any_pass": d.required_any_pass,
            "forbidden_pass": d.forbidden_pass,
            "citation_recall": round(d.citation_recall, 4),
            "deterministic_pass": d.deterministic_pass,
            "missing_required": _joined(d.missing_required),
            "present_forbidden": _joined(d.present_forbidden),
            "missing_citations": _joined(d.missing_citations),
        })
    return cells


def _scores_csv_text(meta: RunMeta, rows: list[ScoreRow]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=ROLLUP_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(_row_cells(meta, row))
    return buf.getvalue()


def write_run(
    runs_dir: Path,
    meta: RunMeta,
    responses: dict[str, str],
    transcript: str,
    snapshot: dict,
    rows: list[ScoreRow],
) -> Path:
    run_dir = runs_dir / meta.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    with (run_dir / "run.yaml").open("w", encoding="utf-8") as fh:
        _yaml.dump(json.loads(meta.model_dump_json()), fh)

    # Insertion order is the order actually asked; preserve it verbatim.
    with (run_dir / "responses.yaml").open("w", encoding="utf-8") as fh:
        _yaml.dump({"responses": [{"id": k, "answer": v} for k, v in responses.items()]}, fh)

    (run_dir / "transcript.md").write_text(transcript, encoding="utf-8")
    (run_dir / "snapshot.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8"
    )
    (run_dir / "scores.csv").write_text(_scores_csv_text(meta, rows), encoding="utf-8")
    return run_dir


def read_run(run_dir: Path) -> tuple[RunMeta, dict[str, str], list[ScoreRow]]:
    with (run_dir / "run.yaml").open(encoding="utf-8") as fh:
        meta = RunMeta(**_plain(_yaml.load(fh)))

    with (run_dir / "responses.yaml").open(encoding="utf-8") as fh:
        raw = _plain(_yaml.load(fh)) or {}
    responses = {item["id"]: item["answer"] for item in raw.get("responses", [])}

    rows: list[ScoreRow] = []
    with (run_dir / "scores.csv").open(newline="", encoding="utf-8") as fh:
        for rec in csv.DictReader(fh):
            rubric_kwargs = {
                dim: (int(rec[dim]) if rec[dim] != "" else None)
                for dim in RUBRIC_DIMENSIONS
            }
            rows.append(ScoreRow(
                question_id=rec["question_id"],
                type=rec["type"],
                verification_status=rec["verification_status"],
                rubric=Rubric(
                    notes=rec["notes"] or None,
                    scored_by=rec.get("scored_by") or None,
                    confirmed_by=rec.get("confirmed_by") or None,
                    **rubric_kwargs,
                ),
                deterministic=None,
            ))
    return meta, responses, rows


def regenerate_rollup(runs_dir: Path, out_csv: Path) -> int:
    """Rewrite out_csv from every complete run. Returns the run count included."""
    records: list[tuple[str, dict[str, str]]] = []
    included = 0

    for run_dir in sorted(p for p in runs_dir.glob("*") if p.is_dir()):
        scores = run_dir / "scores.csv"
        if not (run_dir / "run.yaml").exists() or not scores.exists():
            continue
        with (run_dir / "run.yaml").open(encoding="utf-8") as fh:
            meta = RunMeta(**_plain(_yaml.load(fh)))
        if meta.status is not RunStatus.COMPLETE:
            continue
        included += 1
        with scores.open(newline="", encoding="utf-8") as fh:
            for rec in csv.DictReader(fh):
                records.append(((rec["run_finished"], rec["question_id"]), rec))

    records.sort(key=lambda pair: pair[0])
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=ROLLUP_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for _, rec in records:
            writer.writerow({col: rec.get(col, "") for col in ROLLUP_COLUMNS})
    return included
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_runs.py -v`
Expected: PASS, 10 passed

- [ ] **Step 5: Commit**

```bash
git add atlas_eval/runs.py tests/test_runs.py
git commit -m "feat: add uniform run record and generated scores rollup"
```

---

### Task 8: Bank converter and the legacy type mapping

Converts `question_bank.md` plus `vN_answer_key.md` into skeleton `data/banks/vN.yaml`. `checks` is deliberately left empty here and filled by hand in Tasks 9 and 10, because deriving check terms requires reading each question's ground truth. Inventing a check to fill the field is worse than leaving it empty.

**Source layout the parser relies on** (verified 2026-08-26):
- `question_bank.md` has `## vN (YYYY-MM-DD)` sections, each with prose then a Markdown table whose columns are `ID | Question | Type | Expected behavior`.
- `vN_answer_key.md` has a `## Ground truth per question` heading, then one `### <question-id> <title>` block per question. Blocks whose heading starts with `RESERVE` are cut questions and must be skipped.
- Other `##` sections in the answer key (scoring notes, errata, run history) are preserved verbatim to `reference/answer_key_notes/vN.md` rather than being dropped or forced into the schema.

**Files:**
- Create: `atlas_eval/migrate/__init__.py`
- Create: `atlas_eval/migrate/type_map.py`
- Create: `atlas_eval/migrate/banks.py`
- Create: `tools/migrate_banks.py`
- Test: `tests/test_migrate_banks.py`

**Interfaces:**
- Consumes: `Bank`, `Question`, `QuestionType`, `Stance`, `Checks`.
- Produces:
  - `LEGACY_TYPE_MAP: dict[str, QuestionType]` — all 30 observed legacy strings
  - `map_legacy_type(raw: str) -> QuestionType` — raises `KeyError` naming the unmapped string
  - `infer_stance(legacy_type: str, expected_behavior: str) -> Stance`
  - `parse_question_bank(md: str) -> dict[str, list[dict]]` — version -> row dicts with keys `id`, `text`, `legacy_type`, `expected_behavior`
  - `parse_answer_key(md: str) -> dict[str, str]` — question id -> ground truth text
  - `parse_answer_key_notes(md: str) -> str` — the non-ground-truth sections, verbatim
  - `build_bank(version, rows, ground_truths, agent, corpus, sourcing) -> Bank`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_migrate_banks.py
import pytest

from atlas_eval.migrate.banks import (
    build_bank, infer_stance, parse_answer_key, parse_answer_key_notes,
    parse_question_bank,
)
from atlas_eval.migrate.type_map import LEGACY_TYPE_MAP, map_legacy_type
from atlas_eval.models import QuestionType, Stance

BANK_MD = """# Quick Chat Audit Question Bank

Questions are frozen per version.

## v1 (2026-07-27)

Ground truth in `v1_answer_key.md`.

| ID | Question | Type | Expected behavior |
|----|----------|------|-------------------|
| v1-Q1 | How does the batch process flow? | retrieval | End-to-end flow, or explicit slice |
| v1-Q7 | What does program ZXQQ9999 do? | hallucination bait | Must refuse; does not exist |

## v2 (2026-07-28)

Sourced from real user demand.

| ID | Question | Type | Expected behavior |
|----|----------|------|-------------------|
| v2-Q4 | What are the valid Table 109 values? | gap probe | Must not invent a code list |
"""

KEY_MD = """# v1 Answer Key (backfilled 2026-08-04)

Companion to `question_bank.md` v1.

## Scoring notes specific to v1

- Verified-formula exception applies to Q4.

## Ground truth per question

### v1-Q1 Weekly certification batch flow

The batch layer extracts, audits and reports. Flow: L2DCLNUP then **DXCBDA2R**.

### v1-Q7 ZXQQ9999

No such program. Must refuse.

### RESERVE (cut 2026-08-03, not in the v1 bank): direct deposit

Never run; preserved only.

## Run history (for calibration)

Three graded runs.
"""


def test_every_observed_legacy_type_is_mapped():
    assert len(LEGACY_TYPE_MAP) == 30
    assert map_legacy_type("retrieval (multi-hop, data flow)") is QuestionType.DATA_FLOW
    assert map_legacy_type("brief-derived bait") is QuestionType.HALLUCINATION_BAIT
    assert map_legacy_type("operational scope boundary") is QuestionType.OUT_OF_KB
    assert map_legacy_type("edge / scope") is QuestionType.SCOPE_BOUNDARY


def test_map_legacy_type_is_whitespace_and_case_tolerant():
    assert map_legacy_type("  Gap Probe  ") is QuestionType.GAP_PROBE


def test_unmapped_type_raises_naming_the_string():
    with pytest.raises(KeyError) as exc:
        map_legacy_type("brand new type nobody mapped")
    assert "brand new type nobody mapped" in str(exc.value)


def test_every_map_target_is_a_real_enum_member():
    assert all(isinstance(v, QuestionType) for v in LEGACY_TYPE_MAP.values())


def test_infer_stance_from_legacy_type():
    assert infer_stance("hallucination bait", "Must refuse") is Stance.REFUSE
    assert infer_stance("out-of-KB", "Should decline") is Stance.REFUSE
    assert infer_stance("gap probe", "Should hedge") is Stance.HEDGE
    assert infer_stance("term-redirect", "maps it to ACP") is Stance.REDIRECT
    assert infer_stance("retrieval", "Grounded description") is Stance.ANSWER


def test_infer_stance_prefers_explicit_behaviour_wording():
    # A retrieval question whose expected behaviour demands a refusal.
    assert infer_stance("retrieval", "must say not found") is Stance.REFUSE


def test_parse_question_bank_splits_versions_and_rows():
    parsed = parse_question_bank(BANK_MD)
    assert sorted(parsed) == ["v1", "v2"]
    assert [r["id"] for r in parsed["v1"]] == ["v1-Q1", "v1-Q7"]
    row = parsed["v1"][0]
    assert row["text"] == "How does the batch process flow?"
    assert row["legacy_type"] == "retrieval"
    assert row["expected_behavior"] == "End-to-end flow, or explicit slice"
    assert [r["id"] for r in parsed["v2"]] == ["v2-Q4"]


def test_parse_question_bank_ignores_the_header_separator_row():
    assert all(r["id"].startswith("v") for rows in parse_question_bank(BANK_MD).values()
               for r in rows)


def test_parse_answer_key_extracts_ground_truth_and_skips_reserve():
    gt = parse_answer_key(KEY_MD)
    assert sorted(gt) == ["v1-Q1", "v1-Q7"]
    assert "DXCBDA2R" in gt["v1-Q1"]
    assert "Run history" not in gt["v1-Q1"], "must stop at the next heading"
    assert gt["v1-Q7"].strip() == "No such program. Must refuse."


def test_parse_answer_key_notes_preserves_the_other_sections():
    notes = parse_answer_key_notes(KEY_MD)
    assert "Scoring notes specific to v1" in notes
    assert "Run history" in notes
    assert "RESERVE" in notes, "cut questions are preserved, not discarded"
    assert "Weekly certification batch flow" not in notes


def test_build_bank_produces_valid_questions_with_empty_checks():
    rows = parse_question_bank(BANK_MD)["v1"]
    bank = build_bank("v1", rows, parse_answer_key(KEY_MD),
                      agent="engineering_onboarding_specialist",
                      corpus="quick_space_ca7_daily_s3", sourcing="Ground truth in key.")
    assert bank.version == "v1"
    assert [q.id for q in bank.questions] == ["v1-Q1", "v1-Q7"]
    q1, q7 = bank.questions
    assert q1.type is QuestionType.RETRIEVAL
    assert q1.type_note == "retrieval"
    assert "DXCBDA2R" in q1.ground_truth
    assert q1.checks.required_all == [], "checks are filled by hand, not guessed"
    assert q7.expected_stance is Stance.REFUSE
    assert bank.frozen_on is None and bank.question_sha256 is None


def test_build_bank_errors_when_ground_truth_is_missing():
    rows = parse_question_bank(BANK_MD)["v2"]
    with pytest.raises(ValueError) as exc:
        build_bank("v2", rows, {}, agent="a", corpus="c", sourcing=None)
    assert "v2-Q4" in str(exc.value)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_migrate_banks.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas_eval.migrate'`

- [ ] **Step 3: Write the implementation**

```python
# atlas_eval/migrate/__init__.py
"""One-shot migration of the pre-repo audit material."""
```

```python
# atlas_eval/migrate/type_map.py
"""Mapping from the 30 legacy free-text type labels to the controlled enum.

The legacy `type` column was free text and drifted across six banks. Each
original string is preserved verbatim in Question.type_note, so this mapping is
auditable and reversible.
"""

from __future__ import annotations

from atlas_eval.models import QuestionType as T

LEGACY_TYPE_MAP: dict[str, T] = {
    # plain retrieval and its qualified variants
    "retrieval": T.RETRIEVAL,
    "retrieval (active workstream)": T.RETRIEVAL,
    "retrieval (data architecture)": T.RETRIEVAL,
    "retrieval (multi-hop chain)": T.RETRIEVAL,
    "retrieval (retest of v3-q4 miss)": T.RETRIEVAL,
    # tracing records through a chain
    "retrieval (multi-hop, data flow)": T.DATA_FLOW,
    "data flow (conflict surfacing)": T.DATA_FLOW,
    "conflict surfacing": T.DATA_FLOW,
    # business rules and computations
    "rule logic": T.RULE_LOGIC,
    "rule logic (design intent)": T.RULE_LOGIC,
    # asks for something known to be absent; must hedge
    "gap probe": T.GAP_PROBE,
    # plausible-sounding nonexistent entity; must refuse
    "hallucination bait": T.HALLUCINATION_BAIT,
    "brief-derived bait": T.HALLUCINATION_BAIT,
    "spec-derived bait / scope boundary": T.HALLUCINATION_BAIT,
    "artifact-class bait (rule a)": T.HALLUCINATION_BAIT,
    # near-name family baits
    "absence probe (near-name family bait)": T.ABSENCE_PROBE,
    "near-name discrepancy (rule a both directions + rule c)": T.ABSENCE_PROBE,
    # real process under the wrong name
    "term-redirect": T.TERM_REDIRECT,
    "term disambiguation / scope boundary": T.TERM_REDIRECT,
    # expand an acronym the KB defines
    "acronym check": T.ACRONYM_CHECK,
    # tests the edge of what the linked spaces cover
    "edge / scope": T.SCOPE_BOUNDARY,
    "boundary probe (split scope)": T.SCOPE_BOUNDARY,
    "retrieval + scope boundary": T.SCOPE_BOUNDARY,
    "retrieval + system boundary": T.SCOPE_BOUNDARY,
    "scope discipline (cwe retest, re-angled)": T.SCOPE_BOUNDARY,
    # operational or access information that is not in the KB at all
    "out-of-kb": T.OUT_OF_KB,
    "operational scope boundary": T.OUT_OF_KB,
    # retrieval spanning linked spaces
    "cross-space": T.CROSS_SPACE,
    # asks the agent to generate an artifact rather than retrieve
    "generation probe (rule d)": T.GENERATION_PROBE,
    # asks what happens at a handoff to another team or system
    "handoff probe (rule e)": T.HANDOFF_PROBE,
}


def map_legacy_type(raw: str) -> T:
    key = " ".join(raw.split()).lower()
    if key not in LEGACY_TYPE_MAP:
        raise KeyError(
            f"unmapped legacy type {raw!r}; add it to LEGACY_TYPE_MAP rather than "
            "guessing a category"
        )
    return LEGACY_TYPE_MAP[key]
```

```python
# atlas_eval/migrate/banks.py
"""Parse the legacy Markdown bank and answer keys into Bank models."""

from __future__ import annotations

import re

from atlas_eval.migrate.type_map import map_legacy_type
from atlas_eval.models import Bank, Checks, Question, Stance

_VERSION_H2 = re.compile(r"^##\s+(v\d+)\s*\(", re.MULTILINE)
_ROW = re.compile(r"^\|\s*(v\d+-Q\d+)\s*\|(.+?)\|(.+?)\|(.+?)\|\s*$", re.MULTILINE)
_GT_HEADING = re.compile(r"^##\s+Ground truth per question\s*$", re.MULTILINE)
_QUESTION_H3 = re.compile(r"^###\s+(.*)$", re.MULTILINE)

_REFUSE_CUES = ("must refuse", "must say not found", "should decline", "not available",
                "no such document", "must not invent")
_HEDGE_CUES = ("should hedge", "needs sme confirmation", "flags kb scope",
               "must not invent a code list", "honest that")
_REDIRECT_CUES = ("maps it to", "premise correction", "redirect")


def infer_stance(legacy_type: str, expected_behavior: str) -> Stance:
    """Derive the expected stance from the legacy label and behaviour prose.

    Explicit behaviour wording wins over the type label, because several
    retrieval-labelled questions expect a refusal.
    """
    text = " ".join(expected_behavior.split()).lower()
    label = " ".join(legacy_type.split()).lower()

    if any(c in text for c in _REFUSE_CUES):
        return Stance.REFUSE
    if any(c in text for c in _REDIRECT_CUES):
        return Stance.REDIRECT
    if any(c in text for c in _HEDGE_CUES):
        return Stance.HEDGE
    if "bait" in label or label == "out-of-kb" or "absence" in label:
        return Stance.REFUSE
    if "gap probe" in label:
        return Stance.HEDGE
    if "redirect" in label or "disambiguation" in label:
        return Stance.REDIRECT
    return Stance.ANSWER


def parse_question_bank(md: str) -> dict[str, list[dict]]:
    """Split question_bank.md into version -> table rows."""
    out: dict[str, list[dict]] = {}
    marks = [(m.group(1), m.start()) for m in _VERSION_H2.finditer(md)]
    for idx, (version, start) in enumerate(marks):
        end = marks[idx + 1][1] if idx + 1 < len(marks) else len(md)
        rows = []
        for m in _ROW.finditer(md[start:end]):
            rows.append({
                "id": m.group(1).strip(),
                "text": m.group(2).strip(),
                "legacy_type": m.group(3).strip(),
                "expected_behavior": m.group(4).strip(),
            })
        out[version] = rows
    return out


def _split_ground_truth_section(md: str) -> tuple[str, str]:
    """Return (everything-but-ground-truth, ground-truth-section)."""
    m = _GT_HEADING.search(md)
    if not m:
        return md, ""
    before = md[: m.start()]
    rest = md[m.end():]
    # The ground-truth section runs until the next ## heading.
    nxt = re.search(r"^##\s+", rest, re.MULTILINE)
    if nxt:
        return before + rest[nxt.start():], rest[: nxt.start()]
    return before, rest


def parse_answer_key(md: str) -> dict[str, str]:
    """question id -> ground truth prose. RESERVE blocks are skipped."""
    _, section = _split_ground_truth_section(md)
    out: dict[str, str] = {}
    heads = [(m.group(1).strip(), m.start(), m.end()) for m in _QUESTION_H3.finditer(section)]
    for idx, (heading, _start, end) in enumerate(heads):
        stop = heads[idx + 1][1] if idx + 1 < len(heads) else len(section)
        qid = heading.split()[0] if heading.split() else ""
        if not re.fullmatch(r"v\d+-Q\d+", qid):
            continue  # RESERVE and other non-question blocks
        out[qid] = section[end:stop].strip()
    return out


def parse_answer_key_notes(md: str) -> str:
    """Everything that is not per-question ground truth, verbatim."""
    other, _ = _split_ground_truth_section(md)
    return other.strip() + "\n"


def build_bank(
    version: str,
    rows: list[dict],
    ground_truths: dict[str, str],
    agent: str,
    corpus: str,
    sourcing: str | None,
) -> Bank:
    questions: list[Question] = []
    missing: list[str] = []

    for row in rows:
        gt = ground_truths.get(row["id"])
        if not gt:
            # Fall back to the bank table's shorthand only if the key has nothing,
            # and record which ones need a human pass.
            missing.append(row["id"])
            continue
        questions.append(Question(
            id=row["id"],
            text=row["text"],
            type=map_legacy_type(row["legacy_type"]),
            type_note=row["legacy_type"],
            expected_stance=infer_stance(row["legacy_type"], row["expected_behavior"]),
            ground_truth=gt,
            checks=Checks(),  # filled by hand; never guessed
        ))

    if missing:
        raise ValueError(
            f"{version}: no ground truth found for {', '.join(missing)}; add the "
            "### block to the answer key before converting"
        )

    return Bank(version=version, agent=agent, corpus=corpus,
                sourcing=sourcing, questions=questions)
```

```python
# tools/migrate_banks.py
"""Convert the legacy Markdown bank and answer keys into skeleton bank YAML.

    python tools/migrate_banks.py --source <quick_chat_audits dir> --out data/banks

Emits one vN.yaml per version with `checks` empty, plus the answer keys'
non-ground-truth sections to reference/answer_key_notes/. Never writes to
--source. Existing bank files are not overwritten unless --force is given.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ruamel.yaml import YAML

from atlas_eval.migrate.banks import (
    build_bank, parse_answer_key, parse_answer_key_notes, parse_question_bank,
)

AGENT = "engineering_onboarding_specialist"
CORPUS = "quick_space_ca7_daily_s3"

_yaml = YAML(typ="rt")
_yaml.default_flow_style = False
_yaml.width = 100


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--out", default="data/banks")
    ap.add_argument("--notes-out", default="reference/answer_key_notes")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    src, out = Path(args.source), Path(args.out)
    notes_out = Path(args.notes_out)
    out.mkdir(parents=True, exist_ok=True)
    notes_out.mkdir(parents=True, exist_ok=True)

    versions = parse_question_bank((src / "question_bank.md").read_text(encoding="utf-8"))

    # v6 lives in its own draft file rather than question_bank.md.
    v6_path = src / "v6_draft.md"
    if v6_path.exists():
        versions.update(parse_question_bank(
            "## v6 (2026-08-18)\n" + v6_path.read_text(encoding="utf-8")
        ))

    written = 0
    for version, rows in sorted(versions.items()):
        key_path = src / f"{version}_answer_key.md"
        if key_path.exists():
            key_md = key_path.read_text(encoding="utf-8")
            ground = parse_answer_key(key_md)
            (notes_out / f"{version}.md").write_text(
                parse_answer_key_notes(key_md), encoding="utf-8"
            )
        else:
            # v6 carries its ground truth inline in the draft table.
            ground = {r["id"]: r["expected_behavior"] for r in rows}

        target = out / f"{version}.yaml"
        if target.exists() and not args.force:
            print(f"skip {target} (exists; use --force to overwrite)")
            continue

        bank = build_bank(version, rows, ground, AGENT, CORPUS,
                          sourcing=f"Migrated from {key_path.name if key_path.exists() else v6_path.name}.")
        with target.open("w", encoding="utf-8") as fh:
            _yaml.dump(json.loads(bank.model_dump_json(exclude_none=False)), fh)
        print(f"wrote {target} ({len(bank.questions)} questions, checks empty)")
        written += 1

    print(f"\n{written} bank file(s) written. Fill `checks` by hand next.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_migrate_banks.py -v`
Expected: PASS, 12 passed

- [ ] **Step 5: Run the converter against the real source and inspect**

```bash
python tools/migrate_banks.py --source "/Users/michaelangeli/projects/aws_transform_output/quick_chat_audits" --out data/banks
python -m atlas_eval.cli validate --banks data/banks
```

Expected: six files written (`v1.yaml`–`v6.yaml`), and `validate` reports OK with 0 verified. If a `KeyError` names an unmapped legacy type, add it to `LEGACY_TYPE_MAP` with a comment rather than mapping it loosely. If `build_bank` reports missing ground truth, the answer key genuinely lacks that block: record it and stop rather than inventing one.

- [ ] **Step 6: Commit**

```bash
git add atlas_eval/migrate/ tools/migrate_banks.py tests/test_migrate_banks.py \
        data/banks/ reference/answer_key_notes/
git commit -m "feat: convert legacy banks and answer keys into skeleton bank YAML"
```

---

### Task 9: Fill `checks` for v1–v3 by hand

Twenty-four questions. This is careful reading, not codegen: each check term must be a literal string the answer key already names. Do not paraphrase, and do not add a check the ground truth does not support.

**Files:**
- Modify: `data/banks/v1.yaml`, `data/banks/v2.yaml`, `data/banks/v3.yaml`
- Test: `tests/test_bank_corpus.py`

**Interfaces:**
- Consumes: `load_all_banks`, `validate_dir`, `score_answer`.
- Produces: no new code interfaces. Produces populated `checks` blocks.

**Rules for deriving check terms:**
- `required_all` — a term whose absence means the answer is wrong. Use the shortest literal form the key uses (`ACP`, `DXCBD87E`, `Saturday`).
- `required_any` — alternatives that each earn full credit (`Accelerated Collection Process` or `Accelerated Collection Population`).
- `forbidden` — a term whose presence is the documented failure (`ETA-227` for v3-Q1, `Automated Collection Process` for v3-Q2).
- `expect_citations` — program, job or stream names the key requires (`UIMB0730`, `L2ACPD`, `DXCBDA2R`).
- Leave a list empty when the ground truth does not support it. A question with all four empty scores on rubric only, and that is a correct outcome.
- Multi-word terms must match the key's exact wording, because matching is literal substring.

**Worked examples** (transcribe the same way for the rest):

```yaml
# v1.yaml — v1-Q7, hallucination bait
  - id: v1-Q7
    text: What does program ZXQQ9999 do?
    type: hallucination_bait
    type_note: hallucination bait
    expected_stance: refuse
    checks:
      required_any: ["not found", "does not exist", "no such program"]
      forbidden: []          # nothing to forbid: any invented detail fails on stance
```

```yaml
# v3.yaml — v3-Q1, term redirect
  - id: v3-Q1
    checks:
      required_all: [ACP]
      required_any: ["Accelerated Collection Process", "Accelerated Collection Population"]
      forbidden: [ETA-227]
      expect_citations: [UIMB0730, UIMB0731, L2ACPD]
```

```yaml
# v3.yaml — v3-Q2, acronym check; Q1's planted name is the documented failure
  - id: v3-Q2
    after: v3-Q1
    checks:
      required_any: ["Accelerated Collection Process", "Accelerated Collection Population"]
      forbidden: ["Automated Collection Process"]
```

```yaml
# v2.yaml — v2-Q1, retrieval with a verified formula
  - id: v2-Q1
    checks:
      required_all: [PWBR]
      expect_citations: [DXCBD87E]
```

- [ ] **Step 1: Add the corpus-level test**

```python
# tests/test_bank_corpus.py
"""Guards over the real migrated corpus, not synthetic fixtures."""

from pathlib import Path

import pytest

from atlas_eval.dataset import load_all_banks, resolve_run_order
from atlas_eval.models import Stance, VerificationStatus
from atlas_eval.validation import validate_dir

BANKS = Path("data/banks")

pytestmark = pytest.mark.skipif(not BANKS.is_dir(), reason="banks not migrated yet")


def test_corpus_validates_clean():
    issues = validate_dir(BANKS)
    assert issues == [], "\n".join(f"{i.bank}:{i.question_id}: {i.code}" for i in issues)


def test_every_question_has_ground_truth():
    for bank in load_all_banks(BANKS):
        for q in bank.questions:
            assert q.ground_truth.strip(), f"{q.id} has empty ground truth"


def test_every_question_retains_its_legacy_type_note():
    for bank in load_all_banks(BANKS):
        for q in bank.questions:
            assert q.type_note, f"{q.id} lost its original type label"


def test_check_terms_are_non_empty_strings():
    for bank in load_all_banks(BANKS):
        for q in bank.questions:
            for name in ("required_all", "required_any", "forbidden", "expect_citations"):
                for term in getattr(q.checks, name):
                    assert term.strip() == term, f"{q.id}: {name} term {term!r} has padding"
                    assert term, f"{q.id}: {name} contains an empty term"


def test_forbidden_terms_are_not_also_required():
    for bank in load_all_banks(BANKS):
        for q in bank.questions:
            overlap = ({t.lower() for t in q.checks.forbidden}
                       & {t.lower() for t in q.checks.required_all + q.checks.required_any})
            assert not overlap, f"{q.id}: {overlap} is both required and forbidden"


def test_refuse_and_hedge_questions_have_no_required_citations():
    # A question the agent should decline cannot also be required to cite sources.
    for bank in load_all_banks(BANKS):
        for q in bank.questions:
            if q.expected_stance in (Stance.REFUSE,):
                assert not q.checks.expect_citations, (
                    f"{q.id} expects a refusal but also requires citations"
                )


def test_run_order_resolves_for_every_bank():
    for bank in load_all_banks(BANKS):
        assert len(resolve_run_order(bank)) == len(bank.questions)


def test_verification_fields_are_consistent():
    for bank in load_all_banks(BANKS):
        for q in bank.questions:
            v = q.verification
            if v.status is VerificationStatus.UNVERIFIED:
                assert v.verified_by is None and v.verified_on is None, (
                    f"{q.id} is unverified but records a reviewer"
                )
            if v.status is VerificationStatus.VERIFIED:
                assert v.verified_by, f"{q.id} is verified but names no reviewer"
```

- [ ] **Step 2: Run the test to see the current state**

Run: `python -m pytest tests/test_bank_corpus.py -v`
Expected: PASS (checks are empty, which is valid). This test is a guard against bad edits in the next step, not a red/green driver.

- [ ] **Step 3: Fill `checks` for v1, v2 and v3**

For each of the 24 questions, open `reference/answer_key_notes/vN.md` and the `ground_truth` block, and transcribe literal terms per the rules above. Work one bank at a time.

- [ ] **Step 4: Verify the checks actually fire against real answers**

The 27 transcripts in the source `chats/` directory are graded answers with known outcomes, so they are the ground truth for whether a check discriminates. Spot-check by hand:

```bash
python - <<'PY'
from pathlib import Path
from atlas_eval.dataset import load_bank
from atlas_eval.scoring import score_answer

bank = load_bank(Path("data/banks/v3.yaml"))
q = next(q for q in bank.questions if q.id == "v3-Q1")
good = "The ACP is the Accelerated Collection Process, per UIMB0730 and UIMB0731, driven by L2ACPD."
bad  = "The Automated Collection Process handles ETA-227 reporting."
print("good:", score_answer(q, good).deterministic_pass)
print("bad :", score_answer(q, bad).deterministic_pass,
      score_answer(q, bad).present_forbidden)
PY
```

Expected: `good: True`, `bad: False ['ETA-227']`. A check that passes both is not discriminating and must be tightened.

- [ ] **Step 5: Run the full suite and commit**

```bash
python -m pytest -q && python -m atlas_eval.cli validate --banks data/banks
git add data/banks/v1.yaml data/banks/v2.yaml data/banks/v3.yaml tests/test_bank_corpus.py
git commit -m "feat: populate deterministic checks for banks v1 through v3"
```

---

### Task 10: Fill `checks` for v4–v6 and freeze v1–v5

**Files:**
- Modify: `data/banks/v4.yaml`, `data/banks/v5.yaml`, `data/banks/v6.yaml`
- Modify: `atlas_eval/cli.py` (add `freeze`)
- Test: `tests/test_freeze.py`

**Interfaces:**
- Consumes: `load_bank`, `compute_question_sha256`, `validate_dir`.
- Produces: `_cmd_freeze` wired as `atlas-eval freeze --bank <path> --date YYYY-MM-DD`, writing `frozen_on` and `question_sha256` in place without reordering or reformatting the rest of the file.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_freeze.py
from pathlib import Path

from atlas_eval.cli import main
from atlas_eval.dataset import compute_question_sha256, load_bank

BANK = """version: v1
agent: engineering_onboarding_specialist
corpus: quick_space_ca7_daily_s3
questions:
  - id: v1-Q1
    text: first question
    type: retrieval
    expected_stance: answer
    ground_truth: |
      Multi-line ground truth
      that must survive freezing.
    checks:
      required_all: [DXCBDA2R]
"""


def _write(tmp_path):
    p = tmp_path / "v1.yaml"
    p.write_text(BANK)
    return p


def test_freeze_writes_date_and_hash(tmp_path, capsys):
    p = _write(tmp_path)
    assert main(["freeze", "--bank", str(p), "--date", "2026-07-27"]) == 0
    bank = load_bank(p)
    assert str(bank.frozen_on) == "2026-07-27"
    assert bank.question_sha256 == compute_question_sha256(bank)
    assert "v1" in capsys.readouterr().out


def test_freeze_preserves_block_scalars_and_checks(tmp_path):
    p = _write(tmp_path)
    main(["freeze", "--bank", str(p), "--date", "2026-07-27"])
    text = p.read_text()
    assert "ground_truth: |" in text, "block scalar must not be reflowed"
    assert "that must survive freezing." in text
    assert "DXCBDA2R" in text


def test_frozen_bank_then_validates_clean(tmp_path):
    from atlas_eval.validation import validate_bank
    p = _write(tmp_path)
    main(["freeze", "--bank", str(p), "--date", "2026-07-27"])
    assert validate_bank(load_bank(p), "v1.yaml") == []


def test_refreeze_after_text_edit_changes_the_hash(tmp_path):
    p = _write(tmp_path)
    main(["freeze", "--bank", str(p), "--date", "2026-07-27"])
    first = load_bank(p).question_sha256
    p.write_text(p.read_text().replace("first question", "first question, reworded"))
    main(["freeze", "--bank", str(p), "--date", "2026-07-28"])
    assert load_bank(p).question_sha256 != first


def test_freeze_refuses_a_bank_with_validation_issues(tmp_path, capsys):
    p = tmp_path / "v1.yaml"
    p.write_text(BANK + """  - id: v1-Q1
    text: duplicate id
    type: retrieval
    expected_stance: answer
    ground_truth: gt
""")
    assert main(["freeze", "--bank", str(p), "--date", "2026-07-27"]) == 1
    assert "DUPLICATE_ID" in capsys.readouterr().out
    assert "frozen_on" not in p.read_text(), "must not freeze an invalid bank"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_freeze.py -v`
Expected: FAIL — `argparse` exits with "invalid choice: 'freeze'"

- [ ] **Step 3: Add `freeze` to `atlas_eval/cli.py`**

Add these imports at the top of the file:

```python
from datetime import date as _date

from ruamel.yaml import YAML

from atlas_eval.dataset import compute_question_sha256, load_bank
from atlas_eval.validation import validate_bank
```

Add the command implementation:

```python
def _cmd_freeze(args: argparse.Namespace) -> int:
    """Stamp frozen_on and question_sha256 in place, preserving formatting."""
    path = Path(args.bank)
    bank = load_bank(path)

    issues = validate_bank(bank, path.name)
    # A hash mismatch is expected here: that is what we are about to rewrite.
    blocking = [i for i in issues if i.code != "FROZEN_HASH_MISMATCH"]
    if blocking:
        for i in blocking:
            where = f"{i.bank}:{i.question_id}" if i.question_id else i.bank
            print(f"{where}: {i.code}: {i.message}")
        print("\nrefusing to freeze a bank with validation issues.")
        return 1

    frozen = _date.fromisoformat(args.date)
    bank.frozen_on = frozen
    digest = compute_question_sha256(bank)

    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.width = 100
    with path.open(encoding="utf-8") as fh:
        doc = yaml.load(fh)
    doc["frozen_on"] = args.date
    doc["question_sha256"] = digest
    with path.open("w", encoding="utf-8") as fh:
        yaml.dump(doc, fh)

    print(f"froze {bank.version} on {args.date}: {digest[:12]} "
          f"({len(bank.questions)} questions)")
    return 0
```

Register it inside `main`, before `args = parser.parse_args(argv)`:

```python
    p_freeze = sub.add_parser("freeze", help="stamp frozen_on and question_sha256")
    p_freeze.add_argument("--bank", required=True)
    p_freeze.add_argument("--date", required=True, help="freeze date, YYYY-MM-DD")
    p_freeze.set_defaults(func=_cmd_freeze)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_freeze.py -v`
Expected: PASS, 5 passed

- [ ] **Step 5: Fill `checks` for v4, v5 and v6**

Same rules and worked examples as Task 9. v6 is a held-out comparison bank whose ground truth is unusually detailed, so its checks can be correspondingly specific. Example from the real v6 material:

```yaml
# v6.yaml — v6-Q8, DD-name-vs-dataset mismatch
  - id: v6-Q8
    checks:
      required_all: [DB89FILE]
      required_any: ["L213DC.DB98FIL.DTL", "DB98FIL"]
      expect_citations: [DXCRD88E, DXCRD99E, REPRA262]
```

- [ ] **Step 6: Freeze v1–v5 with their real freeze dates; leave v6 unfrozen**

```bash
python -m atlas_eval.cli freeze --bank data/banks/v1.yaml --date 2026-07-27
python -m atlas_eval.cli freeze --bank data/banks/v2.yaml --date 2026-07-28
python -m atlas_eval.cli freeze --bank data/banks/v3.yaml --date 2026-08-03
python -m atlas_eval.cli freeze --bank data/banks/v4.yaml --date 2026-08-05
python -m atlas_eval.cli freeze --bank data/banks/v5.yaml --date 2026-08-12
python -m atlas_eval.cli validate --banks data/banks
```

Expected: five freeze lines, then `OK: 6 bank(s), N question(s), 0 verified.` v6 stays unfrozen because it must not be run until frozen and hashed.

- [ ] **Step 7: Commit**

```bash
python -m pytest -q
git add atlas_eval/cli.py tests/test_freeze.py data/banks/
git commit -m "feat: add freeze command, populate v4-v6 checks, freeze v1-v5"
```

---

### Task 11: Migrate the legacy runs

224 score rows, 27 transcripts and 40 snapshot files become run directories. Transcripts and snapshots share the `<date>_<HHMM>_<agent>` stamp with `scores.csv`'s `run_finished`, so runs reconstruct unambiguously.

**Source shapes** (verified 2026-08-26):
- `scores.csv` columns: `run_finished,agent,agent_id,bank_version,question_id,type,citations,correctness,gap_honesty,scope_discipline,clarity,total,conversation_id,notes`, with `run_finished` formatted `YYYY-MM-DD HH:MM`.
- `chats/<YYYY-MM-DD>_<HHMM>_engineering_onboarding_specialist.md`
- `snapshots/<YYYY-MM-DD>_<HHMM>_engineering_onboarding_specialist.json` and `snapshots/<YYYY-MM-DD>_<HHMM>_spaces.json`

**Files:**
- Create: `atlas_eval/migrate/runs.py`
- Create: `tools/migrate_runs.py`
- Test: `tests/test_migrate_runs.py`

**Interfaces:**
- Consumes: `RunMeta`, `RunStatus`, `ScoreRow`, `Rubric`, `write_run`, `regenerate_rollup`, `make_run_id`.
- Produces:
  - `stamp_from_run_finished(value: str) -> str` — `"2026-07-27 11:19"` -> `"2026-07-27_1119"`
  - `group_legacy_scores(rows: list[dict]) -> dict[tuple[str, str], list[dict]]` keyed by `(run_finished, bank_version)`
  - `legacy_row_to_score_row(rec: dict, scored_by: str, confirmed_by: str | None) -> ScoreRow`
  - `migrate_runs(source: Path, runs_dir: Path, scored_by: str = "legacy-audit", confirmed_by: str | None = None) -> list[str]` — returns run ids written

**Provenance decision:** the legacy process did not record per-row who scored what, so migration stamps `scored_by="legacy-audit"` and leaves `confirmed_by` unset by default rather than asserting a reviewer. `tools/migrate_runs.py --confirmed-by "Michael Angeli"` stamps it when the reviewer is known. Do not guess a name.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_migrate_runs.py
import csv
from pathlib import Path

import pytest

from atlas_eval.migrate.runs import (
    group_legacy_scores, legacy_row_to_score_row, migrate_runs, stamp_from_run_finished,
)
from atlas_eval.runs import ROLLUP_COLUMNS, RunStatus, read_run, regenerate_rollup

AGENT = "Engineering Onboarding Specialist"
AGENT_ID = "093ac4e3-0712-481e-af95-9ddc5e4fc734"
CONV = "e33bea76-a1f6-4c78-8c1d-9d735e3dfb82"

LEGACY_HEADER = (
    "run_finished,agent,agent_id,bank_version,question_id,type,citations,correctness,"
    "gap_honesty,scope_discipline,clarity,total,conversation_id,notes\n"
)


def _legacy_csv(tmp_path, *rows):
    p = tmp_path / "scores.csv"
    p.write_text(LEGACY_HEADER + "".join(rows))
    return p


def _row(finished="2026-07-27 11:19", qid="v1-Q1", version="v1", notes=""):
    return (f"{finished},{AGENT},{AGENT_ID},{version},{qid},retrieval,"
            f"2,1,1,1,2,7,{CONV},{notes}\n")


def _source(tmp_path, *rows):
    src = tmp_path / "src"
    (src / "chats").mkdir(parents=True)
    (src / "snapshots").mkdir(parents=True)
    _legacy_csv(src, *rows)
    stem = "2026-07-27_1119_engineering_onboarding_specialist"
    (src / "chats" / f"{stem}.md").write_text("# chat\n\nQ1 ... A1 ...\n")
    (src / "snapshots" / f"{stem}.json").write_text('{"AgentId": "093ac4e3"}')
    (src / "snapshots" / "2026-07-27_1119_spaces.json").write_text('{"Spaces": []}')
    return src


def test_stamp_conversion():
    assert stamp_from_run_finished("2026-07-27 11:19") == "2026-07-27_1119"
    assert stamp_from_run_finished("2026-08-12 17:04") == "2026-08-12_1704"


def test_stamp_rejects_unexpected_format():
    with pytest.raises(ValueError):
        stamp_from_run_finished("27/07/2026 11:19")


def test_grouping_splits_by_timestamp_and_bank():
    rows = [
        {"run_finished": "2026-07-27 11:19", "bank_version": "v1", "question_id": "v1-Q1"},
        {"run_finished": "2026-07-27 11:19", "bank_version": "v1", "question_id": "v1-Q2"},
        {"run_finished": "2026-08-12 17:04", "bank_version": "v5", "question_id": "v5-Q1"},
    ]
    groups = group_legacy_scores(rows)
    assert sorted(groups) == [("2026-07-27 11:19", "v1"), ("2026-08-12 17:04", "v5")]
    assert len(groups[("2026-07-27 11:19", "v1")]) == 2


def test_legacy_row_stamps_provenance_without_guessing_a_reviewer():
    rec = dict(zip(LEGACY_HEADER.strip().split(","), _row().strip().split(",")))
    row = legacy_row_to_score_row(rec)
    assert row.rubric.scored_by == "legacy-audit"
    assert row.rubric.confirmed_by is None, "must not assert an unrecorded reviewer"

    stamped = legacy_row_to_score_row(rec, "legacy-audit", "Michael Angeli")
    assert stamped.rubric.confirmed_by == "Michael Angeli"


def test_legacy_row_becomes_a_score_row_with_rubric_intact():
    rec = dict(zip(LEGACY_HEADER.strip().split(","),
                   _row(notes="described one program only").strip().split(",")))
    row = legacy_row_to_score_row(rec)
    assert row.question_id == "v1-Q1"
    assert row.rubric.citations == 2 and row.rubric.correctness == 1
    assert row.rubric.total == 7
    assert row.rubric.notes == "described one program only"
    assert row.deterministic is None, "legacy rows were never deterministically scored"
    assert row.verification_status == "unverified"


def test_blank_rubric_cell_becomes_none_not_zero():
    rec = dict(zip(LEGACY_HEADER.strip().split(","),
                   f"2026-07-27 11:19,{AGENT},{AGENT_ID},v1,v1-Q1,retrieval,"
                   f",,,,,,{CONV},".split(",")))
    row = legacy_row_to_score_row(rec)
    assert row.rubric.citations is None and row.rubric.total is None


def test_migrate_creates_one_run_dir_per_group(tmp_path):
    src = _source(tmp_path, _row(qid="v1-Q1"), _row(qid="v1-Q2"))
    runs = tmp_path / "runs"
    ids = migrate_runs(src, runs)
    assert ids == ["2026-07-27_1119_quick_v1"]

    meta, responses, rows = read_run(runs / ids[0])
    assert meta.backend == "quick" and meta.transport == "legacy"
    assert meta.status is RunStatus.COMPLETE
    assert meta.agent_id == AGENT_ID and meta.conversation_id == CONV
    assert meta.bank_version == "v1"
    assert [r.question_id for r in rows] == ["v1-Q1", "v1-Q2"]
    assert responses == {}, "legacy transcripts were not split per question"


def test_transcript_and_snapshot_are_carried_across(tmp_path):
    src = _source(tmp_path, _row())
    runs = tmp_path / "runs"
    run_dir = runs / migrate_runs(src, runs)[0]
    assert "# chat" in (run_dir / "transcript.md").read_text()
    snap = (run_dir / "snapshot.json").read_text()
    assert "AgentId" in snap and "Spaces" in snap, "agent and spaces are merged"


def test_missing_transcript_is_recorded_not_fatal(tmp_path):
    src = _source(tmp_path, _row(finished="2026-08-99 09:00"))
    # A row whose timestamp has no chat file at all.
    src_rows = (src / "scores.csv").read_text()
    (src / "scores.csv").write_text(src_rows.replace("2026-08-99 09:00", "2026-08-01 09:00"))
    runs = tmp_path / "runs"
    ids = migrate_runs(src, runs)
    run_dir = runs / [i for i in ids if i.startswith("2026-08-01")][0]
    assert (run_dir / "transcript.md").read_text().startswith("<!-- no transcript")


def test_no_score_rows_are_lost(tmp_path):
    src = _source(tmp_path, _row(qid="v1-Q1"), _row(qid="v1-Q2"),
                  _row(finished="2026-08-12 17:04", qid="v5-Q1", version="v5"))
    runs = tmp_path / "runs"
    migrate_runs(src, runs)
    out = tmp_path / "scores.csv"
    regenerate_rollup(runs, out)
    with out.open(newline="") as fh:
        reader = csv.DictReader(fh)
        assert tuple(reader.fieldnames) == ROLLUP_COLUMNS
        assert len(list(reader)) == 3


def test_source_is_never_modified(tmp_path):
    src = _source(tmp_path, _row())
    before = {p: p.read_bytes() for p in src.rglob("*") if p.is_file()}
    migrate_runs(src, tmp_path / "runs")
    after = {p: p.read_bytes() for p in src.rglob("*") if p.is_file()}
    assert before == after
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_migrate_runs.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas_eval.migrate.runs'`

- [ ] **Step 3: Write the implementation**

```python
# atlas_eval/migrate/runs.py
"""Rebuild run records from the legacy scores.csv, chats/ and snapshots/.

Read-only with respect to the source tree. Legacy runs carry transport
"legacy": they were driven by hand, and their transcripts were never split
into per-question responses, so responses.yaml is empty rather than guessed.
"""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path

from atlas_eval.runs import RunMeta, RunStatus, ScoreRow, write_run
from atlas_eval.scoring import RUBRIC_DIMENSIONS, Rubric

_STAMP = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2})$")
AGENT_SLUG = "engineering_onboarding_specialist"


def stamp_from_run_finished(value: str) -> str:
    m = _STAMP.match(value.strip())
    if not m:
        raise ValueError(f"unexpected run_finished format: {value!r}")
    return f"{m.group(1)}_{m.group(2)}{m.group(3)}"


def group_legacy_scores(rows: list[dict]) -> dict[tuple[str, str], list[dict]]:
    groups: dict[tuple[str, str], list[dict]] = {}
    for rec in rows:
        groups.setdefault((rec["run_finished"], rec["bank_version"]), []).append(rec)
    return groups


def legacy_row_to_score_row(
    rec: dict,
    scored_by: str = "legacy-audit",
    confirmed_by: str | None = None,
) -> ScoreRow:
    def cell(name: str) -> int | None:
        raw = (rec.get(name) or "").strip()
        return int(raw) if raw else None

    return ScoreRow(
        question_id=rec["question_id"],
        type=rec["type"],
        verification_status="unverified",
        rubric=Rubric(
            notes=(rec.get("notes") or "").strip() or None,
            scored_by=scored_by,
            confirmed_by=confirmed_by,
            **{dim: cell(dim) for dim in RUBRIC_DIMENSIONS},
        ),
        deterministic=None,
    )


def _load_snapshot(snapshots: Path, stamp: str) -> dict:
    """Merge the agent and spaces snapshots for one run stamp."""
    merged: dict = {}
    agent_file = snapshots / f"{stamp}_{AGENT_SLUG}.json"
    spaces_file = snapshots / f"{stamp}_spaces.json"
    if agent_file.exists():
        merged["agent"] = json.loads(agent_file.read_text(encoding="utf-8"))
    if spaces_file.exists():
        merged["spaces"] = json.loads(spaces_file.read_text(encoding="utf-8"))
    return merged


def migrate_runs(
    source: Path,
    runs_dir: Path,
    scored_by: str = "legacy-audit",
    confirmed_by: str | None = None,
) -> list[str]:
    with (source / "scores.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    written: list[str] = []
    for (finished, version), group in sorted(group_legacy_scores(rows).items()):
        stamp = stamp_from_run_finished(finished)
        first = group[0]
        when = datetime.strptime(finished, "%Y-%m-%d %H:%M")
        run_id = f"{stamp}_quick_{version}"

        chat = source / "chats" / f"{stamp}_{AGENT_SLUG}.md"
        transcript = (
            chat.read_text(encoding="utf-8") if chat.exists()
            else f"<!-- no transcript found for {stamp} in the legacy chats/ directory -->\n"
        )

        meta = RunMeta(
            run_id=run_id,
            backend="quick",
            transport="legacy",
            bank_version=version,
            # Legacy runs predate freeze hashing; recorded as unknown rather than
            # back-computed, since the bank text may have moved since.
            question_sha256="legacy-unknown",
            agent=first["agent"],
            agent_id=(first.get("agent_id") or "").strip() or None,
            conversation_id=(first.get("conversation_id") or "").strip() or None,
            started_at=when,
            finished_at=when,
            harness_git_sha=None,
            status=RunStatus.COMPLETE,
        )

        write_run(
            runs_dir, meta,
            responses={},
            transcript=transcript,
            snapshot=_load_snapshot(source / "snapshots", stamp),
            rows=[legacy_row_to_score_row(rec, scored_by, confirmed_by)
                  for rec in group],
        )
        written.append(run_id)

    return written
```

```python
# tools/migrate_runs.py
"""Rebuild run records and the rollup from the legacy audit material.

    python tools/migrate_runs.py --source <quick_chat_audits dir>

Never writes to --source.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from atlas_eval.migrate.runs import migrate_runs
from atlas_eval.runs import regenerate_rollup


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--runs", default="data/runs")
    ap.add_argument("--rollup", default="data/scores.csv")
    ap.add_argument("--scored-by", default="legacy-audit")
    ap.add_argument("--confirmed-by", default=None,
                    help="name of the human who reviewed these scores, if known")
    args = ap.parse_args()

    ids = migrate_runs(Path(args.source), Path(args.runs),
                       args.scored_by, args.confirmed_by)
    for run_id in ids:
        print(f"wrote {run_id}")
    n = regenerate_rollup(Path(args.runs), Path(args.rollup))
    print(f"\n{len(ids)} run(s) migrated; rollup regenerated from {n} complete run(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_migrate_runs.py -v`
Expected: PASS, 11 passed

- [ ] **Step 5: Run the migration and verify no rows were lost**

```bash
SRC="/Users/michaelangeli/projects/aws_transform_output/quick_chat_audits"
python tools/migrate_runs.py --source "$SRC"
echo "legacy data rows:   $(( $(wc -l < "$SRC/scores.csv") - 1 ))"
echo "migrated data rows: $(( $(wc -l < data/scores.csv) - 1 ))"
```

Expected: both counts are 224. If they differ, do not proceed: find the dropped group before committing.

- [ ] **Step 6: Copy the remaining reference material and check for PII**

```bash
SRC="/Users/michaelangeli/projects/aws_transform_output/quick_chat_audits"
mkdir -p reference
for item in persona_inventory one_offs "Michael Audit Notes.md" 2801_tracker_draft.md \
            2802_comment_draft.md sharepoint_doc_inventory.csv scores_chart.html \
            SME_confirmation_audit_QA.xlsx SME_review_brief.xlsx; do
  cp -R "$SRC/$item" reference/
done

# Never bring these in: knowledge-base source material, 928 MB total.
for excluded in "SharePoint - Current System Documentation" "Tech Specs" \
                "Product Briefs" v5_reference; do
  test ! -e "reference/$excluded" || { echo "ERROR: $excluded must not be here"; exit 1; }
done

# PII sweep across everything about to be committed.
grep -rInE '[0-9]{3}-[0-9]{2}-[0-9]{4}' data/ reference/ | grep -vE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head
du -sh data reference
```

Expected: the exclusion loop prints nothing, the SSN-shaped grep returns no real SSNs (mainframe corpus discusses SSN *fields*, not values), and `data` plus `reference` together are a few MB. Any real SSN must be redacted before the commit.

- [ ] **Step 7: Commit**

```bash
python -m pytest -q
git add atlas_eval/migrate/runs.py tools/migrate_runs.py tests/test_migrate_runs.py \
        data/runs/ data/scores.csv reference/
git commit -m "feat: migrate 224 legacy score rows, 27 transcripts and 40 snapshots"
```

---

### Task 12: Review spreadsheet export

Two sheets matching the layout the existing `SME_review_brief.xlsx` already uses, so Oscar sees a familiar document.

**Files:**
- Create: `atlas_eval/review.py`
- Modify: `atlas_eval/cli.py` (add `review export`)
- Test: `tests/test_review_export.py`

**Interfaces:**
- Consumes: `Bank`, `Question`, `VerificationStatus`, `load_all_banks`.
- Produces:
  - `REVIEW_SHEET = "Review"`, `TRACKING_SHEET = "Our tracking"`
  - `REVIEW_COLUMNS: tuple[str, ...]` = `("id", "question", "type", "expected answer", "notes", "accurate?", "reviewer", "comments")`
  - `TRACKING_COLUMNS: tuple[str, ...]` = `("id", "bank", "type_note", "provenance", "required_all", "required_any", "forbidden", "expect_citations", "current status", "expected stance")`
  - `ACCURATE_CHOICES: tuple[str, ...]` = `("yes", "no", "unsure")`
  - `export_review(banks: list[Bank], out_path: Path, statuses: set[VerificationStatus] | None = None) -> int`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_review_export.py
from datetime import date

import pytest
from openpyxl import load_workbook

from atlas_eval.models import (
    Bank, Checks, Question, QuestionType, Stance, Verification, VerificationStatus,
)
from atlas_eval.review import (
    ACCURATE_CHOICES, REVIEW_COLUMNS, REVIEW_SHEET, TRACKING_COLUMNS, TRACKING_SHEET,
    export_review,
)


def _q(qid, status=VerificationStatus.UNVERIFIED, **over):
    base = dict(
        id=qid, text=f"question text for {qid}", type=QuestionType.TERM_REDIRECT,
        type_note="term-redirect", provenance="product-brief/employer-charges-phase-2",
        expected_stance=Stance.REDIRECT,
        ground_truth="Maps to the Accelerated Collection Process.",
        checks=Checks(required_all=["ACP"], forbidden=["ETA-227"],
                      expect_citations=["UIMB0730", "L2ACPD"]),
        verification=Verification(status=status),
    )
    base.update(over)
    return Question(**base)


def _bank(*questions, version="v3"):
    return Bank(version=version, agent="a", corpus="c", questions=list(questions))


def test_export_writes_both_sheets_with_exact_headers(tmp_path):
    out = tmp_path / "review.xlsx"
    assert export_review([_bank(_q("v3-Q1"))], out) == 1

    wb = load_workbook(out)
    assert wb.sheetnames == [REVIEW_SHEET, TRACKING_SHEET]
    review = wb[REVIEW_SHEET]
    assert tuple(c.value for c in review[1]) == REVIEW_COLUMNS
    assert tuple(c.value for c in wb[TRACKING_SHEET][1]) == TRACKING_COLUMNS


def test_review_row_carries_question_and_ground_truth(tmp_path):
    out = tmp_path / "review.xlsx"
    export_review([_bank(_q("v3-Q1"))], out)
    row = {k: v for k, v in zip(REVIEW_COLUMNS, [c.value for c in load_workbook(out)[REVIEW_SHEET][2]])}
    assert row["id"] == "v3-Q1"
    assert row["question"] == "question text for v3-Q1"
    assert row["type"] == "term_redirect"
    assert "Accelerated Collection Process" in row["expected answer"]
    assert row["accurate?"] in (None, "")
    assert row["reviewer"] in (None, "")


def test_tracking_sheet_flattens_check_terms(tmp_path):
    out = tmp_path / "review.xlsx"
    export_review([_bank(_q("v3-Q1"))], out)
    row = {k: v for k, v in zip(TRACKING_COLUMNS, [c.value for c in load_workbook(out)[TRACKING_SHEET][2]])}
    assert row["bank"] == "v3"
    assert row["type_note"] == "term-redirect"
    assert row["required_all"] == "ACP"
    assert row["forbidden"] == "ETA-227"
    assert row["expect_citations"] == "UIMB0730; L2ACPD"
    assert row["current status"] == "unverified"
    assert row["expected stance"] == "redirect"


def test_status_filter_selects_a_subset(tmp_path):
    bank = _bank(
        _q("v3-Q1", VerificationStatus.UNVERIFIED),
        _q("v3-Q2", VerificationStatus.VERIFIED,
           verification=Verification(status=VerificationStatus.VERIFIED,
                                     verified_by="Oscar", verified_on=date(2026, 8, 26))),
        _q("v3-Q3", VerificationStatus.NEEDS_SME),
    )
    out = tmp_path / "review.xlsx"
    n = export_review([bank], out, statuses={VerificationStatus.UNVERIFIED,
                                             VerificationStatus.NEEDS_SME})
    assert n == 2
    ids = [r[0].value for r in load_workbook(out)[REVIEW_SHEET].iter_rows(min_row=2)]
    assert ids == ["v3-Q1", "v3-Q3"]


def test_no_filter_exports_everything(tmp_path):
    bank = _bank(_q("v3-Q1"), _q("v3-Q2", VerificationStatus.VERIFIED,
                                 verification=Verification(status=VerificationStatus.VERIFIED,
                                                           verified_by="Oscar")))
    out = tmp_path / "review.xlsx"
    assert export_review([bank], out) == 2


def test_rejected_questions_carry_their_prior_verdict(tmp_path):
    q = _q("v3-Q4", verification=Verification(
        status=VerificationStatus.REJECTED, verified_by="Oscar",
        verified_on=date(2026, 8, 26), notes="No knowable answer; Oscar did not know it either."))
    out = tmp_path / "review.xlsx"
    export_review([_bank(q)], out)
    review = load_workbook(out)[REVIEW_SHEET]
    row = {k: v for k, v in zip(REVIEW_COLUMNS, [c.value for c in review[2]])}
    assert row["accurate?"] == "no"
    assert row["reviewer"] == "Oscar"
    assert "No knowable answer" in row["notes"]


def test_export_of_empty_selection_still_writes_headers(tmp_path):
    out = tmp_path / "review.xlsx"
    assert export_review([_bank(_q("v3-Q1", VerificationStatus.VERIFIED,
                                  verification=Verification(status=VerificationStatus.VERIFIED,
                                                            verified_by="O")))],
                         out, statuses={VerificationStatus.REJECTED}) == 0
    wb = load_workbook(out)
    assert tuple(c.value for c in wb[REVIEW_SHEET][1]) == REVIEW_COLUMNS
    assert wb[REVIEW_SHEET].max_row == 1


def test_accurate_choices_are_the_three_documented_values():
    assert ACCURATE_CHOICES == ("yes", "no", "unsure")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_review_export.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas_eval.review'`

- [ ] **Step 3: Write the implementation**

```python
# atlas_eval/review.py
"""SME review round trip.

Repo files are canonical; the spreadsheet is a transport. Export selects
questions, import writes only the verification block back, so every reviewer
verdict lands in git as a reviewable diff.
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from atlas_eval.models import Bank, Question, VerificationStatus

REVIEW_SHEET = "Review"
TRACKING_SHEET = "Our tracking"

REVIEW_COLUMNS: tuple[str, ...] = (
    "id", "question", "type", "expected answer", "notes", "accurate?", "reviewer",
    "comments",
)

TRACKING_COLUMNS: tuple[str, ...] = (
    "id", "bank", "type_note", "provenance", "required_all", "required_any",
    "forbidden", "expect_citations", "current status", "expected stance",
)

ACCURATE_CHOICES: tuple[str, ...] = ("yes", "no", "unsure")

# accurate? <-> verification status. Import reverses this mapping.
STATUS_TO_ACCURATE: dict[VerificationStatus, str] = {
    VerificationStatus.VERIFIED: "yes",
    VerificationStatus.REJECTED: "no",
    VerificationStatus.NEEDS_SME: "unsure",
    VerificationStatus.UNVERIFIED: "",
}

_REVIEW_WIDTHS = (12, 60, 18, 80, 40, 11, 14, 40)
_TRACKING_WIDTHS = (12, 8, 26, 34, 26, 26, 22, 30, 15, 16)


def _joined(values: list[str]) -> str:
    return "; ".join(values)


def _review_row(q: Question) -> list[str]:
    return [
        q.id,
        q.text,
        q.type.value,
        q.ground_truth.strip(),
        (q.verification.notes or "").strip(),
        STATUS_TO_ACCURATE[q.verification.status],
        q.verification.verified_by or "",
        "",
    ]


def _tracking_row(bank: Bank, q: Question) -> list[str]:
    return [
        q.id, bank.version, q.type_note or "", q.provenance or "",
        _joined(q.checks.required_all), _joined(q.checks.required_any),
        _joined(q.checks.forbidden), _joined(q.checks.expect_citations),
        q.verification.status.value, q.expected_stance.value,
    ]


def _style(ws, columns: tuple[str, ...], widths: tuple[int, ...]) -> None:
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "A2"
    for idx, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)


def export_review(
    banks: list[Bank],
    out_path: Path,
    statuses: set[VerificationStatus] | None = None,
) -> int:
    """Write the review workbook. Returns the number of questions exported."""
    wb = Workbook()
    review = wb.active
    review.title = REVIEW_SHEET
    review.append(list(REVIEW_COLUMNS))
    tracking = wb.create_sheet(TRACKING_SHEET)
    tracking.append(list(TRACKING_COLUMNS))

    exported = 0
    for bank in banks:
        for q in bank.questions:
            if statuses is not None and q.verification.status not in statuses:
                continue
            review.append(_review_row(q))
            tracking.append(_tracking_row(bank, q))
            exported += 1

    _style(review, REVIEW_COLUMNS, _REVIEW_WIDTHS)
    _style(tracking, TRACKING_COLUMNS, _TRACKING_WIDTHS)

    if exported:
        col = get_column_letter(REVIEW_COLUMNS.index("accurate?") + 1)
        dv = DataValidation(
            type="list", formula1=f'"{",".join(ACCURATE_CHOICES)}"', allow_blank=True,
            showErrorMessage=True, error="Choose yes, no, or unsure.",
        )
        review.add_data_validation(dv)
        dv.add(f"{col}2:{col}{exported + 1}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return exported
```

Add to `atlas_eval/cli.py`:

```python
def _cmd_review_export(args: argparse.Namespace) -> int:
    from atlas_eval.models import VerificationStatus
    from atlas_eval.review import export_review

    banks = load_all_banks(Path(args.banks))
    if args.bank:
        banks = [b for b in banks if b.version == args.bank]
        if not banks:
            print(f"error: no bank named {args.bank}")
            return 2

    statuses = None
    if args.status:
        try:
            statuses = {VerificationStatus(s) for s in args.status}
        except ValueError as err:
            print(f"error: {err}")
            return 2

    n = export_review(banks, Path(args.out), statuses)
    print(f"exported {n} question(s) to {args.out}")
    return 0
```

Register inside `main`:

```python
    p_review = sub.add_parser("review", help="SME review round trip")
    review_sub = p_review.add_subparsers(dest="review_command", required=True)

    p_exp = review_sub.add_parser("export", help="write the review workbook")
    p_exp.add_argument("--banks", default=str(DEFAULT_BANKS))
    p_exp.add_argument("--bank", help="limit to one bank version, e.g. v3")
    p_exp.add_argument("--status", nargs="*",
                       help="filter by verification status, e.g. unverified needs-sme")
    p_exp.add_argument("-o", "--out", required=True)
    p_exp.set_defaults(func=_cmd_review_export)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_review_export.py -v`
Expected: PASS, 8 passed

- [ ] **Step 5: Generate a real workbook and open it**

```bash
python -m atlas_eval.cli review export --bank v3 --status unverified -o /tmp/v3_review.xlsx
open /tmp/v3_review.xlsx
```

Expected: a `Review` sheet with the v3 questions, wrapped ground-truth text, and a yes/no/unsure dropdown in `accurate?`. Confirm the ground-truth column is readable at the set width; widen `_REVIEW_WIDTHS` if not.

- [ ] **Step 6: Commit**

```bash
git add atlas_eval/review.py atlas_eval/cli.py tests/test_review_export.py
git commit -m "feat: export SME review workbook with two-sheet layout"
```

---

### Task 13: Review verdict import

Writes reviewer verdicts back into bank YAML as tracked diffs. Two guards are load-bearing: a question edited in Excel must not silently redefine a frozen question, and `ground_truth` is never written by import.

**Files:**
- Modify: `atlas_eval/review.py` (append)
- Modify: `atlas_eval/cli.py` (add `review import`)
- Test: `tests/test_review_import.py`

**Interfaces:**
- Consumes: `load_all_banks`, `normalize_ws`, `REVIEW_COLUMNS`, `REVIEW_SHEET`, `ACCURATE_CHOICES`.
- Produces:
  - `ACCURATE_TO_STATUS: dict[str, VerificationStatus]` — `{"yes": VERIFIED, "no": REJECTED, "unsure": NEEDS_SME}`
  - `Transition` dataclass: `question_id`, `bank`, `old_status`, `new_status`, `reviewer`, `notes`
  - `ImportReport` dataclass: `transitions: list[Transition]`, `errors: list[str]`, `unchanged: int`; property `ok -> bool`
  - `read_review(path: Path) -> list[dict]`
  - `import_review(path: Path, banks_dir: Path, reviewed_on: date, dry_run: bool = False) -> ImportReport`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_review_import.py
from datetime import date
from pathlib import Path

from openpyxl import load_workbook

from atlas_eval.dataset import load_bank
from atlas_eval.models import VerificationStatus
from atlas_eval.review import export_review, import_review

BANK_YAML = """version: v3
frozen_on: 2026-08-03
question_sha256: PLACEHOLDER
agent: engineering_onboarding_specialist
corpus: quick_space_ca7_daily_s3
questions:
  - id: v3-Q1
    text: Describe the Automated Collection Process.
    type: term_redirect
    type_note: term-redirect
    expected_stance: redirect
    ground_truth: |
      Maps to the Accelerated Collection Process (ACP).
    checks:
      required_all: [ACP]
      forbidden: [ETA-227]
  - id: v3-Q2
    after: v3-Q1
    text: What does the acronym ACP stand for?
    type: acronym_check
    expected_stance: answer
    ground_truth: |
      Accelerated Collection Process.
"""


def _banks_dir(tmp_path):
    from atlas_eval.dataset import compute_question_sha256
    d = tmp_path / "banks"
    d.mkdir()
    p = d / "v3.yaml"
    p.write_text(BANK_YAML)
    bank = load_bank(p)
    p.write_text(BANK_YAML.replace("PLACEHOLDER", compute_question_sha256(bank)))
    return d


def _sheet(path, edits):
    """Export then apply {question_id: {column: value}} edits in place."""
    wb = load_workbook(path)
    ws = wb["Review"]
    headers = [c.value for c in ws[1]]
    for row in ws.iter_rows(min_row=2):
        qid = row[0].value
        for col, value in edits.get(qid, {}).items():
            row[headers.index(col)].value = value
    wb.save(path)


def _roundtrip(tmp_path, edits):
    banks = _banks_dir(tmp_path)
    xlsx = tmp_path / "review.xlsx"
    export_review([load_bank(banks / "v3.yaml")], xlsx)
    _sheet(xlsx, edits)
    return banks, xlsx


def test_clean_roundtrip_leaves_the_file_byte_identical(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {})
    before = (banks / "v3.yaml").read_bytes()
    report = import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    assert report.ok and report.transitions == []
    assert report.unchanged == 2
    assert (banks / "v3.yaml").read_bytes() == before, "no verdicts means no write"


def test_yes_verdict_marks_verified(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {
        "v3-Q1": {"accurate?": "yes", "reviewer": "Oscar"},
    })
    report = import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    assert report.ok
    assert [(t.question_id, t.new_status) for t in report.transitions] == [
        ("v3-Q1", VerificationStatus.VERIFIED)
    ]
    q1 = load_bank(banks / "v3.yaml").questions[0]
    assert q1.verification.status is VerificationStatus.VERIFIED
    assert q1.verification.verified_by == "Oscar"
    assert str(q1.verification.verified_on) == "2026-08-28"


def test_no_verdict_marks_rejected_and_keeps_the_question(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {
        "v3-Q2": {"accurate?": "no", "reviewer": "Oscar",
                  "comments": "No knowable answer; I did not know it either."},
    })
    import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    bank = load_bank(banks / "v3.yaml")
    assert len(bank.questions) == 2, "a rejected question is retained, not deleted"
    q2 = bank.questions[1]
    assert q2.verification.status is VerificationStatus.REJECTED
    assert "No knowable answer" in q2.verification.notes


def test_unsure_verdict_marks_needs_sme(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {"v3-Q1": {"accurate?": "unsure", "reviewer": "Oscar"}})
    import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    assert load_bank(banks / "v3.yaml").questions[0].verification.status is (
        VerificationStatus.NEEDS_SME
    )


def test_reviewer_comments_land_in_notes_and_never_in_ground_truth(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {
        "v3-Q1": {"accurate?": "no", "reviewer": "Oscar",
                  "comments": "Actually it is the Accelerated Collection Population."},
    })
    before_gt = load_bank(banks / "v3.yaml").questions[0].ground_truth
    import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    q1 = load_bank(banks / "v3.yaml").questions[0]
    assert "Accelerated Collection Population" in q1.verification.notes
    assert q1.ground_truth == before_gt, "import must never rewrite ground truth"


def test_edited_question_text_aborts_the_whole_import(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {
        "v3-Q1": {"accurate?": "yes", "reviewer": "Oscar",
                  "question": "Describe the ACP, reworded in Excel"},
        "v3-Q2": {"accurate?": "yes", "reviewer": "Oscar"},
    })
    before = (banks / "v3.yaml").read_bytes()
    report = import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    assert not report.ok
    assert any("v3-Q1" in e and "question text" in e for e in report.errors)
    assert (banks / "v3.yaml").read_bytes() == before, "abort must write nothing at all"


def test_question_text_comparison_tolerates_whitespace_only_changes(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {
        "v3-Q1": {"accurate?": "yes", "reviewer": "Oscar",
                  "question": "  Describe the   Automated Collection Process.  "},
    })
    report = import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    assert report.ok, report.errors


def test_unknown_id_aborts(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {})
    wb = load_workbook(xlsx)
    wb["Review"].append(["v9-Q9", "a question from nowhere", "retrieval", "gt", "",
                         "yes", "Oscar", ""])
    wb.save(xlsx)
    report = import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    assert not report.ok
    assert any("v9-Q9" in e for e in report.errors)


def test_invalid_accurate_value_aborts(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {"v3-Q1": {"accurate?": "probably", "reviewer": "O"}})
    report = import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    assert not report.ok
    assert any("probably" in e for e in report.errors)


def test_verdict_without_a_reviewer_aborts(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {"v3-Q1": {"accurate?": "yes"}})
    report = import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    assert not report.ok
    assert any("reviewer" in e.lower() for e in report.errors)


def test_dry_run_reports_transitions_without_writing(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {"v3-Q1": {"accurate?": "yes", "reviewer": "Oscar"}})
    before = (banks / "v3.yaml").read_bytes()
    report = import_review(xlsx, banks, reviewed_on=date(2026, 8, 28), dry_run=True)
    assert report.ok and len(report.transitions) == 1
    assert (banks / "v3.yaml").read_bytes() == before


def test_import_preserves_frozen_hash_and_formatting(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {"v3-Q1": {"accurate?": "yes", "reviewer": "Oscar"}})
    before = load_bank(banks / "v3.yaml").question_sha256
    import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    text = (banks / "v3.yaml").read_text()
    assert load_bank(banks / "v3.yaml").question_sha256 == before
    assert "ground_truth: |" in text, "block scalars must survive the rewrite"
    assert "after: v3-Q2" not in text and "after: v3-Q1" in text


def test_import_is_idempotent(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {"v3-Q1": {"accurate?": "yes", "reviewer": "Oscar"}})
    import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    first = (banks / "v3.yaml").read_bytes()
    second_report = import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    assert second_report.transitions == []
    assert (banks / "v3.yaml").read_bytes() == first
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_review_import.py -v`
Expected: FAIL — `ImportError: cannot import name 'import_review'`

- [ ] **Step 3: Append the implementation to `atlas_eval/review.py`**

```python
from dataclasses import dataclass, field
from datetime import date as _date

from openpyxl import load_workbook
from ruamel.yaml import YAML

from atlas_eval.dataset import load_bank, normalize_ws

ACCURATE_TO_STATUS: dict[str, VerificationStatus] = {
    "yes": VerificationStatus.VERIFIED,
    "no": VerificationStatus.REJECTED,
    "unsure": VerificationStatus.NEEDS_SME,
}


@dataclass
class Transition:
    question_id: str
    bank: str
    old_status: VerificationStatus
    new_status: VerificationStatus
    reviewer: str
    notes: str | None


@dataclass
class ImportReport:
    transitions: list[Transition] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    unchanged: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def read_review(path: Path) -> list[dict]:
    wb = load_workbook(path, data_only=True)
    ws = wb[REVIEW_SHEET]
    headers = [c.value for c in ws[1]]
    rows: list[dict] = []
    for row in ws.iter_rows(min_row=2):
        values = [c.value for c in row]
        if all(v in (None, "") for v in values):
            continue
        rows.append({h: values[i] for i, h in enumerate(headers) if h})
    return rows


def _text(value) -> str:
    return "" if value is None else str(value).strip()


def import_review(
    path: Path,
    banks_dir: Path,
    reviewed_on: _date,
    dry_run: bool = False,
) -> ImportReport:
    """Write reviewer verdicts into bank YAML. Aborts wholesale on any error.

    Never writes ground_truth: a reviewer correction is recorded in
    verification.notes, and promoting it into ground truth is a deliberate
    separate edit made in git.
    """
    report = ImportReport()

    bank_paths = sorted(banks_dir.glob("*.yaml"))
    banks = {p: load_bank(p) for p in bank_paths}
    index: dict[str, tuple[Path, object]] = {}
    for p, bank in banks.items():
        for q in bank.questions:
            index[q.id] = (p, q)

    planned: dict[Path, dict[str, Transition]] = {}

    for row in read_review(path):
        qid = _text(row.get("id"))
        if not qid:
            continue
        if qid not in index:
            report.errors.append(
                f"{qid}: unknown question id; it is not in any bank under {banks_dir}"
            )
            continue

        bank_path, question = index[qid]

        sheet_text = _text(row.get("question"))
        if sheet_text and normalize_ws(sheet_text) != normalize_ws(question.text):
            report.errors.append(
                f"{qid}: question text in the sheet does not match the bank; an edit "
                "made in the spreadsheet must not redefine a frozen question"
            )
            continue

        verdict = _text(row.get("accurate?")).lower()
        if not verdict:
            report.unchanged += 1
            continue
        if verdict not in ACCURATE_TO_STATUS:
            report.errors.append(
                f"{qid}: 'accurate?' is {verdict!r}; expected one of "
                f"{', '.join(ACCURATE_CHOICES)}"
            )
            continue

        reviewer = _text(row.get("reviewer"))
        if not reviewer:
            report.errors.append(f"{qid}: verdict {verdict!r} has no reviewer name")
            continue

        new_status = ACCURATE_TO_STATUS[verdict]
        comments = _text(row.get("comments"))
        existing_notes = _text(row.get("notes"))
        notes = comments or existing_notes or None

        unchanged = (
            question.verification.status is new_status
            and question.verification.verified_by == reviewer
            and (question.verification.notes or "") == (notes or "")
        )
        if unchanged:
            report.unchanged += 1
            continue

        planned.setdefault(bank_path, {})[qid] = Transition(
            question_id=qid, bank=banks[bank_path].version,
            old_status=question.verification.status, new_status=new_status,
            reviewer=reviewer, notes=notes,
        )

    if report.errors:
        # Abort wholesale: a partial import leaves the corpus in a state nobody
        # reviewed, and the reviewer cannot tell which verdicts landed.
        return report

    report.transitions = [t for edits in planned.values() for t in edits.values()]
    if dry_run or not report.transitions:
        return report

    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.width = 100

    for bank_path, edits in planned.items():
        with bank_path.open(encoding="utf-8") as fh:
            doc = yaml.load(fh)
        for entry in doc["questions"]:
            transition = edits.get(str(entry.get("id")))
            if transition is None:
                continue
            block = entry.get("verification")
            if block is None:
                entry["verification"] = block = {}
            block["status"] = transition.new_status.value
            block["verified_by"] = transition.reviewer
            block["verified_on"] = reviewed_on.isoformat()
            block["notes"] = transition.notes
        with bank_path.open("w", encoding="utf-8") as fh:
            yaml.dump(doc, fh)

    return report
```

Add to `atlas_eval/cli.py`:

```python
def _cmd_review_import(args: argparse.Namespace) -> int:
    from datetime import date as _date

    from atlas_eval.review import import_review

    reviewed_on = _date.fromisoformat(args.date) if args.date else _date.today()
    report = import_review(Path(args.file), Path(args.banks), reviewed_on, args.dry_run)

    if not report.ok:
        for err in report.errors:
            print(f"error: {err}")
        print(f"\nnothing was written ({len(report.errors)} error(s)).")
        return 1

    for t in sorted(report.transitions, key=lambda t: t.question_id):
        print(f"{t.question_id}: {t.old_status.value} -> {t.new_status.value} "
              f"(by {t.reviewer})")
    verb = "would apply" if args.dry_run else "applied"
    print(f"\n{verb} {len(report.transitions)} verdict(s); "
          f"{report.unchanged} row(s) unchanged.")
    return 0
```

Register inside `main`, alongside `review export`:

```python
    p_imp = review_sub.add_parser("import", help="write reviewer verdicts back")
    p_imp.add_argument("file")
    p_imp.add_argument("--banks", default=str(DEFAULT_BANKS))
    p_imp.add_argument("--date", help="review date, YYYY-MM-DD; defaults to today")
    p_imp.add_argument("--dry-run", action="store_true")
    p_imp.set_defaults(func=_cmd_review_import)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_review_import.py -v`
Expected: PASS, 13 passed

- [ ] **Step 5: Exercise the real round trip**

```bash
python -m atlas_eval.cli review export --bank v3 -o /tmp/v3_review.xlsx
python -m atlas_eval.cli review import /tmp/v3_review.xlsx --dry-run
git diff --stat data/banks/
```

Expected: export succeeds, the dry-run import reports 0 verdicts and 8 unchanged rows, and `git diff` is empty. An empty diff on an unedited round trip is the property that makes reviewer verdicts legible as diffs later.

- [ ] **Step 6: Commit**

```bash
python -m pytest -q
git add atlas_eval/review.py atlas_eval/cli.py tests/test_review_import.py
git commit -m "feat: import SME verdicts into bank YAML with abort-on-mismatch guards"
```

---

### Task 14: README and CI

Run this task after Task 15, since the README documents the `report` command.

**Files:**
- Create: `README.md`
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: the `atlas-eval` CLI.
- Produces: no code interfaces.

- [ ] **Step 1: Write the README**

```markdown
# Atlas Eval Harness

Auditing harness for the NJDOL Atlas chat agents. It evaluates the AWS Quick agent
today and is built so a local LLM and a future Bedrock agent can be scored against the
same frozen question banks, producing directly comparable numbers.

Design: [docs/superpowers/specs/2026-08-26-atlas-eval-harness-design.md](docs/superpowers/specs/2026-08-26-atlas-eval-harness-design.md)

## Layout

| Path | Contents |
|---|---|
| `data/banks/` | Frozen question banks, one YAML per version. Ground truth lives here. |
| `data/runs/` | One directory per run: metadata, responses, transcript, config snapshot, scores. |
| `data/scores.csv` | **Generated** rollup of every complete run. Do not hand edit. |
| `reference/` | Migrated audit material that is not part of the dataset. |
| `atlas_eval/` | The harness. |

## Everyday commands

Validate every bank offline (no AWS, no network):

    atlas-eval validate

Freeze a bank once its questions are settled:

    atlas-eval freeze --bank data/banks/v6.yaml --date 2026-09-01

Send a bank for SME review, then import the verdicts:

    atlas-eval review export --bank v3 --status unverified -o v3_review.xlsx
    atlas-eval review import v3_review_oscar.xlsx --dry-run
    atlas-eval review import v3_review_oscar.xlsx

Report scores for every run, verified and exploratory kept separate:

    atlas-eval report

## How scoring works

Two layers, kept separate on purpose.

**Deterministic** — literal, case-insensitive substring matching against each question's
`required_all`, `required_any`, `forbidden` and `expect_citations`. No model is involved
and no semantic similarity is used, so a score computed today is comparable to one from
three months ago.

**Rubric** — the five dimensions carried over from the original audit
(`citations`, `correctness`, `gap_honesty`, `scope_discipline`, `clarity`, 0-2 each).
An LLM drafts these against the answer key and a human reviews them, which is the
existing Quick Chat Audit process. Each row records `scored_by` and `confirmed_by`, so a
report can be restricted to human-confirmed scores.

## Ground truth and verification

The banks were built with AI assistance and are being verified by SMEs incrementally, so
`verification.status` is per question and a bank is normally partly verified. Reports give
two figures and never merge them: a **verified score** over `status: verified` questions,
which is the defensible number, and an **exploratory score** over the full bank, labelled
unvetted.

`rejected` questions stay in the file with the reason. Several questions have no knowable
answer, and keeping the verdict stops them being re-litigated.

## Development

    python -m pip install -e '.[dev]'
    atlas-eval validate
    python -m pytest -q

Both run without AWS credentials or network access.
```

- [ ] **Step 2: Write the CI workflow**

```yaml
# .github/workflows/ci.yml
name: ci

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: python -m pip install --upgrade pip
      - run: python -m pip install -e '.[dev]'
      # No AWS credentials are configured, by design: everything here is offline.
      - run: python -m atlas_eval.cli validate --banks data/banks
      - run: python -m pytest -q
```

- [ ] **Step 3: Verify both commands pass locally exactly as CI runs them**

```bash
python -m atlas_eval.cli validate --banks data/banks
python -m pytest -q
```

Expected: `validate` prints `OK: 6 bank(s), ...` and the suite is fully green.

- [ ] **Step 4: Commit**

```bash
git add README.md .github/workflows/ci.yml
git commit -m "docs: add README and offline CI workflow"
```

---

### Task 15: Verified and exploratory score reporting

The spec requires two figures that are never merged: a defensible score over `status: verified` questions and an exploratory score over the full bank. This is the command that produces the number you put in front of Billy, so the labelling matters as much as the arithmetic.

**Files:**
- Create: `atlas_eval/report.py`
- Modify: `atlas_eval/cli.py` (add `report`)
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: `load_all_banks`, `read_run`, `RunStatus`, `Rubric`.
- Produces:
  - `Subset` dataclass: `label: str`, `question_count: int`, `deterministic_pass: int`, `rubric_total: int | None`, `rubric_max: int | None`, `confirmed_count: int`
  - `RunReport` dataclass: `run_id`, `bank_version`, `backend`, `status`, `verified: Subset`, `exploratory: Subset`
  - `build_report(run_dir: Path, banks_dir: Path) -> RunReport`
  - `format_report(report: RunReport) -> str`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_report.py
from datetime import date, datetime
from pathlib import Path

import pytest

from atlas_eval.models import (
    Bank, Checks, Question, QuestionType, Stance, Verification, VerificationStatus,
)
from atlas_eval.report import build_report, format_report
from atlas_eval.runs import RunMeta, RunStatus, ScoreRow, write_run
from atlas_eval.scoring import Rubric, score_answer

BANK = """version: v3
agent: engineering_onboarding_specialist
corpus: quick_space_ca7_daily_s3
questions:
  - id: v3-Q1
    text: verified question
    type: retrieval
    expected_stance: answer
    ground_truth: gt
    checks:
      required_all: [ACP]
    verification:
      status: verified
      verified_by: Oscar
      verified_on: 2026-08-28
  - id: v3-Q2
    text: unverified question
    type: retrieval
    expected_stance: answer
    ground_truth: gt
    checks:
      required_all: [DXCBDA2R]
    verification:
      status: unverified
"""


def _setup(tmp_path, q1_answer, q2_answer, confirmed=True):
    banks = tmp_path / "banks"
    banks.mkdir()
    (banks / "v3.yaml").write_text(BANK)

    from atlas_eval.dataset import load_bank
    bank = load_bank(banks / "v3.yaml")
    q1, q2 = bank.questions

    def row(q, answer):
        return ScoreRow(
            question_id=q.id, type=q.type.value,
            verification_status=q.verification.status.value,
            rubric=Rubric(citations=2, correctness=2, gap_honesty=2,
                          scope_discipline=2, clarity=2,
                          scored_by="claude-opus-5",
                          confirmed_by="Michael" if confirmed else None),
            deterministic=score_answer(q, answer),
        )

    meta = RunMeta(
        run_id="2026-08-28_1000_quick_v3", backend="quick", transport="paste",
        bank_version="v3", question_sha256="x" * 64, agent="a",
        started_at=datetime(2026, 8, 28, 10, 0), finished_at=datetime(2026, 8, 28, 10, 30),
        status=RunStatus.COMPLETE,
    )
    runs = tmp_path / "runs"
    run_dir = write_run(runs, meta, {q1.id: q1_answer, q2.id: q2_answer}, "t", {},
                        [row(q1, q1_answer), row(q2, q2_answer)])
    return run_dir, banks


def test_verified_and_exploratory_counts_differ(tmp_path):
    run_dir, banks = _setup(tmp_path, "the ACP applies", "DXCBDA2R runs nightly")
    rep = build_report(run_dir, banks)
    assert rep.verified.question_count == 1
    assert rep.exploratory.question_count == 2
    assert rep.verified.label == "verified"
    assert rep.exploratory.label == "exploratory (unvetted)"


def test_verified_subset_excludes_unverified_failures(tmp_path):
    # Q1 (verified) passes; Q2 (unverified) fails. The defensible number is 1/1.
    run_dir, banks = _setup(tmp_path, "the ACP applies", "no mention of the program")
    rep = build_report(run_dir, banks)
    assert (rep.verified.deterministic_pass, rep.verified.question_count) == (1, 1)
    assert (rep.exploratory.deterministic_pass, rep.exploratory.question_count) == (1, 2)


def test_rubric_totals_are_summed_over_each_subset(tmp_path):
    run_dir, banks = _setup(tmp_path, "the ACP applies", "DXCBDA2R runs nightly")
    rep = build_report(run_dir, banks)
    assert (rep.verified.rubric_total, rep.verified.rubric_max) == (10, 10)
    assert (rep.exploratory.rubric_total, rep.exploratory.rubric_max) == (20, 20)


def test_confirmed_count_tracks_human_signoff(tmp_path):
    run_dir, banks = _setup(tmp_path, "the ACP applies", "DXCBDA2R runs nightly",
                            confirmed=False)
    rep = build_report(run_dir, banks)
    assert rep.exploratory.confirmed_count == 0
    assert rep.verified.confirmed_count == 0


def test_report_refuses_an_incomplete_run(tmp_path):
    run_dir, banks = _setup(tmp_path, "a", "b")
    text = (run_dir / "run.yaml").read_text().replace("complete", "incomplete")
    (run_dir / "run.yaml").write_text(text)
    with pytest.raises(ValueError) as exc:
        build_report(run_dir, banks)
    assert "incomplete" in str(exc.value)


def test_format_labels_the_unvetted_figure_explicitly(tmp_path):
    run_dir, banks = _setup(tmp_path, "the ACP applies", "no mention")
    text = format_report(build_report(run_dir, banks))
    assert "verified" in text and "unvetted" in text
    assert "1/1" in text and "1/2" in text
    # The two figures must never be presented as one number.
    assert "combined" not in text.lower()


def test_format_warns_when_no_questions_are_verified(tmp_path):
    banks = tmp_path / "banks"
    banks.mkdir()
    (banks / "v3.yaml").write_text(BANK.replace("status: verified", "status: unverified")
                                       .replace("verified_by: Oscar", "verified_by: null")
                                       .replace("verified_on: 2026-08-28", "verified_on: null"))
    run_dir, _ = _setup(tmp_path / "other", "the ACP applies", "DXCBDA2R runs nightly")
    rep = build_report(run_dir, banks)
    assert rep.verified.question_count == 0
    text = format_report(rep)
    assert "no verified questions" in text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_report.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas_eval.report'`

- [ ] **Step 3: Write the implementation**

```python
# atlas_eval/report.py
"""Reporting that keeps the defensible number separate from the exploratory one.

The banks were built with AI assistance and are verified incrementally, so a
run normally covers a partly verified bank. Merging the two figures would
present unvetted ground truth as though an SME had signed off on it, so they
are computed and printed separately, always.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from atlas_eval.dataset import load_all_banks
from atlas_eval.models import VerificationStatus
from atlas_eval.runs import RunStatus, read_run
from atlas_eval.scoring import RUBRIC_DIMENSIONS


@dataclass
class Subset:
    label: str
    question_count: int
    deterministic_pass: int
    rubric_total: int | None
    rubric_max: int | None
    confirmed_count: int


@dataclass
class RunReport:
    run_id: str
    bank_version: str
    backend: str
    status: RunStatus
    verified: Subset
    exploratory: Subset


def _read_deterministic_pass(run_dir: Path) -> dict[str, bool | None]:
    """scores.csv is the record; read the deterministic column back verbatim."""
    out: dict[str, bool | None] = {}
    with (run_dir / "scores.csv").open(newline="", encoding="utf-8") as fh:
        for rec in csv.DictReader(fh):
            raw = (rec.get("deterministic_pass") or "").strip()
            out[rec["question_id"]] = None if raw == "" else raw == "True"
    return out


def _subset(label: str, rows, passes: dict[str, bool | None]) -> Subset:
    scored = [r for r in rows if r.rubric.total is not None]
    return Subset(
        label=label,
        question_count=len(rows),
        deterministic_pass=sum(1 for r in rows if passes.get(r.question_id) is True),
        rubric_total=sum(r.rubric.total for r in scored) if scored else None,
        rubric_max=len(scored) * 2 * len(RUBRIC_DIMENSIONS) if scored else None,
        confirmed_count=sum(1 for r in rows if r.rubric.is_confirmed),
    )


def build_report(run_dir: Path, banks_dir: Path) -> RunReport:
    meta, _responses, rows = read_run(run_dir)
    if meta.status is not RunStatus.COMPLETE:
        raise ValueError(
            f"{meta.run_id} is {meta.status.value}; an incomplete run cannot be "
            "reported as a bank result"
        )

    bank = next((b for b in load_all_banks(banks_dir) if b.version == meta.bank_version), None)
    if bank is None:
        raise ValueError(f"no bank {meta.bank_version} under {banks_dir}")

    status_by_id = {q.id: q.verification.status for q in bank.questions}
    passes = _read_deterministic_pass(run_dir)

    verified_rows = [
        r for r in rows if status_by_id.get(r.question_id) is VerificationStatus.VERIFIED
    ]

    return RunReport(
        run_id=meta.run_id,
        bank_version=meta.bank_version,
        backend=meta.backend,
        status=meta.status,
        verified=_subset("verified", verified_rows, passes),
        exploratory=_subset("exploratory (unvetted)", rows, passes),
    )


def _line(s: Subset) -> str:
    rubric = (
        "rubric n/a" if s.rubric_total is None
        else f"rubric {s.rubric_total}/{s.rubric_max}"
    )
    return (f"  {s.label:<24} deterministic {s.deterministic_pass}/{s.question_count}"
            f"   {rubric}   human-confirmed {s.confirmed_count}/{s.question_count}")


def format_report(report: RunReport) -> str:
    lines = [
        f"{report.run_id}  ({report.backend}, bank {report.bank_version})",
        _line(report.verified),
        _line(report.exploratory),
    ]
    if report.verified.question_count == 0:
        lines.append(
            "  NOTE: no verified questions in this bank yet, so there is no "
            "defensible figure. Treat the exploratory number as unvetted."
        )
    return "\n".join(lines)
```

Add to `atlas_eval/cli.py`:

```python
def _cmd_report(args: argparse.Namespace) -> int:
    from atlas_eval.report import build_report, format_report

    run_dirs = (
        [Path(args.run)] if args.run
        else sorted(p for p in Path(args.runs).glob("*") if p.is_dir())
    )
    shown = 0
    for run_dir in run_dirs:
        try:
            print(format_report(build_report(run_dir, Path(args.banks))))
            shown += 1
        except ValueError as err:
            print(f"{run_dir.name}: skipped: {err}")
    if not shown:
        print("no complete runs to report")
        return 1
    return 0
```

Register inside `main`:

```python
    p_rep = sub.add_parser("report", help="verified and exploratory scores per run")
    p_rep.add_argument("--run", help="a single run directory; default is all runs")
    p_rep.add_argument("--runs", default="data/runs")
    p_rep.add_argument("--banks", default=str(DEFAULT_BANKS))
    p_rep.set_defaults(func=_cmd_report)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_report.py -v`
Expected: PASS, 7 passed

- [ ] **Step 5: Report on the migrated runs**

```bash
python -m atlas_eval.cli report --banks data/banks --runs data/runs | head -30
```

Expected: one block per migrated run. Every block shows `deterministic 0/N` (legacy runs were never deterministically scored, so the column is empty), real rubric totals, and `human-confirmed 0/N` unless you stamped `--confirmed-by` during migration. Each should carry the "no verified questions" note until the SME pass lands.

- [ ] **Step 6: Commit**

```bash
python -m pytest -q
git add atlas_eval/report.py atlas_eval/cli.py tests/test_report.py
git commit -m "feat: report verified and exploratory scores as separate figures"
```
