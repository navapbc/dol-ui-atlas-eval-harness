# Grounded judging: what an LLM judge can certify without an SME

**Date:** 2026-09-09 · **Answers judged:** the 50 from the 2026-09-08 sweep 2 · **Judges:** `us.anthropic.claude-opus-5`, `us.anthropic.claude-opus-4-8`, both `judge-v2-grounded`

## Method

Each answer is graded against the excerpts the system actually retrieved for
that question (from the eval store, 10 per question), not against the bank's
answer key. The judge lists `unsupported_claims` and reports agreement with a
model-generated reference answer as a separate 0–2 field that is never scored.

Calibration: the 12 reference answers that humans rated (Brett, Oscar, Billy)
were themselves judged against the same evidence, with no reference block, and
compared to the human 1–5 on a normalised scale.

## Results

| judge | faithfulness | unsupported claims | ref. agreement | ref. disputes |
|---|---:|---:|---:|---:|
| Opus 5, key-based | 346/500 (69%) | — | — | 5 |
| Opus 5, grounded | 455/500 (91%) | 47 across 25 answers | 78/98 | 33 |
| Opus 4.8, grounded | 486/500 (97%) | 8 across 5 answers | 70/100 | 22 |

Inter-judge (grounded): within 1 point on 42/50, within 2 on 46/50. No answer
scored ≤5/10 by both. Judges differ by 3+ on v3-Q2, v5-Q1, v5-Q4, v6-Q2.

**Ceiling check.** Faithfulness averaged 9.9/10 both on the 14 questions where
the system retrieved none of the expected documents and on the 29 where it
retrieved all of them. The metric is invariant to retrieval quality by
construction.

**Reference agreement by type** (Opus 4.8): out_of_kb, absence_probe,
generation_probe 100%; hallucination_bait 92%; gap_probe 90%; rule_logic 83%;
data_flow 67%; scope_boundary 62%; **retrieval 53%**.

## Calibration against the 12 human ratings

| judge | aligned | harsher than human | more lenient |
|---|---:|---:|---:|
| Opus 5 | 3/12 | 7 | 2 |
| Opus 4.8 | 5/12 | 5 | 2 |

Every "harsher" case carried 2–7 unsupported claims: the reference asserted
things absent from the retrieved evidence, which humans rated true from
knowledge. The judge measured faithfulness; the humans measured truth. Not
judge error — the corpus-scope gap, per question.

The two "lenient" cases were the same two for both judges:

- **v3-Q3** — human 1/5: *"no reference to program UIMR0030 on the mainframe;
  perhaps a complete hallucination."* `UIMR0030.md` exists in the corpus. The
  Transform derivative may document a program that does not exist; a judge
  grading against that corpus finds the claims supported.
- **v6-Q7** — human 1/5: *"these are not FEINs but charge codes."* A
  domain-semantics error the evidence does not state.

## What this establishes

A grounded LLM judge can certify **faithfulness** — that an answer stays inside
its evidence, does not fabricate, and stops where the evidence stops. That is
the property that distinguishes this system from a comparator that fills gaps
confidently, and it needs no subject-matter expert.

It cannot certify **truth** where the corpus itself is wrong or the error is
semantic and unstated, and inter-judge disagreement will not flag those cases
either. Those need a person. The human ratings already say which rows: the
ones scored 1 or 2.

The system's failure mode, on this evidence, is *did not have the evidence*,
not *made something up*. Retrieval coverage and corpus scope are the work.

## Not done

Fable 5 / 5.1 were unavailable as a second model line: Bedrock rejects them
with *"data retention mode 'default' is not available for this model"*, a
data-handling opt-in that was not changed. Opus 4.8 is the same family as the
primary judge, so agreement between them is a weaker independence check.

Durable outputs: `.local/eval-runs/judged-2026-09-08-sweep2/` (judged CSVs,
`compare_judges.py`), `.local/reference/` (workbook extract, calibration JSON).
