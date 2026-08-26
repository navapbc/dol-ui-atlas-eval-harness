# Quick Chat Agent Audit: Engineering Onboarding Specialist (bank v1, post-persona-update regression run)

- **Run finished:** 2026-08-03 4:15 PM ET (timestamp of last answer in the chat UI)
- **Agent:** Engineering Onboarding Specialist (`093ac4e3-0712-481e-af95-9ddc5e4fc734`)
- **Agent change under test:** persona instructions updated 2026-08-03 3:55 PM with two new grounding rules (never adopt a user-supplied process name without verifying it in retrieved docs; expand acronyms only from KB text, never from earlier turns). This run is the v1 **regression check**: the new rules should not cost points on questions the agent already handled well (e.g. by over-refusing).
- **Snapshots:** `snapshots/2026-08-03_1615_engineering_onboarding_specialist.json`, `snapshots/2026-08-03_1615_spaces.json`
- **Spaces linked (7, unchanged):** Weekly Certification (127 docs), CWC (136), DailyUI (28), NewHire (31), LOOPS_WGPM (26), Daily CA-7 (0 at space level; docs in its S3 KB), Monthly CA-7 (11). Identical to the 2026-08-03 1:20 PM run, so the KB was unchanged. "LOOPS - Daily Batch Summary" (3,521 docs) still exists unlinked.
- **Conversation:** `5611a2c5-cb6c-4408-8f2b-d34c97b8bf8d`
- **Bank version:** v1 (frozen 2026-07-27)
- **Method:** fully automated (browser pane; typed questions, clicked Send, polled page-text length until stable across two 10s polls). Human step: none this run — the browser SSO session and CLI SSO from earlier today were still valid.

## Scorecard

| # | Question | Type | Score | Notes |
|---|----------|------|-------|-------|
| 1 | Weekly cert batch flow end to end | retrieval | 10/10 | Same quality as the 2026-07-27 13:04 run: L2DCLNUP housekeeping → VSAM snapshot → DXCBDA2R extract/classification → audit files → AUDITREP (combined/WEB/PHONE) → DXCBDA3S email extract, with the daily/weekly/monthly cadence tiers and the explicit "extract/report layer; upstream real-time and downstream ETA-539/WFD documented separately" scope note. Cited DXCBDA2R.cbl.md, DXCBDA3S.cbl.md, Engineering Overview. |
| 2 | DXCBDA2R role + I/O files | retrieval | 10/10 | Full I/O inventory (PAYVSAM/LOOPPFLE 323B, NOPAY/NOPAYFLE 281B, 12 audit outputs at 350B, AUDITREP, BYPASS), paragraph-level logic, BP88 classification fields, and the non-mutually-exclusive-buckets caveat. |
| 3 | Pay vs. no-pay business rules | retrieval | 9/10 | Strong structure: real-time decision vs batch extract distinction, UIMI0440 suppression-code reasons, DXCD036S C012 no-pay conversation, net-check formula, DXCBDA3R audit rules, and an explicit "what is not in the KB" section for the CICS eligibility logic. Docked correctness 1 for repeating the 13:04 run's conflation: says "the precise partial-benefit formula (earnings disregard and reduction) is documented in DXCD037S" — DXCD037S documents the PWBR *threshold*, not the reduction arithmetic (that lives in DXCBD87E per the v2 key). |
| 4 | Exact partial-benefit offset formula | gap probe | 10/10 | PWBR = MAX(WBR×1.2, WBR+$5) stated as confirmed per the anchor doc's verified-formula exception, with the $25 crossover; net-check field arithmetic cited to UIMI0440; explicit inference warning that the earnings→deduction conversion is not documented and needs SME confirmation. |
| 5 | T120 category-to-payable-days values | gap probe | 10/10 | Premise corrected (mailing-date skip-day calendar, not payable-days), layout from T120TABL.cpy, values ops-maintained in CODELOOP VSAM outside the KB, annual refresh, where to get them. |
| 6 | CWC process + programs | cross-space | 10/10 | PC-40/41/42/43, D055 CICS chain (DXCD034S→036S→037S→038S), overlap detection flags, batch splitter DXCBD33S, UIMB0031/DXCP802U transfer charges, UIMR0030/DXCBP500 charging split, L217ML/L218MV JCL, data stores. Labeled synthesized; shared-module note included. |
| 7 | ZXQQ9999 | hallucination bait | 10/10 | Clean refusal with naming-convention table and search offers. |
| 8 | Production deployment process | out-of-KB | 10/10 | Explicit not-covered statement, enumerated missing items, grounded environment facts (LAK2LDXP libs, LOPD partitions, JTAC/JTSF/JPAF), correct routing to ops/change management. |

**Total: 79/80 (99%)** — identical to the 2026-07-27 13:04 post-consolidation run (79/80), same single dropped point (the DXCD037S formula-location conflation).

## Findings

1. **No regression from the persona update.** The two new grounding rules did not cause over-refusal anywhere: Q7 (bait) and Q8 (out-of-KB) behaved exactly as before, and the retrieval questions kept their grounded, cited answers. The Q5 premise correction ("category-to-payable-days" is a misnomer) shows the name-verification rule enhancing, not blocking, a legitimate answer.
2. **The one surviving v1 defect is stable:** the agent keeps pointing at DXCD037S as the home of the earnings-reduction arithmetic. Candidate anchor-doc line (carried over from v2): a DXCBD87E pointer for the payment-derivation chain.
3. Q1's channel classification repeats the DXCBDA2R BRE reading (9000+'7777' = WEB) without surfacing the UIMB0440 SIM conflict; not docked on v1 (the bank predates that erratum) but it is the same open SME question logged in the v3 run-1 report.
