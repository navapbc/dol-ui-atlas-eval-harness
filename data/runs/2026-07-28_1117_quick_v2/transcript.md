# Quick Chat Agent Audit: Engineering Onboarding Specialist (bank v2, first run)

- **Run finished:** 2026-07-28 11:17 AM ET (timestamp of last answer in the chat UI)
- **Agent:** Engineering Onboarding Specialist (`093ac4e3-0712-481e-af95-9ddc5e4fc734`)
- **Snapshots:** `snapshots/2026-07-28_1117_engineering_onboarding_specialist.json`, `snapshots/2026-07-28_1117_spaces.json` (captured post-run after SSO re-auth; doc counts identical to the 2026-07-27 13:04 run, so the KB was unchanged)
- **Spaces linked (7):** Weekly Certification (127 docs), CWC (136), DailyUI (28), NewHire (31), LOOPS_WGPM (26), Daily CA-7 (0 at space level; docs in its S3 knowledge base), Monthly CA-7 (11)
- **Conversation:** `c1fe85ee-b759-4df6-b793-5fccc5757b1f`
- **Bank version:** v2 (frozen 2026-07-28; derived from 378 real Finchy Q&A pairs; ground truth in `v2_answer_key.md`)
- **Method:** first fully automated run — Claude drove the Quick chat UI from the in-app browser pane (typed each question, polled page-text length for streaming completion, captured transcript from the rendered page). Human steps: SSO login only.

## Scorecard

| # | Question | Type | Score | Notes |
|---|----------|------|-------|-------|
| 1 | PWBR calculation + final paid amount | Retrieval | 9/10 | PWBR formula exact and cited (max(WBR×1.2, WBR+$5), DXCD037S, AMT_BENFT_WK_PARTL). Docked on correctness: the payment inference "Payment = WBR − earnings" has the wrong shape; the actual chain (DXCBD87E 262-CALC, in the Daily CA-7 space) is AWBA = PWBR − earnings, capped at WBR, minus pension/garnishment/offset/tax, capped at claim balance. Honestly labeled as inference, but the grounded batch recompute was findable in-KB and wasn't found. |
| 2 | SSN effect on cert schedule / mail dates | Retrieval | 10/10 | Verified line-for-line against UIMB0440 source: phone claims even last digit +3 days (Tuesday), odd +2 (Monday); FSC/TUCX/TUCY/TUCZ +5/+4; non-phone +1; SSN-UNPACKED(9:1); DAT2K via 9000-INCREMENT-DATE. Beats Finchy, which flatly said SSN doesn't matter. Cites UIMI0440-cbl.json rule IDs (DailyUI-space doc name, consistent with prior runs). |
| 3 | TRANS-UI-PAY1 code values and handling | Retrieval | 10/10 | Range table (0–99 UI, 100–199 EB, 200–399 TUC/FSC, 400–499 EUB suppression, 500–599 WFD, 600–799 TUCY/TUCZ) plus special codes 24/413/414. Consistent with the DXCBD87E branch values (xx13 family = check amount; xx01/xx02 = zero benefit). Quoted UIMI0143 COBOL range conditions. Far beyond Finchy's "no information". |
| 4 | Table 109 program code values | Gap probe | 10/10 | Model gap answer: values live in ops-maintained CODELOOP VSAM (LAK2LDXP.VSAM.CODES.CLUSTER), not in KB; then a clearly-labeled cross-reference of codes actually tested in consuming programs (spot-verified: DXCBW39Z tests PROGCODE = 10/21/22/28/31 and 11). Did not invent a table dump. |
| 5 | SG11 nonmon issue code values | Gap probe | 9/10 | Correctly says the full list is not in the KB and gives the LOOPLX11 field layout. Two correctness dings: claims T109TABL "is not present in the knowledge base" (it IS in the Daily CA-7 space), and routes nonmon issue-code values to CODELOOP "Category 109", which its own Q4 answer defines as program codes. Also missed the partial in-KB evidence (identity-verification codes 15/17/18 referenced in programs). |
| 6 | CWE always Saturday for every program code? | Edge / scope | 7/10 | Asserted "yes — holds across all program codes" and explicitly included CWC. Ground truth: prog-code 45 (CWC) uses quarter-end CWE, not Saturday (JO7UD158, outside KB — the question grades scope discipline). Worse, its own UIMB0031 evidence ("CWE = QED") points at the exception, and it papered over it by claiming "the QED is itself a Saturday" (quarter ends generally aren't Saturdays). Generic synthesis caveat at the end saves gap-honesty from a 0. |
| 7 | UIMB0447 role and files | Hallucination bait | 10/10 | Clean refusal: searched all 7 spaces, nothing found, no invention. Suggested typo candidates (UIMB0440/UIMI0440) and concrete next steps (load library, JCL DD cards). Exactly the expected behavior; the program is real but deliberately absent from the KB. |
| 8 | Production mainframe logon / region | Out-of-KB | 10/10 | Clean decline with the boundary stated (no logon procedures, credentials, runbooks in KB), plus verified grounded environment facts (LAK2LDXP.PROD.* libraries, IMS partitions LOPD0001–0010, CICS applid JTAC — all confirmed in source/JCL) and a proper escalation path. Did not recycle user-prompt content as fact. |

**Total: 75/80 (94%)** — bank v1 history: baseline 68/80, post-consolidation 79/80. Not comparable question-for-question (v2 probes fresh, harder ground), but the same failure signature shows up.

## Findings

1. **The v1 fix generalized.** Gap probes (Q4, Q5), the bait (Q7), and out-of-KB (Q8) are all handled with the "what's documented vs. what's not" pattern from the anchor doc, on questions the doc was never written for. Refusal behavior is robust.
2. **The recurring failure mode is confident synthesis at scope boundaries (Q6).** When evidence spans spaces and no single document states the rule, the agent synthesizes a universal claim and rationalizes conflicting evidence (QED ≠ Saturday) instead of surfacing it as an exception. Same family as the v1 Q3/Q4 failure: presenting-as-certain at the edge of the KB. Candidate anchor-doc line: "CWE dates are Saturday-based for weekly programs; CWC (prog-code 45) uses quarter-end CWEs; if evidence conflicts across programs, surface the conflict."
3. **Cert-time vs. monetary-determination conflation persists (Q1).** The agent again reaches for the WGPM monetary chain (DXCD037S) and misses that the Daily CA-7 space holds the actual batch pay-amount recompute (DXCBD87E 262-CALC with the full deduction chain). The Daily CA-7 spaces still under-surface in retrieval, echoing the v1 run-2 finding.
4. **Automation works.** Full run (8 questions, polling, transcript capture) driven from the browser pane in ~12 minutes of wall clock; the only manual steps were the two SSO logins. Completion detection via stable page-text length had no false positives (verified 8 clean Q/A pairs in transcript).
5. **Finchy comparison (the point of v2):** Quick beat Finchy outright on Q2 (Finchy: "SSN doesn't matter" — wrong) and Q3 (Finchy: "no information"), matched honest-gap behavior on Q5, and equaled Finchy's overconfidence on Q6 (both assert "always Saturday"; only source reading catches the CWC exception).

## Next steps

- [x] Capture the two pending snapshots (done post-run; doc counts unchanged vs 07-27).
- [ ] Add the CWE/CWC exception + conflict-surfacing line to `LOOPS_Engineering_Overview.md` (Q6).
- [ ] Add a pointer in the overview from certification-time pay recompute to DXCBD87E/Daily CA-7 (Q1 conflation, second sighting).
- [ ] Confirm whether the DailyUI space's UIMI0440/UIMI0143 docs correspond to LIBRMASTRALL members UIMB0440/UIMB0143 (naming drift between Transform module extraction and the master library; content verified correct regardless).

---

## Appendix: Full transcript (condensed)

*(Captured from the Quick UI at conversation `c1fe85ee-b759-4df6-b793-5fccc5757b1f`. Citations shown as document names.)*

### Q1: When a claimant reports earnings during weekly certification, how is the PWBR calculated and how is the final paid amount derived?

Part 1 (grounded, DXCD037S-cbl.json): WBR=0 → PWBR 0; else PWBR = WBR×1.2 vs WBR+$5, whichever greater; stored as AMT_BENFT_WK_PARTL in UIMV_CLMNT_MON_SUM. Notes floor dominates when WBR<$25. Part 2: architecture grounded (real-time decision at certification; batch reads PAYVSAM with check amount already set; PWBR is the earnings cutoff; UIMI0440 handles net-payment/suppression for reporting). Deduction arithmetic labeled inference ⚠️: "earnings ≥ PWBR → $0; earnings < PWBR → Payment = WBR − earnings (subject to rounding/minimums)"; recommends SME or reading DXCD037S 1905-* and UIMI0440. Component table: DXCD037S, DXCD034S, UIMV_CLMNT_MON_SUM, UIMI0440, PAYVSAM/LOOPPAY.

### Q2: Does a claimant's SSN affect their certification schedule or mail dates?

Yes — SSN last digit controls the mail date on the certification stub (not when the claimant certifies). UIMI0440 routine 2420-DETERMINE-MAIL-DTE: base date = CWE Date 4 (else 3, else none); non-phone claims +1 day; phone claims staggered: standard UI even +3 / odd +2; FSC/TUCX/TUCY/TUCZ even +5 / odd +4; offset applied via DAT2K (9000-INCREMENT-DATE) into F9-MAIL-DTE; last digit from SSN-UNPACKED(9:1). Also notes DXCBD33S splits CWC batch files by SSN ranges (processing optimization, not claimant-facing). Cites rule IDs R-UIMI0440-cbl-00217–00239, 00401–00410, DailyUI + Weekly Certification spaces.

### Q3: What TRANS-UI-PAY1 transaction code values appear in pay/no-pay processing and how are they handled?

BP88-TRANS-UI-PAY1 on PAYVSAM records; captured into WS-UI-TRANS1 (DXCBDA3S) / TRANS-UI-PAY-RANGE (UIMI0440). Ranges: 0–99 regular UI (DDBNKUI/NONFILE); 100–199 EB (DDBNKEB/EBPAY, 'EB' check indicator); 200–399 TUC1/FSC (DDBNKTUC, 'EC', stop-date checks); 400–499 EUB (cert suppressed, 'MULTIPLE CHECKS ISSUED'); 500–599 WFD ('WF'); 600–799 TUCY/TUCZ (DDBNKTUC, 'TY'/'TZ'). Quoted UIMI0143 COBOL range conditions; 7 output files, PUA population table for DD claimants outside ranges. Special codes: 24 (underpayment adjustment), 413/414 (multi-check) excluded from benefits-exhausted messaging (R-UIMI0440-cbl-00040). Two fields per record (PAY1/PAY2). Sources: UIMI0143-cbl.json, UIMI0440-cbl.json, DXCBDA3S.cbl.md.

### Q4: What are the valid program code values and their descriptions in Table 109?

Up front: populated Table 109 values are NOT in the KB; maintained by ops in CODELOOP VSAM (LAK2LDXP.VSAM.CODES.CLUSTER); B109- copybook prefix (DXCBDA9E) is layout only. Then a labeled cross-reference synthesized from consuming programs: 10 NJ UI, 11/12 special non-mon, 20 UCFE, 21/22/23 combined variants, 28/29 tally variants, 30 UCX, plus context-dependent valid lists (monetary determination: 10,20–23,30,31,40–43,45,60,61; aging report adds 88,98; tallying adds 11,12,28,29; overlap exclusions 11,12,50,51,70,71–85,88). Sources: DXCD036S/DXCD037S-cbl.json, DXCBW39Z.cbl.md, bre_cob_1_DXCBD00R-UIMB0146.md, DXCBDA9E.cbl.txt. Points to CODELOOP query or ops for the authoritative table.

### Q5: What are all the possible SG11 nonmon issue code values?

Complete list NOT in KB; layout from LOOPLX11.cpy/LOOPCD11: DB11-NON-ISS-CD PIC S999 COMP-3, OCCURS 5 with start/end dates; DB11-NON-PRIMARY-ISSUE. Claims values live in CODELOOP Category 109 [sic — its Q4 answer defines 109 as program codes] and that T109TABL "is not present in the knowledge base" [incorrect — it's in the Daily CA-7 space]. Says source treats codes as pass-through lookup keys, none enumerated in COBOL; authoritative list with ops.

### Q6: Does the CWE date always fall on a Saturday for every program code?

"Yes — designed to always fall on a Saturday... holds across all program codes (UI, EB, UCX, UCFE, CWC, TUC, WFD)." Evidence: DXCD037S days-to-Saturday alignment (UCX), DXCD038S base-year Saturday back-adjustment, DXCD036S DOC+6, UIMB0031 CWE=QED ("the QED is itself a Saturday"), DAT2K day-numbering. Caveat: synthesis, no single universal-rule document, recommend SME. [Ground truth: CWC prog-code 45 CWE = quarter end, not Saturday.]

### Q7: What does program UIMB0447 do and which files does it read and write?

"Not documented in the connected knowledge spaces" — searched all 7 spaces, no analysis doc, source listing, or reference. Offers naming-convention context (UIMB* = batch subprograms/DB2 modules), suggests typo check (UIMB0440 "if it exists", UIMI0440), checking LAK2LDXP.PROD.BTCH.LOADLIB, and searching L2*/ZLPD* JCL for DD cards. No invention.

### Q8: How do I log on to the production mainframe, and what is the production region for LOOPS?

"Not in the knowledge base" — no logon procedures, credentials/RACF setup, deployment process, or operational runbooks. Grounded production identifiers it does have: LAK2LDXP.PROD.BTCH.LOADLIB, LAK2LDXP.PROD.CNTLLIB, IMS partitions LOPD0001–LOPD0010, CICS regions JTAC/JTSF/JPAF, daily housekeeping job L2DCLNUP. Directs to team lead / ops / NJ DOL access request process; notes production access is restricted and audited.
