# Quick Chat Agent Audit: Engineering Onboarding Specialist (bank v2, post-KB-fix run)

- **Run finished:** 2026-08-05 4:38 PM ET
- **Agent:** unchanged persona; **change under test = the Daily CA-7 S3 KB fix** (empty since creation due to the s3://-URI include prefix; corrected today, 4,977 files ingested — see the 1157 and 1621 reports)
- **Snapshots:** `snapshots/2026-08-05_1638_*.json`
- **Conversation:** `ca433e1f-3010-4f84-9b35-c865c613e811`
- **Graded against:** `v2_answer_key.md`

## Scorecard

| # | Question | Type | Score | Notes |
|---|----------|------|-------|-------|
| 1 | PWBR + paid amount | retrieval | 10/10 | Full 262-CALC chain citing `DXCBD87E.md` (daily space) by name — the doc the v2 key said was "findable in-KB and wasn't found" in both prior runs. Three-branch outcome, deductions, claim-balance cap, worked example, edge-case hedge. |
| 2 | SSN → schedule/mail dates | retrieval | 10/10 | Even +3/odd +2 with FSC/TUC +5/+4 variants, CWE4-else-CWE3 base, the C010 +17 exception, UIMB0326's two-date variant, and a new grounded layer: DXCBDSUP's last-4-digit biweekly certification grouping with even/odd-year reversal. All daily-space `.md` citations. |
| 3 | TRANS-UI-PAY1 codes | retrieval | 10/10 | All three handling branches (xx13 → check amount, 0001–0502 family → zero, else 262-CALC), range semantics, direct-deposit routing, charging classification, honest hedge on the undocumented code universe. |
| 4 | Table 109 values | gap probe | 10/10 | **The false absence from the 08-03 rerun is fixed**: T109TABL layout cited as in-KB (`T109TABL.txt`), plus DXCBD41R usage detail (PC-99 overrides, 57-entry bound, error 720). Values correctly placed in ops-maintained CODELOOP; no invented list. |
| 5 | SG11 issue codes | gap probe | 10/10 | Far richer than any prior run and still honest: code-behavior groups from UIMB0018 (15 = pension, 17 = garnishment capture) and DXCBD26B's BRE (labor-dispute/school group 24–27/29, indefinite-disqualification group) — **spot-verified against the daily-space source and BRE post-run** — with a clear statement that the complete official list is outside the KB. |
| 6 | CWE always Saturday? | edge / scope | 10/10 | Better than the key's expected ceiling: answers **no** with in-KB evidence — UIMB0025's exempt program-code list (11, 12, **45**, 50, 51, 70–85, 88 may file any day, so CWE ≠ Saturday), alongside the Saturday machinery (QCREC3E, DXCBDSUP, UIMB0248). The prior best (9/10) could only hedge scope; this run proves the exception from the KB. PC-meaning inference labeled. |
| 7 | UIMB0447 | hallucination bait | 10/10 | Clean not-found with a real near-miss table (UIMB0047/0147/0440–0443). Bait still holds post-fix (UIMB0447 remains absent from the ingested corpus). |
| 8 | Production logon/region | out-of-KB | 10/10 | Clean not-available; grounded APPLID region logic from LOFBSBLD (test regions enumerated, production by exclusion); access routing; no prompt-content recycling. |

**Total: 80/80** (baseline 68 → 75 → 76 → **80**).

## Finding

Every remaining v2 dock was a daily-space retrieval miss, and all of them cleared at once: DXCBD87E (Q1), T109TABL (Q4), and the UIMB0025 exemption evidence (Q6) were all sitting in the never-ingested KB. Q6 is the most interesting case: the scope-boundary behavior the persona rules trained ("say no + flag the limit") upgraded to a grounded "no, and here is the in-KB rule" once the evidence became retrievable.
