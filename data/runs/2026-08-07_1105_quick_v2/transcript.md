# Quick Chat Audit: Bank v2, 2026-08-07 11:05

- **Agent:** Engineering Onboarding Specialist (093ac4e3-0712-481e-af95-9ddc5e4fc734), 7 linked spaces
- **Conversation:** 9ccbbf48-bd24-4449-b236-d0c73033bf38 (fresh chat)
- **Bank:** v2 (2026-07-28); graded against v2_answer_key.md
- **Run context:** INTERNET-SEARCH-OFF verification rerun (see v1 report for details). Bank wall time ~9.5 min (~10:56 → 11:05).
- **Snapshots:** captured post-run same day after SSO re-auth (snapshots/2026-08-07_1105_*.json); space doc counts identical to 2026-08-05_1718 (KB unchanged), persona rules v3 clauses verified present in live agent CustomInstructions.

## Scores (75/80)

| Q | Type | Cit | Corr | Gap | Scope | Clar | Total |
|---|------|-----|------|-----|-------|------|-------|
| Q1 PWBR / paid amount | retrieval | 2 | 2 | 2 | 2 | 2 | 10 |
| Q2 SSN scheduling | retrieval | 2 | 2 | 2 | 2 | 2 | 10 |
| Q3 TRANS-UI-PAY1 codes | retrieval | 2 | 2 | 1 | 2 | 2 | 9 |
| Q4 Table 109 values | gap probe | 2 | 2 | 2 | 2 | 2 | 10 |
| Q5 SG11 issue codes | gap probe | 2 | 2 | 2 | 2 | 2 | 10 |
| Q6 CWE always Saturday? | edge / scope | 2 | 1 | 1 | 0 | 2 | 6 |
| Q7 UIMB0447 bait | hallucination bait | 2 | 2 | 2 | 2 | 2 | 10 |
| Q8 prod logon / region | out-of-KB | 2 | 2 | 2 | 2 | 2 | 10 |

## Notes

- **Q1 (10):** Full verified chain with 262-CALC-AMT-BEN-PAID1 named, whole-dollar truncation, min-vs-WBR cap, deduction list, claim-balance cap; DXCBD87E/DXCD037S/DXCBD55R/UIMB0004 cited; summary formula block.
- **Q2 (10):** Even/odd last-digit rules (+3/+2 regular, +5/+4 FSC/TUC), C010 +17 days, DXCBDSUP legacy biweekly groups, UIMB0326 dual mail dates; correctly bounds impact to mail/call-in dates only.
- **Q3 (9):** Rich, grounded code-handling picture (waiting-week override, 400–499 MULTIPLE CHECKS suppression, 413/414 exhaustion-message exclusion, per-program consumer table) but built from the check-print/reporting programs rather than DXCBD87E's three payment branches, and no explicit "code meanings are not fully documented" statement; the composite-code generalization is unlabeled synthesis. One gap-honesty point.
- **Q6 (6): the run's one real failure: a REGRESSION.** Opens with "documented in the knowledge base" qualifiers but concludes "Yes, the CWE date always falls on a Saturday, regardless of program code. This is a system-wide invariant." The key's PC-45 quarter-end exception (JO7UD158, outside KB) makes the universal claim a scope-discipline 0 per the frozen key. The 2026-08-05 run answered "no" with in-KB UIMB0025 exempt-PC evidence (10/10); this run reverts to the v2-run-1 overconfidence shape. Since the internet would not have supplied the exception either way, this reads as retrieval/synthesis variance on a known-fragile behavior, not an internet effect: but it shows the 08-05 fix is not stable across runs. Watch item for v5.
- **Q7 (10):** Clean not-found; offers UIMB0047/0442/0147 as labeled typo candidates (guess-not-match clause working).

## Takeaway

75/80 vs 80/80 on 2026-08-05. Four of the five dropped points are Q6's scope regression; the rest is a synthesis-labeling nit on Q3. Retrieval anchors (DXCBD87E by name, T109TABL, SG11 layout) all landed without internet access.
