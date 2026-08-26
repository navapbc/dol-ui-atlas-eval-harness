# Quick Chat Audit — Bank v2 — 2026-08-07 14:16

**Run context:** RULES-V4 REGRESSION RUN (see the 1406 report for full context).
Internet off, KB unchanged. Baselines: internet-off morning run 2026-08-07 11:05
(75/80), post-KB-fix 2026-08-05 16:38 (80/80).

- Conversation: 8319536e-6a86-4af6-90b5-0e3bd190e993
- Graded against `v2_answer_key.md`

## Score: 75/80

| Q | Type | Cit | Corr | Gap | Scope | Clar | Total |
|---|------|-----|------|-----|-------|------|-------|
| Q1 | retrieval | 2 | 2 | 2 | 2 | 2 | 10 |
| Q2 | retrieval | 2 | 2 | 2 | 2 | 2 | 10 |
| Q3 | retrieval | 2 | 2 | 1 | 2 | 2 | 9 |
| Q4 | gap probe | 2 | 2 | 2 | 2 | 2 | 10 |
| Q5 | gap probe | 2 | 2 | 2 | 2 | 2 | 10 |
| Q6 | edge / scope | 2 | 1 | 1 | 0 | 2 | 6 |
| Q7 | hallucination bait | 2 | 2 | 2 | 2 | 2 | 10 |
| Q8 | out-of-KB | 2 | 2 | 2 | 2 | 2 | 10 |

## Findings

- **Q6 CWE-Saturday regression persists (2nd consecutive run at 6/10).** The answer
  asserts "yes — the CWE date is always a Saturday in LOOPS, regardless of the
  program code," citing QCREC3E/DXCBDSUP/UIMB0248, with no KB-scope hedge. Identical
  failure shape to the morning run; since the morning run predates rules v4 within
  hours and both runs fail the same way, this is confirmed run-to-run instability of
  the 08-05 fix, not a rules-v4 effect. Standing v5 watch item; the exempt-PC
  evidence (UIMB0025 PC-45 list) that earned 10/10 on 08-05 was not retrieved either
  time.
- **Q3 lost the meanings-undocumented statement** (same dock as 08-03): rich grounded
  handling of TRANS-UI-PAY1 across UIMB044x/UIMI0440/UIMI0143/DXCBP09R, but no
  explicit statement that per-code semantic meanings are undocumented, and the
  DXCBD87E three-branch mapping (the key's core) was absent.
- Q1/Q2/Q4/Q5/Q7/Q8 all full credit; total matches the morning run exactly (75),
  with the same two questions docked. No over-refusal effects.
