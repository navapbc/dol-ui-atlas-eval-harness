# Rubric (all versions)

Migrated verbatim from `question_bank.md` §"Rubric (all versions)". The original
converter extracted only the per-version question tables, so this scale was
absent from the repo until 2026-08-27 — every rubric score before that was
drafted against an undefined scale.

Score each answer 0-2 on five dimensions (10 max per question):

1. **Citations** — cites real documents from the space
2. **Correctness** — consistent with source code / Transform analysis / known facts
3. **Gap-honesty** — says "not available" instead of inventing; hedges inferences
4. **Scope discipline** — stays within the KB; flags narrowed scope
5. **Clarity** — structured, usable answer for the target audience

**Scoring guide: 2 = fully met, 1 = partially met or unverifiable, 0 = failed.**

## Column names

The CSV columns use the snake_case forms: `citations`, `correctness`,
`gap_honesty`, `scope_discipline`, `clarity`, and `total` (0-10).

## How the 224 legacy rows used this scale

Worth knowing before comparing new scores against them. Across those rows
`clarity` was 2 in every single case and never discriminated; `citations` was 2
in 221 of 224 and `scope_discipline` 2 in 207. Only `correctness` and
`gap_honesty` carried real variance. A stricter reading of the same scale will
produce lower numbers that are not directly comparable to that baseline.
