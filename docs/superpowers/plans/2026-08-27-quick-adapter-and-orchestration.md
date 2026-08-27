# Quick Adapter and Run Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute a frozen question bank against the AWS Quick chat agent and produce a scored run record identical in shape to what a Bedrock or local-LLM backend will later produce.

**Architecture:** One `Backend` protocol every future backend implements. The Quick backend has two interchangeable transports — `paste` (operator pastes a transcript, zero UI risk) and `playwright` (drives the UI using selectors the recon spike established). DOM extraction lives in its own pure module so it is tested against a committed fixture with no browser session. An orchestrator wires snapshot → ask → score → `write_run`, and knows nothing about which transport ran.

**Tech Stack:** Python 3.11+, pydantic v2, Playwright (chromium), ruamel.yaml, openpyxl, pytest, `aws quicksight` CLI (read-only control plane).

## Global Constraints

- **Every backend produces an identically shaped run directory:** `run.yaml`, `responses.yaml`, `transcript.md`, `snapshot.json`, `scores.csv`. Never add a backend-specific field.
- **Adapters never score.** An adapter returns raw answer text. `atlas_eval/scoring.py` stays the only scorer and must never be imported by an adapter.
- **The harness never authenticates.** No credential entry, no password typing, no MFA handling. The operator logs in; the transport detects a login redirect and aborts.
- **A run that cannot complete every question is `status: incomplete`**, is still written to disk, and is refused as a bank result by `report`. Fail closed.
- **Run order is `resolve_run_order(bank)`, always.** Four questions carry `after` dependencies (v3-Q2→Q1, v3-Q5→Q4, v3-Q7→Q6, v4-Q6→Q5) and must be asked in one continuous conversation. Never reorder, never split the conversation.
- **A frozen bank whose `question_sha256` no longer matches must not be run.** Refuse before asking anything.
- **Never commit a raw Quick capture.** They carry AWS account ids and a federated ARN with the operator's email. `tests/fixtures/quick/*.html` is gitignored except `sanitized_*.html`.
- **Fixture tests must use `java_script_enabled=False`.** The live page is a React SPA; its scripts wipe captured markup on re-mount and every selector silently returns empty.

## Established selectors (from `docs/recon/2026-08-27-quick-chat-dom.md`)

Verified against the live agent 2026-08-27. Do not invent alternatives.

| Purpose | Selector |
|---|---|
| Message input | `[data-testid="qbiz-components-prompt-textarea"]` |
| Thread container (also holds `data-conversation-id`) | `[data-testid="chat-panel-conversation-thread-container"]` |
| User turn | `[data-testid="user-chat-message-container"]` |
| Agent turn (its `innerText` is the answer) | `[data-testid="ai-chat-message-container"]` |
| **Completion: one per COMPLETED answer** | `[data-testid="qbiz-component-ai-message-footer"]` |
| Citation | `[data-testid="citation-reference"]` |
| Model chip | `[data-testid="qbiz-model-selection-chip"]` |
| Agent selector wrapper | `[data-testid="qbiz-component-chat-experience-agent-selector-wrapper"]` |
| Completion announcement | `div[role="status"]` containing `New message from <agent name>` |

**Ruled out by the spike:** `aria-busy` (absent at every capture point) and `id="base-ui-:rNN:"` (16 of 55 ids churned within one session). Neither may be used.

---

### Task 1: Backend protocol and the Response type

**Files:**
- Create: `atlas_eval/adapters/__init__.py`
- Create: `atlas_eval/adapters/base.py`
- Test: `tests/test_adapters_base.py`

**Interfaces:**
- Consumes: `Question` from `atlas_eval.models`.
- Produces:
  - `Response` pydantic model: `question_id: str`, `answer: str`, `asked_at: datetime`, `citations: list[str]` (default empty), `observed_stance: Stance | None = None`
  - `AskResult` pydantic model: `responses: list[Response]`, `conversation_id: str | None`, `complete: bool`, `failure: str | None`
  - `TransportError(Exception)` with `.code` in `{"AUTH_REQUIRED", "SELECTOR_MISSING", "TIMEOUT", "CONVERSATION_LOST", "PARSE_FAILED"}` and `.detail: str`
  - `Backend(Protocol)`: attributes `name: str`, `transport: str`; methods `snapshot(self) -> dict` and `ask(self, questions: list[Question]) -> AskResult`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_adapters_base.py
from datetime import datetime

import pytest
from pydantic import ValidationError

from atlas_eval.adapters.base import AskResult, Backend, Response, TransportError
from atlas_eval.models import Question, QuestionType, Stance


def _q(qid="v1-Q1"):
    return Question(id=qid, text="t", type=QuestionType.RETRIEVAL,
                    expected_stance=Stance.ANSWER, ground_truth="gt")


def test_response_defaults():
    r = Response(question_id="v1-Q1", answer="a", asked_at=datetime(2026, 8, 27, 9, 0))
    assert r.citations == []
    assert r.observed_stance is None


def test_response_default_citations_not_shared():
    a = Response(question_id="v1-Q1", answer="a", asked_at=datetime(2026, 8, 27, 9, 0))
    b = Response(question_id="v1-Q2", answer="b", asked_at=datetime(2026, 8, 27, 9, 1))
    a.citations.append("DXCBD87E")
    assert b.citations == []


def test_response_rejects_unknown_field():
    with pytest.raises(ValidationError):
        Response(question_id="v1-Q1", answer="a",
                 asked_at=datetime(2026, 8, 27, 9, 0), scored=True)


def test_ask_result_complete_and_failed_shapes():
    ok = AskResult(responses=[], conversation_id="c1", complete=True)
    assert ok.failure is None

    bad = AskResult(responses=[], conversation_id=None, complete=False,
                    failure="AUTH_REQUIRED: login redirect detected")
    assert bad.complete is False and "AUTH_REQUIRED" in bad.failure


def test_transport_error_carries_code_and_detail():
    err = TransportError("AUTH_REQUIRED", "redirected to /start/home?redirect_uri=")
    assert err.code == "AUTH_REQUIRED"
    assert "redirect_uri" in err.detail
    assert "AUTH_REQUIRED" in str(err)


def test_a_minimal_class_satisfies_the_protocol():
    class Fake:
        name = "fake"
        transport = "memory"

        def snapshot(self) -> dict:
            return {"agent": "fake"}

        def ask(self, questions):
            return AskResult(
                responses=[Response(question_id=q.id, answer=f"answer to {q.id}",
                                    asked_at=datetime(2026, 8, 27, 9, 0))
                           for q in questions],
                conversation_id="c1", complete=True,
            )

    fake: Backend = Fake()
    result = fake.ask([_q("v1-Q1"), _q("v1-Q2")])
    assert [r.question_id for r in result.responses] == ["v1-Q1", "v1-Q2"]
    assert isinstance(fake.snapshot(), dict)


def test_adapters_never_import_the_scorer():
    # An adapter returns raw text; scoring is a separate layer that must not be
    # reachable from transport code, or a transport bug could alter a score.
    import atlas_eval.adapters.base as mod
    src = open(mod.__file__).read()
    assert "scoring" not in src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_adapters_base.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas_eval.adapters'`

- [ ] **Step 3: Write the implementation**

```python
# atlas_eval/adapters/__init__.py
"""Backend adapters. Each returns raw answers; none of them score."""

__all__ = ["base"]
```

```python
# atlas_eval/adapters/base.py
"""The one interface every backend implements.

An adapter's only job is to get raw answer text out of a backend, in the order
asked. It never scores, never writes a run record, and never authenticates.
Keeping that boundary is what makes a Quick run and a future Bedrock run
comparable: the same orchestrator, the same scorer, the same record.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from atlas_eval.models import Question, Stance


class Response(BaseModel):
    """One backend answer, exactly as returned. Never post-processed here."""

    model_config = ConfigDict(extra="forbid")

    question_id: str
    answer: str
    asked_at: datetime
    citations: list[str] = Field(default_factory=list)
    # Supplied only when the transport can observe it (for example a UI refusal
    # marker). Otherwise a human sets it during review. Never inferred by model.
    observed_stance: Stance | None = None


class AskResult(BaseModel):
    """The outcome of asking a whole bank in one conversation."""

    model_config = ConfigDict(extra="forbid")

    responses: list[Response] = Field(default_factory=list)
    conversation_id: str | None = None
    complete: bool = False
    failure: str | None = None


class TransportError(Exception):
    """A transport could not continue. Codes are stable; messages are not."""

    CODES = (
        "AUTH_REQUIRED",
        "SELECTOR_MISSING",
        "TIMEOUT",
        "CONVERSATION_LOST",
        "PARSE_FAILED",
    )

    def __init__(self, code: str, detail: str) -> None:
        if code not in self.CODES:
            raise ValueError(f"unknown TransportError code: {code!r}")
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@runtime_checkable
class Backend(Protocol):
    """Implemented by the Quick adapter now, Bedrock and a local LLM later."""

    name: str
    transport: str

    def snapshot(self) -> dict:
        """Config that makes a later score interpretable. Read-only."""
        ...

    def ask(self, questions: list[Question]) -> AskResult:
        """Ask in the given order, in ONE conversation, and return raw answers.

        The order is already resolved by resolve_run_order and must not be
        changed: several questions only work immediately after their predecessor.
        """
        ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_adapters_base.py -v`
Expected: PASS, 7 passed

- [ ] **Step 5: Commit**

```bash
git add atlas_eval/adapters/ tests/test_adapters_base.py
git commit -m "feat: add the Backend protocol every adapter implements"
```

---

### Task 2: DOM extraction, tested against the committed fixture

The highest-value unit in this plan: pure functions over a page, with no browser session and no auth. If this is right, the transport is mostly plumbing.

**Files:**
- Create: `atlas_eval/adapters/quick_dom.py`
- Test: `tests/test_quick_dom.py`

**Interfaces:**
- Consumes: `Response` from `atlas_eval.adapters.base`.
- Produces:
  - Selector constants: `SEL_INPUT`, `SEL_THREAD`, `SEL_USER_TURN`, `SEL_AI_TURN`, `SEL_AI_FOOTER`, `SEL_CITATION`, `SEL_MODEL_CHIP`, `SEL_AGENT_SELECTOR`, `SEL_STATUS`
  - `AUTH_URL_MARKERS: tuple[str, ...]`
  - `completed_answer_count(page) -> int`
  - `conversation_id(page) -> str | None`
  - `model_chip(page) -> str | None`
  - `agent_from_status(page) -> str | None`
  - `answer_texts(page) -> list[str]`
  - `question_texts(page) -> list[str]`
  - `citation_labels(page) -> list[str]`
  - `is_auth_redirect(url: str) -> bool`

`page` is any object exposing Playwright's sync `locator()` API. Tests pass a real Playwright page over the committed fixture, so no fake is needed.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_quick_dom.py
from pathlib import Path

import pytest

from atlas_eval.adapters import quick_dom as qd

FIXTURE = Path("tests/fixtures/quick/sanitized_conversation_complete.html")


@pytest.fixture(scope="module")
def page():
    """The committed fixture, loaded the ONLY way that works.

    java_script_enabled=False is mandatory: the real page is a React SPA and its
    own scripts wipe the captured markup on re-mount, after which every selector
    returns empty and the tests pass for the wrong reason.
    """
    pw = pytest.importorskip("playwright.sync_api")
    with pw.sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(java_script_enabled=False)
        pg = ctx.new_page()
        pg.goto("file://" + str(FIXTURE.resolve()))
        yield pg
        browser.close()


def test_fixture_exists_and_is_sanitized():
    text = FIXTURE.read_text()
    assert "arn:aws" not in text
    assert "dol.nj.gov" not in text
    assert "SANITIZED" in text


def test_completed_answer_count_matches_the_footers(page):
    # One footer renders per COMPLETED answer. The fixture holds two.
    assert qd.completed_answer_count(page) == 2


def test_conversation_id_is_read_from_the_thread_container(page):
    assert qd.conversation_id(page) == "00000000-0000-4000-8000-000000000000"


def test_model_chip(page):
    assert qd.model_chip(page) == "Advanced"


def test_agent_name_from_the_status_announcement(page):
    assert qd.agent_from_status(page) == "Engineering Onboarding Specialist"


def test_answer_and_question_texts_pair_up(page):
    answers, questions = qd.answer_texts(page), qd.question_texts(page)
    assert len(answers) == len(questions) == 2
    assert "L204DF2" in questions[0]


def test_answer_text_is_whole_not_truncated(page):
    answer = qd.answer_texts(page)[0]
    assert len(answer) > 4000, "the real answer is ~4.8k chars"
    # Terms that live inside markdown tables must survive extraction, because
    # the deterministic scorer matches against exactly this string.
    for term in ("BNKFLMOD", "BNKFLDTE", "BANKMTCH", "CHECKS.ISSUED", "ACC2528"):
        assert term.lower() in answer.lower(), term


def test_citation_labels(page):
    labels = qd.citation_labels(page)
    assert labels and all(l.startswith("Citation") for l in labels)


def test_auth_redirect_detection():
    assert qd.is_auth_redirect(
        "https://us-east-1.quicksight.aws.amazon.com/sn/account/njuimod/start/home"
        "?redirect_uri=https%3A%2F%2F...%26isauthcode%3Dtrue"
    )
    assert qd.is_auth_redirect("https://x/start/home?redirect_uri=y")
    assert not qd.is_auth_redirect(
        "https://us-east-1.quicksight.aws.amazon.com/sn/account/njuimod/start/agents"
    )


def test_selectors_avoid_the_ruled_out_mechanisms():
    src = open(qd.__file__).read()
    # aria-busy was absent at every capture point; base-ui ids churned 16/55
    # within a single session. Either would produce silent, intermittent failure.
    assert "aria-busy" not in src
    assert "base-ui" not in src


def test_module_never_imports_the_scorer():
    src = open(qd.__file__).read()
    assert "scoring" not in src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_quick_dom.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas_eval.adapters.quick_dom'`

- [ ] **Step 3: Write the implementation**

```python
# atlas_eval/adapters/quick_dom.py
"""Reading the Quick chat DOM.

Quick is Amazon Q Business components (`qbiz-*`) embedded in QuickSuite. Every
selector below was verified against the live agent on 2026-08-27 and is recorded
in docs/recon/2026-08-27-quick-chat-dom.md.

Two mechanisms are deliberately NOT used:
  * `aria-busy` — absent at every capture point, so it can never fire.
  * `id="base-ui-:rNN:"` — React-generated; 16 of 55 button ids changed within a
    single session, which would fail intermittently and look like a Quick bug.

Completion is detected positively: one message footer renders per COMPLETED
answer, so the transport waits for that count to reach the number of questions
asked. Waiting for a control to disappear cannot distinguish "finished" from
"never started".
"""

from __future__ import annotations

SEL_INPUT = '[data-testid="qbiz-components-prompt-textarea"]'
SEL_THREAD = '[data-testid="chat-panel-conversation-thread-container"]'
SEL_USER_TURN = '[data-testid="user-chat-message-container"]'
SEL_AI_TURN = '[data-testid="ai-chat-message-container"]'
SEL_AI_FOOTER = '[data-testid="qbiz-component-ai-message-footer"]'
SEL_CITATION = '[data-testid="citation-reference"]'
SEL_MODEL_CHIP = '[data-testid="qbiz-model-selection-chip"]'
SEL_AGENT_SELECTOR = '[data-testid="qbiz-component-chat-experience-agent-selector-wrapper"]'
SEL_STATUS = 'div[role="status"]'

# The run state is not URL-addressable: the landing and run-ready URLs were
# byte-identical, and both are the auth redirect. So these markers mean "we are
# looking at a login hop, not the chat".
AUTH_URL_MARKERS: tuple[str, ...] = ("/start/home?redirect_uri=", "isauthcode=true")

_STATUS_PREFIX = "New message from "


def is_auth_redirect(url: str) -> bool:
    return any(marker in url for marker in AUTH_URL_MARKERS)


def completed_answer_count(page) -> int:
    """How many answers have finished rendering. The completion signal."""
    return page.locator(SEL_AI_FOOTER).count()


def conversation_id(page) -> str | None:
    thread = page.locator(SEL_THREAD).first
    if thread.count() == 0:
        return None
    return thread.get_attribute("data-conversation-id")


def _first_text(page, selector: str) -> str | None:
    loc = page.locator(selector).first
    if loc.count() == 0:
        return None
    return loc.inner_text().strip() or None


def model_chip(page) -> str | None:
    """Which model backs the agent. Worth recording in the run snapshot."""
    return _first_text(page, SEL_MODEL_CHIP)


def agent_from_status(page) -> str | None:
    """Agent name from the completion announcement.

    Needed because the agent id is absent from the DOM, so this is the only
    in-page confirmation that the intended agent answered.
    """
    for text in page.locator(SEL_STATUS).all_inner_texts():
        stripped = text.strip()
        if stripped.startswith(_STATUS_PREFIX):
            return stripped[len(_STATUS_PREFIX):].strip() or None
    return None


def answer_texts(page) -> list[str]:
    """Full answer text per agent turn, in order.

    innerText keeps markdown tables and code blocks readable, which matters
    because scorer check terms live inside them.
    """
    return [t.strip() for t in page.locator(SEL_AI_TURN).all_inner_texts()]


def question_texts(page) -> list[str]:
    return [t.strip() for t in page.locator(SEL_USER_TURN).all_inner_texts()]


def citation_labels(page) -> list[str]:
    labels = []
    for i in range(page.locator(SEL_CITATION).count()):
        label = page.locator(SEL_CITATION).nth(i).get_attribute("aria-label")
        if label:
            labels.append(label.strip())
    return labels
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_quick_dom.py -v`
Expected: PASS, 11 passed

- [ ] **Step 5: Commit**

```bash
git add atlas_eval/adapters/quick_dom.py tests/test_quick_dom.py
git commit -m "feat: read the Quick chat DOM using recon-verified selectors"
```

---

### Task 3: Transcript rendering

`transcript.md` is the human-readable half of a run record and the thing anyone re-grading a run actually reads. The 27 migrated legacy transcripts set the format; match their spirit rather than inventing one.

**Files:**
- Create: `atlas_eval/transcript.py`
- Test: `tests/test_transcript.py`

**Interfaces:**
- Consumes: `RunMeta` from `atlas_eval.runs`, `Response` from `atlas_eval.adapters.base`, `Question` from `atlas_eval.models`.
- Produces: `render_transcript(meta: RunMeta, questions: list[Question], responses: list[Response], snapshot: dict) -> str`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_transcript.py
from datetime import datetime

from atlas_eval.adapters.base import Response
from atlas_eval.models import Question, QuestionType, Stance
from atlas_eval.runs import RunMeta, RunStatus
from atlas_eval.transcript import render_transcript


def _meta(**over):
    base = dict(
        run_id="2026-08-27_0900_quick_v3", backend="quick", transport="playwright",
        bank_version="v3", question_sha256="a" * 64,
        agent="engineering_onboarding_specialist",
        agent_id="093ac4e3-0712-481e-af95-9ddc5e4fc734",
        conversation_id="0f7d8a7d-21b5-4c8f-a278-42b98aa6fcf8",
        started_at=datetime(2026, 8, 27, 9, 0), finished_at=datetime(2026, 8, 27, 9, 30),
        status=RunStatus.COMPLETE,
    )
    base.update(over)
    return RunMeta(**base)


def _q(qid, text, after=None):
    return Question(id=qid, text=text, type=QuestionType.RETRIEVAL,
                    expected_stance=Stance.ANSWER, ground_truth="gt", after=after)


def _r(qid, answer, minute):
    return Response(question_id=qid, answer=answer,
                    asked_at=datetime(2026, 8, 27, 9, minute))


def test_header_carries_the_facts_needed_to_reinterpret_a_score():
    text = render_transcript(
        _meta(), [_q("v3-Q1", "first question")], [_r("v3-Q1", "first answer", 5)],
        {"model_chip": "Advanced"},
    )
    for expected in ("2026-08-27_0900_quick_v3", "quick", "playwright", "v3",
                     "engineering_onboarding_specialist",
                     "0f7d8a7d-21b5-4c8f-a278-42b98aa6fcf8", "Advanced"):
        assert expected in text, expected


def test_questions_and_answers_appear_in_asked_order():
    text = render_transcript(
        _meta(), [_q("v3-Q1", "first question"), _q("v3-Q2", "second question", after="v3-Q1")],
        [_r("v3-Q1", "first answer", 5), _r("v3-Q2", "second answer", 8)], {},
    )
    assert text.index("first question") < text.index("second question")
    assert text.index("first answer") < text.index("second answer")


def test_after_dependency_is_called_out():
    # A later reader must be able to see that Q2's answer only means anything
    # because Q1 immediately preceded it.
    text = render_transcript(
        _meta(), [_q("v3-Q1", "q one"), _q("v3-Q2", "q two", after="v3-Q1")],
        [_r("v3-Q1", "a one", 5), _r("v3-Q2", "a two", 8)], {},
    )
    assert "after v3-Q1" in text


def test_unanswered_question_is_marked_not_silently_dropped():
    text = render_transcript(
        _meta(status=RunStatus.INCOMPLETE, finished_at=None),
        [_q("v3-Q1", "q one"), _q("v3-Q2", "q two")], [_r("v3-Q1", "a one", 5)], {},
    )
    assert "q two" in text
    assert "NO ANSWER" in text
    assert "incomplete" in text.lower()


def test_answer_text_is_never_truncated():
    long_answer = "X" * 9000
    text = render_transcript(_meta(), [_q("v3-Q1", "q")], [_r("v3-Q1", long_answer, 5)], {})
    assert long_answer in text


def test_is_markdown_with_one_top_level_heading():
    text = render_transcript(_meta(), [_q("v3-Q1", "q")], [_r("v3-Q1", "a", 5)], {})
    assert text.startswith("# ")
    assert sum(1 for line in text.splitlines() if line.startswith("# ")) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_transcript.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas_eval.transcript'`

- [ ] **Step 3: Write the implementation**

```python
# atlas_eval/transcript.py
"""Render the human-readable half of a run record.

Anyone re-grading a run six months later reads this file, not the CSV. It has to
carry enough context to reinterpret a score: which agent, which model, which
conversation, and which questions were primed by the one before them.
"""

from __future__ import annotations

from atlas_eval.adapters.base import Response
from atlas_eval.models import Question
from atlas_eval.runs import RunMeta

_MISSING = "**NO ANSWER** — the run did not capture a response for this question."


def render_transcript(
    meta: RunMeta,
    questions: list[Question],
    responses: list[Response],
    snapshot: dict,
) -> str:
    by_id = {r.question_id: r for r in responses}

    lines: list[str] = [
        f"# {meta.run_id}",
        "",
        f"- **Backend:** {meta.backend} (transport: {meta.transport})",
        f"- **Bank:** {meta.bank_version} (`question_sha256` {meta.question_sha256[:12]}…)",
        f"- **Agent:** {meta.agent}" + (f" (`{meta.agent_id}`)" if meta.agent_id else ""),
    ]
    if meta.conversation_id:
        lines.append(f"- **Conversation:** `{meta.conversation_id}`")
    model = snapshot.get("model_chip")
    if model:
        lines.append(f"- **Model:** {model}")
    lines += [
        f"- **Started:** {meta.started_at:%Y-%m-%d %H:%M}",
        f"- **Finished:** " + (f"{meta.finished_at:%Y-%m-%d %H:%M}"
                               if meta.finished_at else "—"),
        f"- **Status:** {meta.status.value}",
        f"- **Questions asked:** {len(questions)}, answered: {len(responses)}",
        "",
    ]

    if meta.status.value != "complete":
        lines += [
            "> This run is **incomplete** and is excluded from bank-level results. "
            "It is kept for diagnosis only.",
            "",
        ]

    for question in questions:
        heading = f"## {question.id}"
        if question.after:
            heading += f" (asked immediately after {question.after})"
        lines += [heading, "", f"**Q:** {question.text}", ""]

        response = by_id.get(question.id)
        if response is None:
            lines += [_MISSING, ""]
            continue

        lines += [f"**A** ({response.asked_at:%H:%M}):", "", response.answer, ""]
        if response.citations:
            lines += ["_Citations: " + ", ".join(response.citations) + "_", ""]

    return "\n".join(lines).rstrip() + "\n"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_transcript.py -v`
Expected: PASS, 6 passed

- [ ] **Step 5: Commit**

```bash
git add atlas_eval/transcript.py tests/test_transcript.py
git commit -m "feat: render run transcripts with priming context intact"
```

---

### Task 4: Agent and space snapshot via the read-only control plane

**Files:**
- Create: `atlas_eval/snapshot.py`
- Test: `tests/test_snapshot.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `SnapshotError(Exception)`
  - `AwsRunner` protocol: `__call__(self, args: list[str]) -> str` returning stdout
  - `default_aws_runner(args: list[str]) -> str` — runs `aws` via `subprocess`, read-only
  - `capture(account_id: str, agent_id: str | None = None, runner=default_aws_runner) -> dict`

`capture` shells out to `aws quicksight` read-only operations only: `list-agents`, `describe-agent`, `list-spaces`. It never calls `create-*`, `update-*`, or `delete-*`. Tests inject a fake runner, so no AWS access is needed.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_snapshot.py
import json

import pytest

from atlas_eval.snapshot import SnapshotError, capture

AGENTS = {"AgentSummaryList": [
    {"AgentId": "093ac4e3-0712-481e-af95-9ddc5e4fc734",
     "Name": "Engineering Onboarding Specialist"},
    {"AgentId": "aaaaaaaa-0000-0000-0000-000000000000", "Name": "Other Agent"},
]}
AGENT = {"Agent": {"AgentId": "093ac4e3-0712-481e-af95-9ddc5e4fc734",
                   "Name": "Engineering Onboarding Specialist",
                   "Instructions": "you are an onboarding specialist"}}
SPACES = {"SpaceSummaryList": [{"SpaceId": "s1", "Name": "quick_space_ca7_daily_s3"}]}


def _runner(calls, responses):
    def run(args):
        calls.append(args)
        for key, payload in responses.items():
            if key in args:
                return json.dumps(payload)
        raise AssertionError(f"unexpected call: {args}")
    return run


def test_capture_records_agent_and_spaces():
    calls = []
    snap = capture("123456789012", agent_id="093ac4e3-0712-481e-af95-9ddc5e4fc734",
                   runner=_runner(calls, {"list-agents": AGENTS,
                                          "describe-agent": AGENT,
                                          "list-spaces": SPACES}))
    assert snap["agent"]["Name"] == "Engineering Onboarding Specialist"
    assert snap["spaces"][0]["Name"] == "quick_space_ca7_daily_s3"
    assert snap["captured_with"] == "aws quicksight (read-only)"


def test_capture_uses_only_read_only_operations():
    calls = []
    capture("123456789012", agent_id="093ac4e3-0712-481e-af95-9ddc5e4fc734",
            runner=_runner(calls, {"list-agents": AGENTS, "describe-agent": AGENT,
                                   "list-spaces": SPACES}))
    flat = [a for call in calls for a in call]
    for forbidden in ("create-agent", "update-agent", "delete-agent",
                      "update-space", "update-space-resources", "delete-space"):
        assert forbidden not in flat, forbidden
    assert all(call[0] == "quicksight" for call in calls)


def test_account_id_is_not_stored_in_the_snapshot():
    # Snapshots are committed; an AWS account id must not enter the repo.
    snap = capture("123456789012", agent_id="093ac4e3-0712-481e-af95-9ddc5e4fc734",
                   runner=_runner([], {"list-agents": AGENTS, "describe-agent": AGENT,
                                       "list-spaces": SPACES}))
    assert "123456789012" not in json.dumps(snap)


def test_agent_id_resolved_by_name_when_not_given():
    snap = capture("123456789012", agent_id=None,
                   runner=_runner([], {"list-agents": AGENTS, "describe-agent": AGENT,
                                       "list-spaces": SPACES}),
                   agent_name="Engineering Onboarding Specialist")
    assert snap["agent"]["AgentId"] == "093ac4e3-0712-481e-af95-9ddc5e4fc734"


def test_unknown_agent_name_raises():
    with pytest.raises(SnapshotError) as exc:
        capture("123456789012", agent_id=None,
                runner=_runner([], {"list-agents": AGENTS}),
                agent_name="No Such Agent")
    assert "No Such Agent" in str(exc.value)


def test_cli_failure_surfaces_as_snapshot_error():
    def boom(args):
        raise OSError("aws: command not found")
    with pytest.raises(SnapshotError) as exc:
        capture("123456789012", agent_id="x", runner=boom)
    assert "aws" in str(exc.value)


def test_bad_json_surfaces_as_snapshot_error():
    with pytest.raises(SnapshotError):
        capture("123456789012", agent_id="x", runner=lambda args: "not json")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_snapshot.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas_eval.snapshot'`

- [ ] **Step 3: Write the implementation**

```python
# atlas_eval/snapshot.py
"""Capture the agent and space configuration a run was executed against.

Without this, an old score is uninterpretable: you cannot tell whether a
regression came from the model, the instructions, or the corpus. Everything here
is read-only — the harness reads agent config and never writes it.

The AWS account id is used to scope the calls but is deliberately never stored:
snapshots are committed to the repo.
"""

from __future__ import annotations

import json
import subprocess

READ_ONLY_OPS = ("list-agents", "describe-agent", "list-spaces")


class SnapshotError(Exception):
    """The control-plane capture could not be completed."""


def default_aws_runner(args: list[str]) -> str:
    """Run `aws <args>` and return stdout. Read-only calls only."""
    if args[1] not in READ_ONLY_OPS:
        raise SnapshotError(f"refusing non-read-only operation: {args[1]}")
    completed = subprocess.run(
        ["aws", *args, "--output", "json"],
        capture_output=True, text=True, check=False,
    )
    if completed.returncode != 0:
        raise SnapshotError(
            f"aws {' '.join(args)} failed ({completed.returncode}): "
            f"{completed.stderr.strip()[:400]}"
        )
    return completed.stdout


def _call(runner, args: list[str]) -> dict:
    try:
        raw = runner(args)
    except SnapshotError:
        raise
    except Exception as err:  # OSError, subprocess problems, injected fakes
        raise SnapshotError(f"aws {' '.join(args)} failed: {err}") from err
    try:
        return json.loads(raw)
    except json.JSONDecodeError as err:
        raise SnapshotError(f"aws {' '.join(args)} returned non-JSON: {err}") from err


def capture(
    account_id: str,
    agent_id: str | None = None,
    runner=default_aws_runner,
    agent_name: str | None = None,
) -> dict:
    """Snapshot the agent and its linked spaces.

    Pass agent_id when known. Otherwise pass agent_name and it is resolved from
    list-agents, so a run is never recorded against a guessed agent.
    """
    agents = _call(runner, ["quicksight", "list-agents", "--aws-account-id", account_id])

    if agent_id is None:
        if not agent_name:
            raise SnapshotError("one of agent_id or agent_name is required")
        matches = [a for a in agents.get("AgentSummaryList", [])
                   if a.get("Name") == agent_name]
        if not matches:
            available = ", ".join(sorted(
                a.get("Name", "?") for a in agents.get("AgentSummaryList", [])
            ))
            raise SnapshotError(
                f"no agent named {agent_name!r}; available: {available or '(none)'}"
            )
        agent_id = matches[0]["AgentId"]

    agent = _call(runner, ["quicksight", "describe-agent", "--aws-account-id",
                           account_id, "--agent-id", agent_id])
    spaces = _call(runner, ["quicksight", "list-spaces", "--aws-account-id", account_id])

    return {
        "captured_with": "aws quicksight (read-only)",
        "operations": list(READ_ONLY_OPS),
        "agent": agent.get("Agent", {}),
        "agent_list": agents.get("AgentSummaryList", []),
        "spaces": spaces.get("SpaceSummaryList", []),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_snapshot.py -v`
Expected: PASS, 7 passed

- [ ] **Step 5: Commit**

```bash
git add atlas_eval/snapshot.py tests/test_snapshot.py
git commit -m "feat: capture agent and space config through read-only calls"
```

---

### Task 5: Quick paste transport

Built before the Playwright transport on purpose: it is immediately usable, has no UI risk, and it forces the parsing and ordering logic into shape where it can be tested against the 27 migrated legacy transcripts.

**Files:**
- Create: `atlas_eval/adapters/quick_paste.py`
- Test: `tests/test_quick_paste.py`

**Interfaces:**
- Consumes: `AskResult`, `Response`, `TransportError` from `atlas_eval.adapters.base`; `Question` from `atlas_eval.models`.
- Produces:
  - `PROMPT_HEADER: str`
  - `render_prompt_sheet(questions: list[Question]) -> str`
  - `parse_pasted_transcript(text: str, questions: list[Question], asked_at: datetime) -> AskResult`
  - `QuickPasteBackend` class: `__init__(self, agent: str, snapshot_data: dict, transcript_text: str)`, attributes `name = "quick"` / `transport = "paste"`, methods `snapshot()` and `ask(questions)`

Paste format: the operator copies each answer under a line containing the question id in the form `### <question-id>`. That is the same delimiter the existing answer-key notes use, so it is already familiar.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_quick_paste.py
from datetime import datetime

import pytest

from atlas_eval.adapters.quick_paste import (
    QuickPasteBackend, parse_pasted_transcript, render_prompt_sheet,
)
from atlas_eval.models import Question, QuestionType, Stance

ASKED = datetime(2026, 8, 27, 9, 0)


def _q(qid, text="question text", after=None):
    return Question(id=qid, text=text, type=QuestionType.RETRIEVAL,
                    expected_stance=Stance.ANSWER, ground_truth="gt", after=after)


def test_prompt_sheet_lists_questions_in_given_order_with_ids():
    sheet = render_prompt_sheet([_q("v3-Q1", "first"), _q("v3-Q2", "second", after="v3-Q1")])
    assert sheet.index("v3-Q1") < sheet.index("v3-Q2")
    assert "first" in sheet and "second" in sheet


def test_prompt_sheet_flags_the_immediately_after_constraint():
    # The operator must not interleave anything, or the probe is destroyed.
    sheet = render_prompt_sheet([_q("v3-Q1"), _q("v3-Q2", after="v3-Q1")])
    assert "immediately after v3-Q1" in sheet
    assert "same conversation" in sheet.lower()


def test_parse_extracts_answers_by_id_heading():
    text = "### v3-Q1\nThe ACP is the Accelerated Collection Process.\n\n### v3-Q2\nACP.\n"
    result = parse_pasted_transcript(text, [_q("v3-Q1"), _q("v3-Q2")], ASKED)
    assert result.complete is True
    assert [r.question_id for r in result.responses] == ["v3-Q1", "v3-Q2"]
    assert "Accelerated Collection Process" in result.responses[0].answer


def test_parse_preserves_multi_paragraph_answers_and_code_blocks():
    answer = "Line one.\n\n```\nCOMPUTE WS-PWBR1 = (BP88-WBR * 1.2)\n```\n\nLine two."
    text = f"### v3-Q1\n{answer}\n"
    result = parse_pasted_transcript(text, [_q("v3-Q1")], ASKED)
    assert result.responses[0].answer.strip() == answer.strip()


def test_parse_is_tolerant_of_heading_whitespace_and_case():
    text = "###   V3-q1  \nan answer\n"
    result = parse_pasted_transcript(text, [_q("v3-Q1")], ASKED)
    assert result.responses[0].answer.strip() == "an answer"


def test_missing_answer_yields_incomplete_not_a_silent_gap():
    text = "### v3-Q1\nonly the first answer\n"
    result = parse_pasted_transcript(text, [_q("v3-Q1"), _q("v3-Q2")], ASKED)
    assert result.complete is False
    assert "v3-Q2" in result.failure
    assert [r.question_id for r in result.responses] == ["v3-Q1"]


def test_empty_answer_body_counts_as_missing():
    text = "### v3-Q1\nreal answer\n\n### v3-Q2\n   \n"
    result = parse_pasted_transcript(text, [_q("v3-Q1"), _q("v3-Q2")], ASKED)
    assert result.complete is False
    assert "v3-Q2" in result.failure


def test_unknown_id_in_the_paste_is_reported_not_ignored():
    text = "### v3-Q1\na\n\n### v9-Q9\nstray\n"
    result = parse_pasted_transcript(text, [_q("v3-Q1")], ASKED)
    assert result.complete is False
    assert "v9-Q9" in result.failure


def test_responses_come_back_in_asked_order_not_paste_order():
    text = "### v3-Q2\nsecond\n\n### v3-Q1\nfirst\n"
    result = parse_pasted_transcript(text, [_q("v3-Q1"), _q("v3-Q2")], ASKED)
    assert [r.question_id for r in result.responses] == ["v3-Q1", "v3-Q2"]


def test_conversation_id_is_read_when_the_operator_supplies_it():
    text = "conversation: 0f7d8a7d-21b5-4c8f-a278-42b98aa6fcf8\n\n### v3-Q1\na\n"
    result = parse_pasted_transcript(text, [_q("v3-Q1")], ASKED)
    assert result.conversation_id == "0f7d8a7d-21b5-4c8f-a278-42b98aa6fcf8"


def test_backend_satisfies_the_protocol_and_never_scores():
    backend = QuickPasteBackend(
        agent="engineering_onboarding_specialist",
        snapshot_data={"agent": {"Name": "Engineering Onboarding Specialist"}},
        transcript_text="### v3-Q1\nan answer\n",
    )
    assert (backend.name, backend.transport) == ("quick", "paste")
    assert backend.snapshot()["agent"]["Name"] == "Engineering Onboarding Specialist"
    result = backend.ask([_q("v3-Q1")])
    assert result.complete and result.responses[0].answer.strip() == "an answer"

    import atlas_eval.adapters.quick_paste as mod
    assert "scoring" not in open(mod.__file__).read()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_quick_paste.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas_eval.adapters.quick_paste'`

- [ ] **Step 3: Write the implementation**

```python
# atlas_eval/adapters/quick_paste.py
"""The paste transport: the operator drives Quick, the harness parses.

This exists for two reasons. It is the documented fallback for when the UI
shifts and a run is needed before selectors are fixed, and it is the only
transport that carries no UI risk at all, which makes it the right thing to
reach for when a result matters more than automation.

Answers are delimited by `### <question-id>`, the same heading form the existing
answer-key notes use.
"""

from __future__ import annotations

import re
from datetime import datetime

from atlas_eval.adapters.base import AskResult, Response
from atlas_eval.models import Question

PROMPT_HEADER = """\
# Quick run sheet

Ask these in EXACTLY this order, in ONE conversation. Do not start a new chat
partway through, and do not interleave any other question: some questions only
mean something when they immediately follow the one before them.

Paste each answer back under a heading of the form `### <question-id>`, and
optionally record the conversation id on a line reading `conversation: <id>`.
"""

_HEADING = re.compile(r"^\s*###\s*([A-Za-z0-9._-]+)\s*$")
_CONVERSATION = re.compile(r"^\s*conversation:\s*(\S+)\s*$", re.IGNORECASE)


def render_prompt_sheet(questions: list[Question]) -> str:
    lines = [PROMPT_HEADER, ""]
    for index, question in enumerate(questions, 1):
        note = f"  _(must be asked immediately after {question.after})_" if question.after else ""
        lines += [f"## {index}. {question.id}{note}", "", question.text, "",
                  f"### {question.id}", "", "_paste the answer here_", ""]
    return "\n".join(lines)


def parse_pasted_transcript(
    text: str,
    questions: list[Question],
    asked_at: datetime,
) -> AskResult:
    """Split a pasted transcript into per-question answers.

    Returns an incomplete AskResult rather than raising, so a partial run is
    still recorded and diagnosable instead of being lost.
    """
    wanted = {q.id.lower(): q.id for q in questions}
    found: dict[str, list[str]] = {}
    unknown: list[str] = []
    conversation_id: str | None = None

    current: str | None = None
    for line in text.splitlines():
        heading = _HEADING.match(line)
        if heading:
            raw = heading.group(1)
            canonical = wanted.get(raw.lower())
            if canonical is None:
                unknown.append(raw)
                current = None
            else:
                current = canonical
                found.setdefault(canonical, [])
            continue
        if current is None:
            conversation = _CONVERSATION.match(line)
            if conversation and conversation_id is None:
                conversation_id = conversation.group(1)
            continue
        found[current].append(line)

    responses: list[Response] = []
    missing: list[str] = []
    for question in questions:  # asked order, not paste order
        body = "\n".join(found.get(question.id, [])).strip()
        if not body:
            missing.append(question.id)
            continue
        responses.append(Response(question_id=question.id, answer=body, asked_at=asked_at))

    problems: list[str] = []
    if missing:
        problems.append("no answer for: " + ", ".join(missing))
    if unknown:
        problems.append("unrecognised question id in paste: " + ", ".join(sorted(set(unknown))))

    return AskResult(
        responses=responses,
        conversation_id=conversation_id,
        complete=not problems,
        failure="; ".join(problems) or None,
    )


class QuickPasteBackend:
    """Backend whose `ask` reads an already-collected transcript."""

    name = "quick"
    transport = "paste"

    def __init__(self, agent: str, snapshot_data: dict, transcript_text: str) -> None:
        self.agent = agent
        self._snapshot = snapshot_data
        self._text = transcript_text

    def snapshot(self) -> dict:
        return self._snapshot

    def ask(self, questions: list[Question]) -> AskResult:
        return parse_pasted_transcript(self._text, questions, datetime.now())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_quick_paste.py -v`
Expected: PASS, 11 passed

- [ ] **Step 5: Commit**

```bash
git add atlas_eval/adapters/quick_paste.py tests/test_quick_paste.py
git commit -m "feat: add the Quick paste transport"
```

---

### Task 6: Quick Playwright transport

**Files:**
- Create: `atlas_eval/adapters/quick_playwright.py`
- Test: `tests/test_quick_playwright.py`

**Interfaces:**
- Consumes: `AskResult`, `Response`, `TransportError` from base; everything from `quick_dom`; `Question` from models.
- Produces:
  - `DEFAULT_PROFILE_DIR = Path(".auth/quick-profile")`
  - `ANSWER_TIMEOUT_MS = 300_000` (5 minutes per question; the captured answer was 4.8k characters)
  - `POLL_INTERVAL_MS = 1_000`
  - `wait_for_answer(page, expected_count: int, timeout_ms: int = ANSWER_TIMEOUT_MS, poll_ms: int = POLL_INTERVAL_MS, sleep=None) -> None` — raises `TransportError("TIMEOUT", …)`
  - `submit_question(page, text: str) -> None`
  - `QuickPlaywrightBackend` class: `__init__(self, agent: str, url: str, snapshot_data: dict, profile_dir: Path = DEFAULT_PROFILE_DIR, page=None)`, attributes `name = "quick"` / `transport = "playwright"`, methods `snapshot()` and `ask(questions)`

Passing `page` injects an already-open page, which is how the tests drive it without a browser session or auth.

**Design points that came from the recon spike and must not be re-litigated:**
- Completion is `completed_answer_count(page) == expected`, polled. Not `aria-busy`, not a vanishing control.
- Before each question and after each answer, check `page.url` with `is_auth_redirect`; on a hit raise `TransportError("AUTH_REQUIRED", …)`.
- Never type into a password field, never submit credentials. The operator authenticates into a persistent profile beforehand.
- The whole bank runs in one page/conversation. If `conversation_id(page)` changes mid-run, raise `TransportError("CONVERSATION_LOST", …)` — the `after` dependencies are void once the thread changes.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_quick_playwright.py
from datetime import datetime

import pytest

from atlas_eval.adapters.base import TransportError
from atlas_eval.adapters.quick_playwright import (
    QuickPlaywrightBackend, submit_question, wait_for_answer,
)
from atlas_eval.models import Question, QuestionType, Stance


def _q(qid, text="question text", after=None):
    return Question(id=qid, text=text, type=QuestionType.RETRIEVAL,
                    expected_stance=Stance.ANSWER, ground_truth="gt", after=after)


class FakeLocator:
    def __init__(self, page, selector):
        self._page, self._sel = page, selector

    @property
    def first(self):
        return self

    def count(self):
        return self._page.counts.get(self._sel, 0)

    def fill(self, text):
        self._page.filled.append((self._sel, text))

    def press(self, key):
        self._page.pressed.append((self._sel, key))
        self._page.on_submit()

    def get_attribute(self, name):
        return self._page.attrs.get((self._sel, name))

    def inner_text(self):
        return self._page.texts.get(self._sel, "")

    def all_inner_texts(self):
        return self._page.lists.get(self._sel, [])

    def nth(self, i):
        return self


class FakePage:
    """Minimal stand-in exposing the slice of the Playwright API used here."""

    def __init__(self, url="https://q/sn/account/njuimod/start/agents"):
        self.url = url
        self.counts, self.attrs, self.texts, self.lists = {}, {}, {}, {}
        self.filled, self.pressed = [], []
        self.on_submit = lambda: None

    def locator(self, selector):
        return FakeLocator(self, selector)


def test_wait_for_answer_returns_once_the_footer_count_is_reached():
    from atlas_eval.adapters import quick_dom as qd
    page = FakePage()
    page.counts[qd.SEL_AI_FOOTER] = 0
    ticks = []

    def sleep(_ms):
        ticks.append(1)
        page.counts[qd.SEL_AI_FOOTER] = len(ticks)  # one answer completes per tick

    wait_for_answer(page, expected_count=2, sleep=sleep)
    assert page.counts[qd.SEL_AI_FOOTER] == 2


def test_wait_for_answer_times_out_with_a_transport_error():
    from atlas_eval.adapters import quick_dom as qd
    page = FakePage()
    page.counts[qd.SEL_AI_FOOTER] = 0
    with pytest.raises(TransportError) as exc:
        wait_for_answer(page, expected_count=1, timeout_ms=3_000, poll_ms=1_000,
                        sleep=lambda _ms: None)
    assert exc.value.code == "TIMEOUT"
    assert "1" in exc.value.detail


def test_wait_for_answer_aborts_on_an_auth_redirect_mid_wait():
    from atlas_eval.adapters import quick_dom as qd
    page = FakePage()
    page.counts[qd.SEL_AI_FOOTER] = 0

    def sleep(_ms):
        page.url = "https://q/sn/account/njuimod/start/home?redirect_uri=x&isauthcode=true"

    with pytest.raises(TransportError) as exc:
        wait_for_answer(page, expected_count=1, sleep=sleep)
    assert exc.value.code == "AUTH_REQUIRED"


def test_submit_question_fills_the_input_and_presses_enter():
    from atlas_eval.adapters import quick_dom as qd
    page = FakePage()
    page.counts[qd.SEL_INPUT] = 1
    submit_question(page, "what does DXCBD87E do?")
    assert page.filled == [(qd.SEL_INPUT, "what does DXCBD87E do?")]
    assert page.pressed == [(qd.SEL_INPUT, "Enter")]


def test_submit_question_raises_when_the_input_is_absent():
    page = FakePage()  # no input registered
    with pytest.raises(TransportError) as exc:
        submit_question(page, "anything")
    assert exc.value.code == "SELECTOR_MISSING"


def _wired_page(n_questions):
    """A page that completes one answer per submitted question."""
    from atlas_eval.adapters import quick_dom as qd
    page = FakePage()
    page.counts[qd.SEL_INPUT] = 1
    page.counts[qd.SEL_AI_FOOTER] = 0
    page.counts[qd.SEL_THREAD] = 1
    page.attrs[(qd.SEL_THREAD, "data-conversation-id")] = "conv-1"
    page.lists[qd.SEL_AI_TURN] = []
    page.lists[qd.SEL_STATUS] = ["New message from Engineering Onboarding Specialist"]
    page.lists[qd.SEL_USER_TURN] = []

    def on_submit():
        i = page.counts[qd.SEL_AI_FOOTER] + 1
        page.counts[qd.SEL_AI_FOOTER] = i
        page.lists[qd.SEL_AI_TURN] = [f"answer {k}" for k in range(1, i + 1)]
    page.on_submit = on_submit
    return page


def test_ask_walks_the_bank_in_order_and_pairs_answers():
    page = _wired_page(2)
    backend = QuickPlaywrightBackend(agent="engineering_onboarding_specialist",
                                     url="https://q", snapshot_data={}, page=page)
    result = backend.ask([_q("v3-Q1"), _q("v3-Q2", after="v3-Q1")])
    assert result.complete is True
    assert [r.question_id for r in result.responses] == ["v3-Q1", "v3-Q2"]
    assert result.responses[0].answer == "answer 1"
    assert result.responses[1].answer == "answer 2"
    assert result.conversation_id == "conv-1"


def test_ask_marks_incomplete_on_a_transport_error_and_keeps_prior_answers():
    from atlas_eval.adapters import quick_dom as qd
    page = _wired_page(2)
    calls = {"n": 0}
    original = page.on_submit

    def flaky():
        calls["n"] += 1
        if calls["n"] == 2:
            page.url = "https://q/start/home?redirect_uri=x"
            return
        original()
    page.on_submit = flaky

    backend = QuickPlaywrightBackend(agent="a", url="https://q", snapshot_data={}, page=page)
    result = backend.ask([_q("v3-Q1"), _q("v3-Q2")])
    assert result.complete is False
    assert "AUTH_REQUIRED" in result.failure
    assert [r.question_id for r in result.responses] == ["v3-Q1"]


def test_ask_aborts_if_the_conversation_changes_midway():
    from atlas_eval.adapters import quick_dom as qd
    page = _wired_page(2)
    original = page.on_submit
    state = {"n": 0}

    def switching():
        state["n"] += 1
        original()
        if state["n"] == 1:
            page.attrs[(qd.SEL_THREAD, "data-conversation-id")] = "conv-2"
    page.on_submit = switching

    backend = QuickPlaywrightBackend(agent="a", url="https://q", snapshot_data={}, page=page)
    result = backend.ask([_q("v3-Q1"), _q("v3-Q2", after="v3-Q1")])
    assert result.complete is False
    assert "CONVERSATION_LOST" in result.failure


def test_ask_refuses_before_asking_when_already_on_an_auth_redirect():
    page = _wired_page(1)
    page.url = "https://q/sn/account/njuimod/start/home?redirect_uri=x&isauthcode=true"
    backend = QuickPlaywrightBackend(agent="a", url="https://q", snapshot_data={}, page=page)
    result = backend.ask([_q("v3-Q1")])
    assert result.complete is False
    assert "AUTH_REQUIRED" in result.failure
    assert result.responses == []
    assert page.filled == [], "must not type into a login page"


def test_backend_identity_and_no_scoring_import():
    backend = QuickPlaywrightBackend(agent="a", url="https://q", snapshot_data={"k": 1},
                                     page=FakePage())
    assert (backend.name, backend.transport) == ("quick", "playwright")
    assert backend.snapshot() == {"k": 1}
    import atlas_eval.adapters.quick_playwright as mod
    src = open(mod.__file__).read()
    assert "scoring" not in src
    # Never handle credentials.
    for banned in ("password", "fill_password", "credential"):
        assert banned not in src.lower(), banned
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_quick_playwright.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas_eval.adapters.quick_playwright'`

- [ ] **Step 3: Write the implementation**

```python
# atlas_eval/adapters/quick_playwright.py
"""The Playwright transport: drive the Quick chat UI deterministically.

Chosen over an LLM agent clicking through the UI because an agent makes unlogged
judgement calls every run (which element, whether streaming finished, whether to
retry) and those calls move scores without appearing in the record. A script
makes the same calls every time, and breaks loudly when the UI changes.

Selectors and the completion signal come from docs/recon/2026-08-27-quick-chat-dom.md,
verified against the live agent. Completion is positive: one message footer per
COMPLETED answer, so we wait for that count to reach the number asked.

Authentication is never automated. The operator signs in once into a persistent
profile; this module only detects that it has been bounced to a login page and
aborts the run.
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from atlas_eval.adapters import quick_dom as qd
from atlas_eval.adapters.base import AskResult, Response, TransportError
from atlas_eval.models import Question

DEFAULT_PROFILE_DIR = Path(".auth/quick-profile")

# The captured real answer was ~4.8k characters over several paragraphs, tables
# and code blocks. Five minutes is generous rather than tight, because a false
# timeout discards a whole run.
ANSWER_TIMEOUT_MS = 300_000
POLL_INTERVAL_MS = 1_000


def _guard_auth(page) -> None:
    if qd.is_auth_redirect(page.url):
        raise TransportError(
            "AUTH_REQUIRED",
            f"bounced to a login page ({page.url[:120]}); sign in to the persistent "
            "profile and re-run. The harness never submits credentials.",
        )


def wait_for_answer(
    page,
    expected_count: int,
    timeout_ms: int = ANSWER_TIMEOUT_MS,
    poll_ms: int = POLL_INTERVAL_MS,
    sleep=None,
) -> None:
    """Block until `expected_count` answers have finished rendering.

    The footer element renders once per completed answer, which is a positive
    signal: it cannot confuse "finished" with "never started", which is exactly
    what waiting for a stop control to vanish would do.
    """
    rest = sleep if sleep is not None else (lambda ms: time.sleep(ms / 1000))
    waited = 0
    while True:
        _guard_auth(page)
        if qd.completed_answer_count(page) >= expected_count:
            return
        if waited >= timeout_ms:
            raise TransportError(
                "TIMEOUT",
                f"only {qd.completed_answer_count(page)} of {expected_count} answers "
                f"completed within {timeout_ms // 1000}s",
            )
        rest(poll_ms)
        waited += poll_ms


def submit_question(page, text: str) -> None:
    _guard_auth(page)
    box = page.locator(qd.SEL_INPUT)
    if box.count() == 0:
        raise TransportError(
            "SELECTOR_MISSING",
            f"message input {qd.SEL_INPUT} not found; the Quick UI may have changed. "
            "Recapture fixtures with tools/recon_quick_dom.py, or use the paste transport.",
        )
    box.fill(text)
    box.press("Enter")


class QuickPlaywrightBackend:
    """Ask a whole bank in one Quick conversation."""

    name = "quick"
    transport = "playwright"

    def __init__(
        self,
        agent: str,
        url: str,
        snapshot_data: dict,
        profile_dir: Path = DEFAULT_PROFILE_DIR,
        page=None,
    ) -> None:
        self.agent = agent
        self.url = url
        self.profile_dir = profile_dir
        self._snapshot = snapshot_data
        self._page = page  # injected in tests; a live page in real runs

    def snapshot(self) -> dict:
        return self._snapshot

    def ask(self, questions: list[Question]) -> AskResult:
        page = self._page
        if page is None:
            raise TransportError(
                "SELECTOR_MISSING",
                "no page supplied; open a persistent context and pass page=",
            )

        responses: list[Response] = []
        conversation = qd.conversation_id(page)

        try:
            _guard_auth(page)
            for index, question in enumerate(questions, 1):
                submit_question(page, question.text)
                wait_for_answer(page, expected_count=index)

                current = qd.conversation_id(page)
                if conversation is None:
                    conversation = current
                elif current != conversation:
                    raise TransportError(
                        "CONVERSATION_LOST",
                        f"conversation changed from {conversation} to {current} before "
                        f"{question.id}; `after` dependencies are void once the thread "
                        "changes, so the run cannot continue",
                    )

                answers = qd.answer_texts(page)
                if len(answers) < index:
                    raise TransportError(
                        "PARSE_FAILED",
                        f"{index} answers completed but only {len(answers)} agent turns "
                        f"are readable for {question.id}",
                    )
                responses.append(Response(
                    question_id=question.id,
                    answer=answers[index - 1],
                    asked_at=datetime.now(),
                    citations=qd.citation_labels(page),
                ))
        except TransportError as err:
            return AskResult(
                responses=responses, conversation_id=conversation,
                complete=False, failure=str(err),
            )

        return AskResult(responses=responses, conversation_id=conversation, complete=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_quick_playwright.py -v`
Expected: PASS, 11 passed

- [ ] **Step 5: Commit**

```bash
git add atlas_eval/adapters/quick_playwright.py tests/test_quick_playwright.py
git commit -m "feat: add the Quick Playwright transport"
```

---

### Task 7: Orchestration

**Files:**
- Create: `atlas_eval/orchestrate.py`
- Test: `tests/test_orchestrate.py`

**Interfaces:**
- Consumes: `Backend`, `AskResult`, `Response` from base; `load_bank`, `compute_question_sha256`, `resolve_run_order` from dataset; `score_answer` from scoring; `Rubric` from scoring; `RunMeta`, `RunStatus`, `ScoreRow`, `make_run_id`, `write_run` from runs; `render_transcript` from transcript.
- Produces:
  - `OrchestrationError(Exception)`
  - `run_bank(bank_path: Path, backend, runs_dir: Path, scored_by: str = "harness-deterministic", harness_git_sha: str | None = None, now: datetime | None = None) -> Path`

**The invariants this function enforces, in this order:**
1. Refuse a frozen bank whose `question_sha256` no longer matches — before asking anything.
2. Ask in `resolve_run_order` order.
3. Score deterministically only. It never writes a rubric value; `Rubric` carries `scored_by` and the five dimensions stay `None` for a human.
4. Write the run whether or not it completed, with `status` reflecting reality.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_orchestrate.py
from datetime import datetime
from pathlib import Path

import pytest

from atlas_eval.adapters.base import AskResult, Response
from atlas_eval.dataset import compute_question_sha256, load_bank
from atlas_eval.orchestrate import OrchestrationError, run_bank
from atlas_eval.runs import read_run

BANK = """version: v3
agent: engineering_onboarding_specialist
corpus: quick_space_ca7_daily_s3
questions:
  - id: v3-Q1
    text: Describe the Accelerated Collection Process.
    type: retrieval
    expected_stance: answer
    ground_truth: ACP is the Accelerated Collection Process.
    checks:
      required_all: [ACP]
      forbidden: [ETA-227]
      expect_citations: [UIMB0730]
  - id: v3-Q2
    after: v3-Q1
    text: What does ACP stand for?
    type: acronym_check
    expected_stance: answer
    ground_truth: Accelerated Collection Process.
    checks:
      required_any: ["Accelerated Collection Process"]
"""


def _bank_file(tmp_path, frozen=False):
    path = tmp_path / "v3.yaml"
    path.write_text(BANK)
    if frozen:
        bank = load_bank(path)
        path.write_text(
            BANK.replace("version: v3",
                         f"version: v3\nfrozen_on: 2026-08-03\n"
                         f"question_sha256: {compute_question_sha256(bank)}")
        )
    return path


class StubBackend:
    name, transport = "quick", "stub"

    def __init__(self, answers, complete=True, failure=None, conversation="conv-1"):
        self._answers, self._complete = answers, complete
        self._failure, self._conversation = failure, conversation
        self.asked: list[str] = []

    def snapshot(self):
        return {"model_chip": "Advanced"}

    def ask(self, questions):
        self.asked = [q.id for q in questions]
        return AskResult(
            responses=[Response(question_id=q.id, answer=self._answers[q.id],
                                asked_at=datetime(2026, 8, 27, 9, 0))
                       for q in questions if q.id in self._answers],
            conversation_id=self._conversation,
            complete=self._complete, failure=self._failure,
        )


GOOD = {"v3-Q1": "The ACP is documented in UIMB0730.",
        "v3-Q2": "It stands for Accelerated Collection Process."}


def test_happy_path_writes_a_complete_run(tmp_path):
    backend = StubBackend(GOOD)
    run_dir = run_bank(_bank_file(tmp_path), backend, tmp_path / "runs",
                       now=datetime(2026, 8, 27, 9, 30))
    meta, responses, rows = read_run(run_dir)
    assert meta.status.value == "complete"
    assert meta.bank_version == "v3"
    assert meta.transport == "stub"
    assert meta.conversation_id == "conv-1"
    assert list(responses) == ["v3-Q1", "v3-Q2"]
    assert len(rows) == 2
    for name in ("run.yaml", "responses.yaml", "transcript.md", "snapshot.json", "scores.csv"):
        assert (run_dir / name).exists(), name


def test_questions_are_asked_in_resolved_run_order(tmp_path):
    backend = StubBackend(GOOD)
    run_bank(_bank_file(tmp_path), backend, tmp_path / "runs",
             now=datetime(2026, 8, 27, 9, 30))
    assert backend.asked == ["v3-Q1", "v3-Q2"]


def test_deterministic_scores_are_computed_and_recorded(tmp_path):
    run_dir = run_bank(_bank_file(tmp_path), StubBackend(GOOD), tmp_path / "runs",
                       now=datetime(2026, 8, 27, 9, 30))
    text = (run_dir / "scores.csv").read_text()
    assert "deterministic_pass" in text
    assert "True" in text


def test_a_wrong_answer_records_a_failing_deterministic_result(tmp_path):
    bad = dict(GOOD, **{"v3-Q1": "This is the ETA-227 reporting process."})
    run_dir = run_bank(_bank_file(tmp_path), StubBackend(bad), tmp_path / "runs",
                       now=datetime(2026, 8, 27, 9, 30))
    import csv
    rows = {r["question_id"]: r for r in csv.DictReader((run_dir / "scores.csv").open())}
    assert rows["v3-Q1"]["deterministic_pass"] == "False"
    assert "ETA-227" in rows["v3-Q1"]["present_forbidden"]


def test_rubric_cells_are_left_empty_for_a_human(tmp_path):
    run_dir = run_bank(_bank_file(tmp_path), StubBackend(GOOD), tmp_path / "runs",
                       now=datetime(2026, 8, 27, 9, 30))
    import csv
    for row in csv.DictReader((run_dir / "scores.csv").open()):
        for dim in ("citations", "correctness", "gap_honesty", "scope_discipline", "clarity"):
            assert row[dim] == "", f"{dim} must be blank, not zero"
        assert row["total"] == ""
        assert row["confirmed_by"] == ""
        assert row["scored_by"] == "harness-deterministic"


def test_incomplete_ask_still_writes_a_run_marked_incomplete(tmp_path):
    partial = {"v3-Q1": GOOD["v3-Q1"]}
    run_dir = run_bank(_bank_file(tmp_path),
                       StubBackend(partial, complete=False,
                                   failure="TIMEOUT: only 1 of 2 answers completed"),
                       tmp_path / "runs", now=datetime(2026, 8, 27, 9, 30))
    meta, responses, rows = read_run(run_dir)
    assert meta.status.value == "incomplete"
    assert list(responses) == ["v3-Q1"]
    assert len(rows) == 1
    assert "TIMEOUT" in (run_dir / "transcript.md").read_text()


def test_frozen_bank_with_edited_text_is_refused_before_asking(tmp_path):
    path = _bank_file(tmp_path, frozen=True)
    path.write_text(path.read_text().replace("What does ACP stand for?",
                                             "What does ACP mean?"))
    backend = StubBackend(GOOD)
    with pytest.raises(OrchestrationError) as exc:
        run_bank(path, backend, tmp_path / "runs", now=datetime(2026, 8, 27, 9, 30))
    assert "question_sha256" in str(exc.value)
    assert backend.asked == [], "must not ask anything against a mismatched bank"


def test_frozen_bank_with_matching_hash_runs(tmp_path):
    run_dir = run_bank(_bank_file(tmp_path, frozen=True), StubBackend(GOOD),
                       tmp_path / "runs", now=datetime(2026, 8, 27, 9, 30))
    assert read_run(run_dir)[0].status.value == "complete"


def test_unfrozen_bank_records_the_computed_hash(tmp_path):
    path = _bank_file(tmp_path)
    run_dir = run_bank(path, StubBackend(GOOD), tmp_path / "runs",
                       now=datetime(2026, 8, 27, 9, 30))
    assert read_run(run_dir)[0].question_sha256 == compute_question_sha256(load_bank(path))


def test_orchestrator_never_writes_a_rubric_value(tmp_path):
    import atlas_eval.orchestrate as mod
    src = open(mod.__file__).read()
    for dim in ("citations=", "correctness=", "gap_honesty=", "scope_discipline=", "clarity="):
        assert dim not in src, f"orchestrator must not set {dim}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_orchestrate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas_eval.orchestrate'`

- [ ] **Step 3: Write the implementation**

```python
# atlas_eval/orchestrate.py
"""Wire a backend to the scorer and the run record.

This is the layer that makes backends comparable: whichever transport ran, the
questions are asked in the same resolved order, scored by the same deterministic
rules, and written to the same five-file record.

It never writes a rubric value. Rubric scoring is the audit process's job (an
LLM drafts, a human confirms), and those columns stay blank here so a zero is
never confused with "nobody has scored this".
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from atlas_eval.dataset import compute_question_sha256, load_bank, resolve_run_order
from atlas_eval.runs import RunMeta, RunStatus, ScoreRow, make_run_id, write_run
from atlas_eval.scoring import Rubric, score_answer
from atlas_eval.transcript import render_transcript


class OrchestrationError(Exception):
    """The run could not be started."""


def _git_sha() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             text=True, check=False)
        return out.stdout.strip() or None if out.returncode == 0 else None
    except OSError:
        return None


def run_bank(
    bank_path: Path,
    backend,
    runs_dir: Path,
    scored_by: str = "harness-deterministic",
    harness_git_sha: str | None = None,
    now: datetime | None = None,
) -> Path:
    bank = load_bank(bank_path)

    # Refuse before asking anything: a frozen bank whose questions changed would
    # produce scores that silently refer to questions that no longer exist.
    actual = compute_question_sha256(bank)
    if bank.frozen_on is not None:
        if not bank.question_sha256:
            raise OrchestrationError(
                f"{bank_path} is frozen ({bank.frozen_on}) but has no question_sha256"
            )
        if bank.question_sha256 != actual:
            raise OrchestrationError(
                f"{bank_path}: question_sha256 mismatch (recorded "
                f"{bank.question_sha256[:12]}, actual {actual[:12]}). A frozen "
                "question's id or text changed; bump the bank version instead of "
                "running against it."
            )

    questions = resolve_run_order(bank)
    started = now or datetime.now()

    result = backend.ask(questions)
    snapshot = backend.snapshot()
    finished = now or datetime.now()

    by_id = {r.question_id: r for r in result.responses}
    rows: list[ScoreRow] = []
    for question in questions:
        response = by_id.get(question.id)
        if response is None:
            continue
        rows.append(ScoreRow(
            question_id=question.id,
            type=question.type.value,
            verification_status=question.verification.status.value,
            rubric=Rubric(scored_by=scored_by),
            deterministic=score_answer(question, response.answer,
                                       response.observed_stance),
        ))

    status = RunStatus.COMPLETE if result.complete else RunStatus.INCOMPLETE
    meta = RunMeta(
        run_id=make_run_id(finished, backend.name, bank.version),
        backend=backend.name,
        transport=backend.transport,
        bank_version=bank.version,
        question_sha256=bank.question_sha256 or actual,
        agent=bank.agent,
        agent_id=(snapshot.get("agent") or {}).get("AgentId"),
        conversation_id=result.conversation_id,
        started_at=started,
        finished_at=finished if result.complete else None,
        harness_git_sha=harness_git_sha or _git_sha(),
        status=status,
    )

    transcript = render_transcript(meta, questions, result.responses, snapshot)
    if result.failure:
        transcript += f"\n---\n\n**Run failure:** {result.failure}\n"

    return write_run(
        runs_dir, meta,
        {r.question_id: r.answer for r in result.responses},
        transcript, snapshot, rows,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_orchestrate.py -v`
Expected: PASS, 10 passed

- [ ] **Step 5: Commit**

```bash
git add atlas_eval/orchestrate.py tests/test_orchestrate.py
git commit -m "feat: orchestrate snapshot, ask, score and write into one run record"
```

---

### Task 8: The `atlas-eval run` command

**Files:**
- Modify: `atlas_eval/cli.py`
- Create: `tools/open_quick_session.py`
- Modify: `README.md`
- Test: `tests/test_cli_run.py`

**Interfaces:**
- Consumes: `run_bank` from orchestrate; `QuickPasteBackend` from quick_paste; `QuickPlaywrightBackend`, `DEFAULT_PROFILE_DIR` from quick_playwright; `capture` from snapshot.
- Produces: `_cmd_run(args) -> int` in `cli.py`, registered as the `run` subcommand.

Flags: `--bank` (path, required), `--transport` (`paste`|`playwright`, default `paste`), `--runs` (default `data/runs`), `--transcript` (path, required for `paste`), `--url`, `--profile-dir`, `--account-id`, `--agent-id`, `--agent-name`, `--no-snapshot`.

`tools/open_quick_session.py` opens a headed persistent context at the profile dir so the operator can authenticate once, then exits leaving the profile populated. That keeps authentication a separate, explicit human step rather than something a run does.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_run.py
from pathlib import Path

import pytest

from atlas_eval.cli import main
from atlas_eval.runs import read_run

BANK = """version: v3
agent: engineering_onboarding_specialist
corpus: quick_space_ca7_daily_s3
questions:
  - id: v3-Q1
    text: Describe the ACP.
    type: retrieval
    expected_stance: answer
    ground_truth: ACP is the Accelerated Collection Process.
    checks:
      required_all: [ACP]
"""


def _bank(tmp_path):
    p = tmp_path / "v3.yaml"
    p.write_text(BANK)
    return p


def test_paste_transport_end_to_end(tmp_path, capsys):
    bank = _bank(tmp_path)
    transcript = tmp_path / "pasted.md"
    transcript.write_text("### v3-Q1\nThe ACP is the Accelerated Collection Process.\n")
    runs = tmp_path / "runs"

    code = main(["run", "--bank", str(bank), "--transport", "paste",
                 "--transcript", str(transcript), "--runs", str(runs), "--no-snapshot"])
    assert code == 0
    out = capsys.readouterr().out
    assert "complete" in out

    run_dir = next(runs.iterdir())
    meta, responses, rows = read_run(run_dir)
    assert meta.transport == "paste"
    assert responses["v3-Q1"].startswith("The ACP")
    assert len(rows) == 1


def test_paste_transport_requires_a_transcript(tmp_path, capsys):
    code = main(["run", "--bank", str(_bank(tmp_path)), "--transport", "paste",
                 "--runs", str(tmp_path / "runs"), "--no-snapshot"])
    assert code == 2
    assert "--transcript" in capsys.readouterr().out


def test_incomplete_paste_exits_nonzero_but_still_writes_the_run(tmp_path, capsys):
    bank = tmp_path / "v3.yaml"
    bank.write_text(BANK + """  - id: v3-Q2
    text: And what does ACP stand for?
    type: acronym_check
    expected_stance: answer
    ground_truth: Accelerated Collection Process.
""")
    transcript = tmp_path / "pasted.md"
    transcript.write_text("### v3-Q1\nThe ACP.\n")
    runs = tmp_path / "runs"

    code = main(["run", "--bank", str(bank), "--transport", "paste",
                 "--transcript", str(transcript), "--runs", str(runs), "--no-snapshot"])
    assert code == 1, "an incomplete run must not report success"
    assert "incomplete" in capsys.readouterr().out.lower()
    assert read_run(next(runs.iterdir()))[0].status.value == "incomplete"


def test_print_sheet_emits_the_run_sheet_and_exits_zero(tmp_path, capsys):
    code = main(["run", "--bank", str(_bank(tmp_path)), "--transport", "paste",
                 "--print-sheet", "--runs", str(tmp_path / "runs"), "--no-snapshot"])
    assert code == 0
    out = capsys.readouterr().out
    assert "### v3-Q1" in out
    assert "Describe the ACP." in out
    assert "same conversation" in out.lower()


def test_playwright_transport_requires_a_url(tmp_path, capsys):
    code = main(["run", "--bank", str(_bank(tmp_path)), "--transport", "playwright",
                 "--runs", str(tmp_path / "runs"), "--no-snapshot"])
    assert code == 2
    assert "--url" in capsys.readouterr().out


def test_missing_bank_exits_two(tmp_path, capsys):
    code = main(["run", "--bank", str(tmp_path / "nope.yaml"), "--transport", "paste",
                 "--transcript", str(tmp_path / "t.md"), "--runs", str(tmp_path / "runs"),
                 "--no-snapshot"])
    assert code == 2


def test_run_help_lists_both_transports(capsys):
    with pytest.raises(SystemExit):
        main(["run", "--help"])
    out = capsys.readouterr().out
    assert "paste" in out and "playwright" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_cli_run.py -v`
Expected: FAIL — `argparse` error, `invalid choice: 'run'`

- [ ] **Step 3: Add `_cmd_run` to `atlas_eval/cli.py`**

```python
def _cmd_run(args: argparse.Namespace) -> int:
    from atlas_eval.adapters.quick_paste import QuickPasteBackend
    from atlas_eval.orchestrate import OrchestrationError, run_bank

    bank_path = Path(args.bank)
    if not bank_path.is_file():
        print(f"error: no such bank file: {bank_path}")
        return 2

    snapshot_data: dict = {}
    if not args.no_snapshot:
        from atlas_eval.snapshot import SnapshotError, capture
        if not args.account_id:
            print("error: --account-id is required unless --no-snapshot is given")
            return 2
        try:
            snapshot_data = capture(args.account_id, agent_id=args.agent_id,
                                    agent_name=args.agent_name)
        except SnapshotError as err:
            print(f"error: snapshot failed: {err}")
            return 2

    if args.transport == "paste":
        if args.print_sheet:
            from atlas_eval.adapters.quick_paste import render_prompt_sheet
            from atlas_eval.dataset import load_bank, resolve_run_order
            print(render_prompt_sheet(resolve_run_order(load_bank(bank_path))))
            return 0
        if not args.transcript:
            print("error: --transcript is required for the paste transport "
                  "(or pass --print-sheet to generate the sheet to fill in)")
            return 2
        transcript_path = Path(args.transcript)
        if not transcript_path.is_file():
            print(f"error: no such transcript: {transcript_path}")
            return 2
        backend = QuickPasteBackend(agent=args.agent_name or "",
                                    snapshot_data=snapshot_data,
                                    transcript_text=transcript_path.read_text())
    else:
        if not args.url:
            print("error: --url is required for the playwright transport")
            return 2
        from playwright.sync_api import sync_playwright

        from atlas_eval.adapters.quick_playwright import QuickPlaywrightBackend
        profile = Path(args.profile_dir)
        if not profile.exists():
            print(f"error: no browser profile at {profile}. Run "
                  f"tools/open_quick_session.py first and sign in once.")
            return 2
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(str(profile), headless=False)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(args.url)
            backend = QuickPlaywrightBackend(
                agent=args.agent_name or "", url=args.url,
                snapshot_data=snapshot_data, profile_dir=profile, page=page,
            )
            try:
                run_dir = run_bank(bank_path, backend, Path(args.runs))
            except OrchestrationError as err:
                print(f"error: {err}")
                return 2
            finally:
                ctx.close()
            return _report_run(run_dir)

    try:
        run_dir = run_bank(bank_path, backend, Path(args.runs))
    except OrchestrationError as err:
        print(f"error: {err}")
        return 2
    return _report_run(run_dir)


def _report_run(run_dir: Path) -> int:
    from atlas_eval.runs import read_run

    meta, responses, rows = read_run(run_dir)
    passed = sum(1 for line in (run_dir / "scores.csv").read_text().splitlines()[1:]
                 if ",True," in line)
    print(f"{meta.run_id}: {meta.status.value}")
    print(f"  answers: {len(responses)}   scored rows: {len(rows)}   "
          f"deterministic passes: {passed}")
    print(f"  written to {run_dir}")
    if meta.status.value != "complete":
        print("  this run is incomplete and is excluded from bank-level results")
        return 1
    return 0
```

Register inside `main`, alongside the other subcommands:

```python
    p_run = sub.add_parser("run", help="execute a bank against a backend")
    p_run.add_argument("--bank", required=True)
    p_run.add_argument("--transport", choices=("paste", "playwright"), default="paste",
                       help="paste: you drive Quick and paste the transcript. "
                            "playwright: drive the UI (needs a signed-in profile).")
    p_run.add_argument("--runs", default="data/runs")
    p_run.add_argument("--transcript", help="pasted transcript (paste transport)")
    p_run.add_argument("--print-sheet", action="store_true",
                       help="print the run sheet to fill in, then exit (paste transport)")
    p_run.add_argument("--url", help="Quick chat URL (playwright transport)")
    p_run.add_argument("--profile-dir", default=".auth/quick-profile")
    p_run.add_argument("--account-id", help="AWS account id, for the config snapshot")
    p_run.add_argument("--agent-id")
    p_run.add_argument("--agent-name")
    p_run.add_argument("--no-snapshot", action="store_true",
                       help="skip the control-plane snapshot (offline testing)")
    p_run.set_defaults(func=_cmd_run)
```

- [ ] **Step 4: Write the sign-in helper**

```python
# tools/open_quick_session.py
"""Open a headed browser against the persistent profile so you can sign in once.

Authentication is a deliberate human step, kept out of the run path: the harness
never submits credentials. Sign in here, close the window, and later runs reuse
the profile until the session expires.

    .venv/bin/python tools/open_quick_session.py \\
      --url "https://us-east-1.quicksight.aws.amazon.com/sn/account/njuimod/start/agents"
"""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--profile-dir", default=".auth/quick-profile")
    args = ap.parse_args()

    profile = Path(args.profile_dir)
    profile.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(profile), headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(args.url)
        print(f"Profile: {profile}")
        print("Sign in, open the agent, then press Enter here to save and close.")
        input("> ")
        print(f"  final URL: {page.url}")
        ctx.close()
    print("Session stored. Runs can now use --transport playwright.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_cli_run.py -v && .venv/bin/python -m pytest -q`
Expected: PASS, 7 passed in the file; whole suite green

- [ ] **Step 6: Add a Running section to `README.md`**

```markdown
## Running a bank

Two transports. Both produce an identical run record.

**Paste** — you drive Quick, the harness parses. No UI risk; use it when the
result matters more than the automation:

    atlas-eval run --bank data/banks/v3.yaml --transport paste \
      --transcript my_pasted_answers.md --account-id <id> --agent-name "Engineering Onboarding Specialist"

Answers go under `### <question-id>` headings. Generate the sheet to fill in with:

    atlas-eval run --bank data/banks/v3.yaml --transport paste --print-sheet

**Playwright** — drives the UI. Sign in once, then reuse the profile:

    .venv/bin/python tools/open_quick_session.py --url "<quick url>"
    atlas-eval run --bank data/banks/v3.yaml --transport playwright \
      --url "<quick url>" --account-id <id>

The harness never submits credentials. If a run is bounced to a login page it
aborts and marks the run `incomplete`.

An incomplete run is still written to `data/runs/` for diagnosis, exits non-zero,
and is excluded from `atlas-eval report`.
```

- [ ] **Step 7: Commit**

```bash
git add atlas_eval/cli.py tools/open_quick_session.py tests/test_cli_run.py README.md
git commit -m "feat: add atlas-eval run for both Quick transports"
```
