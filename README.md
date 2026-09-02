# Atlas Eval Harness

Auditing harness for the NJDOL Atlas chat agents. It evaluates the AWS Quick agent
today and is built so a local LLM and a future Bedrock agent can be scored against the
same frozen question banks, producing directly comparable numbers.

Design: [docs/superpowers/specs/2026-08-26-atlas-eval-harness-design.md](docs/superpowers/specs/2026-08-26-atlas-eval-harness-design.md)

## Layout

| Path | Contents |
|---|---|
| `data/banks/` | 7 question bank YAML files (v1-v7), 50 questions total, all frozen. Ground truth lives here. |
| `data/runs/` | One directory per run: `run.yaml` metadata, `responses.yaml`, `transcript.md`, `snapshot.json` config snapshot, `scores.csv`. |
| `data/scores.csv` | **Generated** rollup of every complete run. Do not hand edit. |
| `reference/` | Migrated audit material that is not part of the dataset. |
| `atlas_eval/` | The harness. |

## Everyday commands

`atlas-eval` is installed as a console script by `pip install -e .` (see `pyproject.toml`).
It is equivalent to `python -m atlas_eval.cli`; use whichever is on your PATH.

Validate every bank offline (no AWS, no network):

    atlas-eval validate --banks data/banks

Freeze a bank once its questions are settled:

    atlas-eval freeze --bank data/banks/v6.yaml --date 2026-09-01

Send a bank for SME review, then import the verdicts:

    atlas-eval review export --bank v3 --status unverified -o v3_review.xlsx
    atlas-eval review import v3_review_oscar.xlsx --dry-run
    atlas-eval review import v3_review_oscar.xlsx

Check how far verification has got, and who has returned verdicts:

    atlas-eval coverage
    atlas-eval coverage --detail

Draft rubric scores for a run, then import them once a human has reviewed the draft:

    atlas-eval rubric export --run data/runs/2026-08-12_1704_quick_v5 -o v5_rubric.csv
    atlas-eval rubric import v5_rubric.csv --run data/runs/2026-08-12_1704_quick_v5 \
      --scored-by claude-opus-5 --dry-run
    atlas-eval rubric import v5_rubric.csv --run data/runs/2026-08-12_1704_quick_v5 \
      --scored-by claude-opus-5

Report scores for every run, verified and exploratory kept separate:

    atlas-eval report

## How scoring works

Two layers, kept separate on purpose.

**Deterministic** - literal, case-insensitive substring matching against each question's
`required_all`, `required_any`, `forbidden` and `expect_citations`. No model is involved
and no semantic similarity is used, so a score computed today is comparable to one from
three months ago.

**Rubric** - five dimensions carried over from the original audit (`citations`,
`correctness`, `gap_honesty`, `scope_discipline`, `clarity`, 0-2 each). An LLM drafts
these against the answer key and a human reviews them, which is the existing Quick Chat
Audit process. Each row records `scored_by` (who or what produced the values: a model
id or a person's name) and `confirmed_by` (the human who signed off; `None` until then),
so a report can be restricted to human-confirmed scores.

The 0-2 scale is defined in [reference/rubric.md](reference/rubric.md):
2 = fully met, 1 = partially met or unverifiable, 0 = failed.

## Drafting rubric scores

`atlas-eval rubric export`/`atlas-eval rubric import` are the import/export boundary
for the rubric layer. The harness itself never calls a model — `atlas_eval/scoring.py`
is model-free and stays that way — so drafting happens outside these two commands, in
whatever tool an LLM is driven from.

    atlas-eval rubric export --run data/runs/<run-id> -o rubric.csv

writes one row per question in the run: `question_id`, `type`, `verification_status`,
`deterministic_pass` (read-only context) and blank columns for the five dimensions plus
`notes` and `scored_by`. It deliberately does **not** duplicate the question text, ground
truth, or the answer into the CSV — a second copy of a multi-thousand-character answer
would drift from the record it was copied from. Instead it prints the two paths a grader
needs: the run's own `transcript.md` (question, answer, and priming context, already
paired) and the bank YAML for that run's `bank_version` (ground truth). An LLM drafts the
five dimensions against those two files, then a human reviews the draft before anyone
runs `import`.

    atlas-eval rubric import rubric.csv --run data/runs/<run-id> --scored-by claude-opus-5

writes the filled-in rows back into that run's `scores.csv` in place. A blank row is left
unscored, not zeroed; a row must have all five dimensions or none; each scored row needs a
`scored_by` (from the CSV column, or the `--scored-by` flag); and `--confirmed-by` is the
only source for `confirmed_by` — a drafting pass can never mark its own scores confirmed.
Any problem aborts the whole import with nothing written. Always `--dry-run` first.

Import does not regenerate `data/scores.csv` — run `atlas-eval rollup` afterward, same as
after `atlas-eval run`, and before committing.

## Ground truth and verification

The banks were built with AI assistance and are being verified by SMEs incrementally, so
`verification.status` is per question and a bank is normally partly verified. Reports give
two figures and never merge them: a **verified score** over `status: verified` questions,
which is the defensible number, and an **exploratory score** over the full bank, labelled
unvetted.

`rejected` questions stay in the file with the reason. Several questions have no knowable
answer, and keeping the verdict stops them being re-litigated.

## Writing check terms

Two rules a `data/banks/*.yaml` contributor needs, both enforced by
`tests/test_bank_corpus.py` against the real corpus:

1. **Check terms encode substance, never phrasing.** Refusal and absence wordings
   ("not found", "not documented", "cannot", "unable"...) must never appear in
   `required_all` / `required_any`. Agent wording for a refusal varies between runs and
   backends, so phrasing-keyed checks produce false failures on a correctly-worded
   refusal. Refusal is a stance judgment (`expected_stance` vs. an `observed_stance`
   supplied by a human or transport signal), not a substring check. For
   `hallucination_bait` questions the deterministic signal is `forbidden` (the
   fabricated term the agent must not produce), not a required refusal phrase. The same
   logic applies to format: a bare `1.2` false-fails an answer written as `120%`, so
   surface-form variants belong in `required_any`, not `required_all`.
2. **Framing failures are not deterministically checkable.** When a documented failure
   is "states X as if documented" or "presents the spec's behavior as LOOPS behavior"
   rather than a wrong value, no substring check can express it; it belongs to the
   rubric's `scope_discipline` / `gap_honesty` dimensions instead. That's why several
   `scope_boundary` questions carry thin checks, and why four questions in the corpus
   today carry no checks at all and score on stance plus rubric alone.

One more limitation worth knowing: a `Checks` block has only one `required_any` list, so
two independent OR-groups can't be expressed. The workaround is a common substring
prefix in `required_all` (e.g. require a shared token that only the intended phrasings
contain) rather than trying to nest a second OR group.

## Development

    python -m pip install -e '.[dev]'
    python -m playwright install chromium
    atlas-eval validate --banks data/banks
    python -m pytest -q

Both run without AWS credentials or network access. The `playwright install`
step downloads the browser the DOM tests drive; skipping it leaves those tests
erroring on a fresh clone.

## Running a bank

Two transports. Both produce an identical run record.

**Paste** — you drive Quick, the harness parses. No UI risk; use it when the
result matters more than the automation:

    atlas-eval run --bank data/banks/v3.yaml --transport paste \
      --transcript my_pasted_answers.md --account-id <id> --agent-name "Engineering Onboarding Specialist"

Generate the sheet to fill in with:

    atlas-eval run --bank data/banks/v3.yaml --transport paste --print-sheet

Each question in the sheet gets an `<!-- atlas:answer <question-id> -->` marker
(an HTML comment, invisible when rendered). Paste the answer between its marker
and the next one, replacing the placeholder text; leave the markers themselves
alone. This is an HTML comment rather than a markdown heading on purpose: a
real Quick answer routinely contains its own subheadings and dozens of fenced
code blocks, and a heading delimiter collides with that content and silently
corrupts the parse. A `conversation: <id>` line is read wherever it appears in
the pasted document, not only at the end where the sheet places it.

If you return the sheet with a placeholder still in place, that question is
recorded as unanswered (not as a literal answer of placeholder text) and the
run is reported incomplete.

**Playwright** — drives the UI. Sign in once, then reuse the profile:

    .venv/bin/python tools/open_quick_session.py --url "<quick url>"
    atlas-eval run --bank data/banks/v3.yaml --transport playwright \
      --url "<quick url>" --account-id <id>

The harness never submits credentials. If a run is bounced to a login page it
aborts and marks the run `incomplete`.

An incomplete run is still written to `data/runs/` for diagnosis, exits non-zero,
and is excluded from `atlas-eval report`.

After a run, regenerate `data/scores.csv` from `data/runs/` and commit the
result:

    atlas-eval rollup

CI runs `atlas-eval rollup --check` and fails if `data/scores.csv` is out of
date with `data/runs/`, so a real run isn't finished until this has been run.
