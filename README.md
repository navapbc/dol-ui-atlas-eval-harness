# Atlas Eval Harness

Auditing harness for the NJDOL Atlas chat agents. It evaluates the AWS Quick agent
today and is built so a local LLM and a future Bedrock agent can be scored against the
same frozen question banks, producing directly comparable numbers.

Design: [docs/superpowers/specs/2026-08-26-atlas-eval-harness-design.md](docs/superpowers/specs/2026-08-26-atlas-eval-harness-design.md)

## Layout

| Path | Contents |
|---|---|
| `data/banks/` | 6 question bank YAML files (v1-v6), 50 questions total. v1-v5 are frozen; v6 is held out, unfrozen. Ground truth lives here. |
| `data/runs/` | One directory per run (28 migrated runs today): `run.yaml` metadata, `responses.yaml`, `transcript.md`, `snapshot.json` config snapshot, `scores.csv`. |
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
    atlas-eval validate --banks data/banks
    python -m pytest -q

Both run without AWS credentials or network access.
