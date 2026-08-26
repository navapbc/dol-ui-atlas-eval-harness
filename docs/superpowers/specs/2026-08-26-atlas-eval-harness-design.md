# Atlas Eval Harness — dataset layer and Quick runner

Date: 2026-08-26
Status: approved design, not yet implemented
Author: Michael Angeli
Origin: Michael/Billy sync, 2026-08-26 (Eval Harness Architecture)

## Purpose

A repeatable auditing harness for the NJDOL Atlas chat agents. It evaluates the AWS
Quick agent today, and is built so a local "second brain" LLM and a future AWS Bedrock
agent can be evaluated against the same frozen question banks with the same scoring,
producing directly comparable numbers.

This spec covers two of the harness's subsystems: the **question/answer dataset layer**
and the **Quick runner**. Scoring is specified because the dataset schema depends on it.
The Bedrock and local-LLM adapters, cross-model comparison reporting, and cost/latency
gates are deliberately out of scope and get their own specs.

## Constraints

These are not preferences; they are fixed facts the design has to absorb.

1. **Quick has no invoke API.** `aws quicksight` exposes agent and space control-plane
   operations only (`create-agent`, `describe-agent`, `list-spaces`, `update-space-resources`,
   and so on). There is no `converse`, `invoke`, or `chat` operation. A Quick run must be
   driven through the web UI. Bedrock and a local model are directly callable, so the
   Quick arm is permanently asymmetric with the others in transport, and must not be
   asymmetric in anything else.

2. **Ground truth must be human-verified.** The 2026-08-26 sync's "can't use AI to
   confirm AI" applies to the *question and answer sets*: they were produced with AI
   assistance and have not had SME review. An AI-written answer key cannot be validated
   by AI. Grading is a separate matter: the existing Quick Chat Audit process, where an
   LLM drafts rubric scores against the answer key and a human confirms them, continues
   as-is. Every rubric score therefore records who or what produced it and whether a
   human confirmed it, so a report can be restricted to human-confirmed scores whenever
   that is what defensibility requires.

3. **Ground truth is not yet vetted.** The current banks were built by Michael, partly
   sourced from Oscar, and never verified. Some questions have no known correct answer
   because Oscar asked things he did not know the answer to. The dataset must therefore
   represent verification state per question and must be able to report a score over only
   the verified subset.

4. **Comparability over time is the product.** The harness exists to detect regression
   and to compare backends. Anything that introduces run-to-run variance in the transport
   or the scorer destroys the thing being measured.

## Scope

In scope:

- Repo skeleton and module boundaries.
- Frozen question bank format, merging the current question tables and answer keys.
- Deterministic scoring, plus carrying the existing five-dimension human rubric.
- Backend adapter interface, with the Quick adapter implemented (Playwright transport,
  paste transport as fallback).
- Run record format, uniform across backends.
- Spreadsheet export/import for SME verification.
- Migration of the existing audit history into the repo.
- Offline validation and unit tests.

Out of scope:

- Bedrock adapter, local-LLM adapter.
- Cross-model comparison report, cost and latency gates.
- Any change to the knowledge base, spaces, or agent configuration. The harness reads
  agent config; it never writes it.
- The Loops knowledge base corpus itself, which is Billy's separate repo.

## Repo structure

```
dol-ui-atlas-eval-harness/
  README.md
  pyproject.toml
  atlas_eval/
    __init__.py
    dataset.py          # load + validate banks, freeze hashing, run-order resolution
    adapters/
      base.py           # Backend protocol
      quick.py          # Playwright transport + paste transport
    scoring.py          # deterministic checks only; imports no adapter, calls no model
    review.py           # xlsx export / verdict import
    runner.py           # snapshot -> run -> score -> write run record
    cli.py
  data/
    banks/              # v1.yaml .. v6.yaml, frozen question sets
    runs/               # one directory per run
    scores.csv          # GENERATED rollup of all runs
  reference/            # migrated non-dataset audit material
  docs/
    superpowers/specs/
  tests/
    fixtures/
```

Three hard module boundaries, each independently testable:

- `dataset.py` knows nothing about backends or transports.
- `adapters/*` know nothing about scoring. An adapter returns raw responses.
- `scoring.py` never calls a model and never touches the network.

Adding the Bedrock or local-LLM arm later means adding one file under `adapters/` and
registering it. No other module changes. That is the concrete meaning of model-agnostic
here.

Language is Python, matching the existing `nava-finchy-nj/tools/finchy-eval` harness so
the two are maintainable by the same people.

## Dataset format

One frozen YAML file per bank version at `data/banks/vN.yaml`. Each file merges what are
currently two separate artifacts: the question table in `question_bank.md` and the
corresponding `vN_answer_key.md`. They are merged because a question and its ground truth
drifting apart is the most likely silent failure in the current layout, and because the
ground-truth prose has outgrown a Markdown table cell (several exceed 900 characters).
YAML block scalars hold that prose natively and diff line by line during review.

```yaml
version: v3
frozen_on: 2026-08-03
question_sha256: 4c1f...          # over normalized (id, text) pairs only
agent: engineering_onboarding_specialist
corpus: quick_space_ca7_daily_s3
sourcing: |
  Q1/Q2 are the settled ACP pair. Q3-Q8 pooled from four Product Briefs
  (Employer Charges Phase 2, SSN Validation & Deceased Check, IVR Migration to
  Amazon Connect, MUNC Table in Postgres). In-KB anchors and absences verified
  against quick_space_ca7_daily_s3/s3/ on 2026-08-03.

questions:
  - id: v3-Q1
    text: Describe the Automated Collection Process.
    type: term_redirect
    type_note: term-redirect              # original free-text label, preserved verbatim
    provenance: product-brief/employer-charges-phase-2
    expected_stance: redirect             # answer | hedge | refuse | redirect
    ground_truth: |
      "Automated Collection Process" appears nowhere in the KB. Full credit maps it to
      the Accelerated Collection Process (ACP) and describes the DOR payment flow with
      citations. Describing ETA-227 reporting as the process is wrong.
    partial_credit: |
      A clarifying question that offers ACP as the candidate earns partial credit.
    checks:
      required_all:     [ACP]
      required_any:     ["Accelerated Collection Process"]
      forbidden:        [ETA-227]
      expect_citations: [UIMB0730, UIMB0731, L2ACPD]
    verification:
      status: unverified                  # unverified | verified | rejected | needs-sme
      verified_by: null
      verified_on: null
      notes: null

  - id: v3-Q2
    after: v3-Q1                          # run-order dependency; priming is deliberate
    text: What does the acronym ACP stand for?
    ...
```

### Field semantics

- `question_sha256` covers **only** ids and question text. Ground truth and checks stay
  editable after freezing, which matches actual practice (the v3 key was corrected in
  place after the run, and v1's was backfilled from graded runs). The runner refuses to
  score a bank whose *questions* changed without a version bump. This is what makes the
  v6 rule "do not run until frozen and hashed" enforceable rather than aspirational.

- `after` encodes run-order dependency. Several questions only work in sequence: v3-Q2
  tests whether the agent echoes the invalid name v3-Q1 planted, v3-Q5 is primed by
  v3-Q4's answer, v3-Q7 by v3-Q6's. This is currently prose a human must remember to
  honor. As data, the runner enforces it and an automated run cannot shuffle away the
  entire point of the question. Validation checks the dependency graph is acyclic and
  that every `after` target exists.

- `type` is a controlled enum so scores aggregate by question type, which is the main
  analysis axis. The current field is free text and has drifted to 30 distinct strings
  across six banks. Enum: `retrieval`, `rule_logic`, `data_flow`, `gap_probe`,
  `hallucination_bait`, `absence_probe`, `term_redirect`, `acronym_check`,
  `scope_boundary`, `out_of_kb`, `cross_space`, `generation_probe`, `handoff_probe`.
  `type_note` preserves the original string verbatim so migration loses nothing and the
  mapping stays auditable.

- `expected_stance` is the coarse behavioral expectation, distinct from content
  correctness. A gap probe answered with confident invented detail fails on stance even
  if it happens to name a real program.

- `verification.status` is per question, not per bank. A bank is normally partly
  verified: Oscar-verified questions are added incrementally, and kick-screens questions
  wait on Morgan's Transform work. `rejected` is first-class and retains the question and
  the reason rather than deleting it, so a question with no knowable answer is not
  re-litigated next round. This block is where the "can't use AI to confirm AI" constraint
  actually lives: the ground truth was AI-assisted, so `verified` means a human SME signed
  off on it. An SME session is scheduled for Friday 2026-08-28 to begin working through
  the backlog.

### Reporting on a partly verified bank

The scorer emits two figures and never merges them:

- **Verified score** — over `status: verified` questions only. This is the defensible
  number, the one that goes to Billy or into a ticket.
- **Exploratory score** — over the full bank, labeled as unvetted.

## Scoring

Two independent layers, written to the same per-run `scores.csv`.

**Deterministic layer**, computed with zero LLM involvement:

- `stance_pass` — observed stance matches `expected_stance`.
- `required_all_pass` — every term in `required_all` is present.
- `required_any_pass` — at least one term in `required_any` is present, if any given.
- `forbidden_pass` — no `forbidden` term is present.
- `citation_recall` — fraction of `expect_citations` appearing in the answer.
- `deterministic_pass` — conjunction of the above.

Matching is case-insensitive and whitespace-normalized. It is plain substring and literal
matching, not semantic similarity, because a scorer whose behavior can shift is a scorer
that silently rewrites history.

**Rubric layer**, carried over unchanged from the existing `scores.csv`: `citations`,
`correctness`, `gap_honesty`, `scope_discipline`, `clarity`, each 0-2, `total` out of 10,
plus a free-text `notes`.

The rubric is filled by the current audit process: an LLM drafts the scores against the
answer key and a human reviews them. Two provenance fields make that auditable rather
than implicit:

- `scored_by` — who or what produced the values (a model id such as `claude-opus-5`, or a
  person's name for a hand-scored row).
- `confirmed_by` — the person who reviewed them, or null if nobody has yet.

Reports can then be filtered to `confirmed_by` being set. This keeps the honest
distinction the sync was reaching for, without discarding a working process: an
unconfirmed LLM-drafted score is a useful signal and a legitimate intermediate state, it
just is not the same artifact as a human-confirmed one.

Keeping both layers matters: the deterministic layer gives cross-model comparability and
catches regression mechanically, while the rubric captures the judgment the deterministic
checks cannot, which for this corpus is mostly scope discipline and honesty about gaps.
Moving toward more deterministic coverage over time is the direction, not a precondition.

## Backend adapter interface

```python
class Backend(Protocol):
    name: str
    transport: str

    def snapshot(self) -> dict: ...
    def ask(self, questions: list[Question]) -> list[Response]: ...
```

`snapshot()` captures whatever makes a later score interpretable: for Quick, the agent
description and the linked spaces with their resources, via the read-only control-plane
calls already in use. `ask()` submits questions in resolved run order within a single
conversation and returns raw answer text per question id. An adapter never scores.

### Quick adapter

Two transports behind one adapter, both producing an identical run record.

**`playwright` (default).** Drives the Quick web UI deterministically. Chosen over the
previous approach of an LLM agent pasting and scraping in the Claude Desktop browser,
because an agent makes unlogged judgment calls every run (which element to click, whether
streaming finished, whether to retry, whether to nudge a stalled response) and those calls
move scores without appearing anywhere in the record. A script makes the same calls every
time. The failure modes also differ in the direction that matters: a script breaks loudly
on a changed selector, whereas an agent recovers by finding another path and silently
changes the procedure mid-suite. Agent-driven browsing remains appropriate for
exploratory probing; it is not appropriate for scored regression runs.

**`paste` (fallback).** Emits the frozen question list in resolved run order, then ingests
a pasted transcript and parses it into per-question responses. This is the documented
path for when the UI shifts and a run is needed before selectors are fixed.

Authentication is never automated. Quick sits behind IAM Identity Center SSO, so the
operator logs in once in a headed browser and the session state is persisted and reused.
The harness never enters credentials.

## Run record

One directory per run, `data/runs/<timestamp>_<backend>_<bank>/`, identical in shape
across every backend. That uniformity is what makes cross-model comparison possible later.

```
run.yaml         # backend, transport, bank version + question_sha256, agent_id,
                 # conversation_id, started_at, finished_at, harness git sha, status
responses.yaml   # question_id -> raw answer text, in the order actually asked
transcript.md    # human-readable, same format as the existing chats/ files
snapshot.json    # agent + spaces config captured at run time
scores.csv       # deterministic results + rubric columns for this run
```

`status` is `complete` or `incomplete`. A run that lost auth or timed out partway is
`incomplete`, is retained, and is refused as a bank result by the scorer. Fail closed,
matching finchy-eval's behavior on execution errors. A partial run still has diagnostic
value; it just cannot be compared.

`data/scores.csv` is a **generated** rollup of every run's scores, preserving the existing
column order so `scores_chart.html` and any pivoting keep working. Because it is
regenerable, a stray hand-edit cannot put it at odds with the run records.

## SME review cycle

Repo files are canonical. The spreadsheet is a round-trip artifact.

```bash
atlas-eval review export --bank v3 --status unverified -o v3_sme_review.xlsx
atlas-eval review import v3_sme_review_oscar.xlsx
```

Export writes the two-sheet layout the existing `SME_review_brief.xlsx` already uses
(`Review` and `Our tracking`), so reviewers see a familiar document. Review columns: id,
question, type, expected answer, notes, `accurate?`, reviewer, comments.

Import matches rows by id and writes the `verification` block back into the bank YAML,
making each reviewer verdict a tracked git diff. Two guards, both load-bearing:

- The sheet's question text is compared against the file's, and a mismatch **aborts** the
  import. An edit made in Excel must not silently redefine a frozen question.
- Import **never writes `ground_truth`**. A reviewer correction lands in
  `verification.notes`; promoting it into ground truth is a deliberate separate edit in
  git. Otherwise a reviewer's offhand phrasing quietly becomes the answer key, which is
  precisely the failure this dataset exists to prevent.

Unknown ids abort rather than being appended, and the command prints a summary of status
transitions before writing.

## Migration

Moves into the repo (roughly 1.3 MB total):

| Source | Destination |
|---|---|
| `question_bank.md` (v1-v5 sections) + `v1..v5_answer_key.md` | `data/banks/v1.yaml` .. `v5.yaml` |
| `v6_draft.md` | `data/banks/v6.yaml`, `frozen_on: null` |
| `scores.csv` (224 rows) | split per run into `data/runs/*/scores.csv`, rollup regenerated |
| `chats/` (27 transcripts) | `data/runs/*/transcript.md` |
| `snapshots/` (40 agent + spaces JSON) | `data/runs/*/snapshot.json` |
| `persona_inventory/`, `one_offs/`, `Michael Audit Notes.md`, `2801_tracker_draft.md`, `2802_comment_draft.md`, `sharepoint_doc_inventory.csv`, `scores_chart.html`, both SME `.xlsx` | `reference/` |

Transcripts and snapshots are keyed by the same `<date>_<time>_<agent>` stamp as the
`scores.csv` `run_finished` column, so run directories reconstruct unambiguously.

Explicitly does **not** move, being knowledge-base source material rather than audit
material, and belonging to the Loops KB repo:

- `SharePoint - Current System Documentation` (916 MB)
- `Tech Specs` (10 MB)
- `Product Briefs` (1.8 MB)
- `v5_reference` (856 KB)

Migration is mechanical but not blind: converting six banks and five answer keys into the
new schema requires reading each question's ground truth to populate `checks`. The
`required_all` / `forbidden` / `expect_citations` terms are derived from the existing
answer-key prose, which already names them explicitly. Where a question's ground truth
does not support a deterministic check, `checks` is left empty and the question scores on
rubric only, rather than inventing a check to fill the field.

Repo is private, in the NJDOL org. Before the first push, confirm no transcript or
snapshot carries PII. The corpus is mainframe program logic, so this is expected to be
clean, but it is checked rather than assumed.

## Failure modes

Quick/Playwright, each handled explicitly rather than retried blindly:

- **Auth expiry.** Detect the SSO login redirect, abort the run as `incomplete`, print the
  re-auth instruction. Never attempt credential entry.
- **Answer-completion detection.** Wait on the streaming-stopped signal plus a DOM-quiet
  interval, with a hard per-question timeout. This is the fiddly part of scraping a
  streaming chat and it gets dedicated tests against captured fixtures.
- **Selector drift.** A missing selector aborts loudly. This is the trigger for using the
  `paste` transport.
- **Mid-run conversation loss.** Because `after` dependencies assume one continuous
  conversation, losing the thread invalidates every dependent question downstream. The
  run is marked `incomplete` rather than resumed in a fresh conversation.

Dataset layer:

- A bank edited after freezing fails `validate` on hash mismatch.
- An `after` cycle or dangling target fails `validate`.
- Duplicate question ids within or across banks fail `validate`.

## Testing

Fully offline. No AWS credentials, no network, mirroring finchy-eval's arrangement so CI
can run it unconditionally.

```bash
atlas-eval validate
pytest -q
```

`validate` checks every bank against the schema, verifies freeze hashes, rejects duplicate
ids, and confirms the `after` graph is acyclic with no dangling targets. It is the cheap
gate for the errors most likely to occur in practice.

Unit tests cover:

- **Scoring** — concept matching, stance logic, citation recall. Highest-value coverage in
  the repo, because a scorer bug silently changes every historical number at once.
- **Review round trip** — export then import returns the bank byte-identical; a mutated
  question in the sheet aborts; an unknown id aborts; `ground_truth` is never written.
- **Dataset loading** — schema errors surface with the offending question id.
- **Transcript parsing** — against a captured fixture from `chats/`.
- **Run-order resolution** — `after` dependencies produce the documented sequence.

Fixtures live in `tests/fixtures/`: a small synthetic bank and one real captured
transcript. Playwright selector logic is tested against saved HTML, not a live session.

## Sequencing and de-risking

The least predictable work is Playwright's grip on Quick's chat UI, and specifically
answer-completion detection on a streaming response. That uncertainty is resolved early
rather than deferred, because it is the one item that can invalidate the automated
transport entirely.

**Step 0, before the transport is written: a reconnaissance spike.** Open the Quick chat
agent in a headed browser and capture what the harness will have to grip:

- The message-input element and its submit affordance.
- The message-list container and the per-message boundary for a single agent turn.
- The streaming-in-progress signal (a stop button, a spinner, a busy attribute, or the
  absence of a completion marker) and whichever of those actually flips reliably when a
  long multi-paragraph answer finishes. Answers to these banks run long, so completion
  must be verified against a real lengthy response, not a one-line reply.
- Whether a conversation's turns remain addressable after the thread scrolls, since
  `after` dependencies require reading earlier answers in the same conversation.
- How `conversation_id` surfaces in the DOM or the network traffic, since the existing
  `scores.csv` records it per run.

The spike's deliverable is saved HTML of a real completed conversation, committed to
`tests/fixtures/`, plus a short findings note. Those fixtures are what the selector and
completion-detection tests run against, so the tests never need a live session.

The spike also settles a question the design cannot settle on paper: whether Quick's
completion signal is reliable enough to trust unattended. If it is not, the automated
transport gains an explicit per-question settle-and-confirm step, or the `paste` transport
becomes primary. Either outcome is cheap to absorb at step 0 and expensive to absorb after
the runner is built around an assumption.

Build order:

1. Playwright reconnaissance spike; commit DOM fixtures and findings.
2. Dataset layer: schema, loader, freeze hashing, run-order resolution, `validate`.
3. Scoring, tested against the fixtures and the 27 existing transcripts.
4. Migration of the six banks and five answer keys.
5. Review export/import round trip.
6. Quick adapter: `paste` transport first (immediately usable, no selector risk), then
   `playwright` against the step-1 fixtures.
7. Run record and rollup generation.

Steps 2 through 5 depend on nothing external, so they proceed regardless of what the spike
finds.

## Open questions

None blocking. Two to settle during implementation:

1. Whether `data/runs/` transcripts stay in git or move to S3 if the directory grows past
   a few MB. Current volume (240 KB for 27 runs) makes git fine for now, and the meeting
   settled on repo-not-S3 for the near term.
2. The exact `type` mapping for the 30 legacy free-text labels. Proposed enum covers all
   observed cases, but the mapping table is written during migration and reviewed then,
   with `type_note` preserving the original either way.
3. Whether Quick's streaming-completion signal is reliable enough for unattended runs.
   Resolved by the step-0 reconnaissance spike, not by further design.
