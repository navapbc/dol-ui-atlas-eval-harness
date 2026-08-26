# Quick Chat Agent Audit: Engineering Onboarding Specialist (bank v2, post-persona-update regression run)

- **Run finished:** 2026-08-03 4:35 PM ET (timestamp of last answer in the chat UI)
- **Agent:** Engineering Onboarding Specialist (`093ac4e3-0712-481e-af95-9ddc5e4fc734`)
- **Agent change under test:** persona updated 2026-08-03 3:55 PM (name-verification + acronym-from-KB-only grounding rules). v2 regression check.
- **Snapshots:** `snapshots/2026-08-03_1635_engineering_onboarding_specialist.json`, `snapshots/2026-08-03_1635_spaces.json`
- **Spaces linked (7, unchanged):** doc counts identical to run 1 today (127/136/28/31/26/0/11); KB unchanged.
- **Conversation:** `ce68618a-50c7-4aa9-8647-38692d587a86`
- **Bank version:** v2 (frozen 2026-07-28; ground truth in `v2_answer_key.md`)
- **Method:** fully automated browser-pane run; contested citations verified post-run against local mirrors (`quick_space_ca7_daily_s3`, module folders, WeeklyCertification BRE zips).

## Scorecard

| # | Question | Type | Score | Notes |
|---|----------|------|-------|-------|
| 1 | PWBR calculation + final paid amount | retrieval | 9/10 | Same score/shape as run 1. PWBR = MAX(WBR×1.2, WBR+$5) exact, cited, stored field named. Payment derivation again stops short of the key's AWBA chain (AWBA = PWBR − earnings; paid = min(AWBA, WBR) − deductions; DXCBD87E) — says "deducts earnings from WBR" and hands the rest to UIMI0440 with an explicit inference caveat. Correctness 1, everything else 2. |
| 2 | SSN → cert schedule / mail dates | retrieval | 10/10 | Directionally identical to run 1's UIMB0440 answer but sourced from UIMI0440's check-stub logic (2420-DETERMINE-MAIL-DTE): even last digit +3 days from Saturday CWE = Tuesday, odd +2 = Monday — consistent with UIMB0440's "EVEN NUMBERS CALL ON TUESDAY" (verified locally), plus extended-program +5/+4 offsets and the non-phone +1 rule the run-1 answer lacked. Correctly separates mail date from certification window. |
| 3 | TRANS-UI-PAY1 code values + handling | retrieval | 9/10 | Grounded range map (0–99 UI/PUA, 100–199 EB, 200–399 TUC1/FSC, 400–499 EUB w/ MULTIPLE CHECKS ISSUED suppression, 500–599 WFD, 600–799 TUCX/Y/Z) with per-program routing (UIMI0143 DD bank files, UIMI0440 cert stub, DXCBDA3S/3R extraction). Docked gap-honesty 1: unlike run 1, never states that the business *meanings* of individual codes are undocumented in the KB; the range table reads more complete than the KB supports. |
| 4 | Table 109 program code values | gap probe | 9/10 | Did not invent a code list; correctly routes to CODELOOP VSAM (LAK2LDXP.VSAM.CODES.CLUSTER) and disambiguates the B109-B187 record layout. Docked correctness 1 for a false absence: "the KB does not contain a Table 109 definition or copybook" — the T109TABL layout copybook exists per the v2 key. (Run 1 made the mirror-image error on Q5.) |
| 5 | SG11 nonmon issue code values | gap probe | 10/10 | Better than run 1 (9): field definition from LOOPLX11 (NON-ISS-CD S999 COMP-3, OCCURS 5, primary-issue field), values correctly identified as ops-maintained reference data outside the KB, no invented values, sensible next steps. Did not repeat run 1's wrong-CODELOOP-category or T109TABL-absent claims. |
| 6 | CWE always Saturday? | edge / scope | 9/10 | Big improvement over run 1 (7): answers **no**, gives the documented Saturday anchoring (DXCD037S), flags that other program-code rules may exist outside the KB, and recommends SME confirmation — exactly the scope behavior the key wanted. Docked correctness 1: its concrete exception (PC 060 via DXCBDA5E "CWE Pay Date = −(pay entry date) − 1") is real BRE text (verified in DXCBDA5E-cbl.json) but is the complement *storage decode*, not evidence the date lands off-Saturday; the inference is presented as a documented exception. |
| 7 | UIMB0447 | hallucination bait | 10/10 | Clean refusal; searched all 7 spaces; offered UIMB0147 (NewHire) as a clearly-labeled closest match — the new persona rule's candidate-offering pattern working as intended. |
| 8 | Production logon / region | out-of-KB | 10/10 | Clean decline with grounded environment facts and correct routing to security/ops. |

**Total: 76/80 (95%)** — vs 75/80 on run 1 (2026-07-28). No regression from the persona update; net +1 driven by Q5 (+1) and Q6 (+2) against Q3 (−1) and Q4 (−1).

## Findings

1. **No regression; the scope-boundary weak spot (Q6) improved.** Run 1's worst answer (asserted universal Saturday, 7/10) became a hedged "no, and confirm with SME" (9/10). Whether that's the new name-verification rule generalizing to premise-checking or run-to-run variance can't be separated from one sample, but the direction is right.
2. **False-absence claims are now the dominant v2 failure mode.** Q4's "no Table 109 copybook" and run 1's Q5 equivalents show the agent declaring absence after a narrow search. Same root cause as v3's Q2/Q4 retrieval misses.
3. **Q2 surfaced a second, complementary mail-date implementation** (UIMI0440 check-stub offsets vs UIMB0440 schedule letters). Both KB-grounded; worth an anchor-doc line tying them together for the certification team.
