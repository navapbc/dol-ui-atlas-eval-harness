# Quick Chat Agent Audit: Engineering Onboarding Specialist

- **Run finished:** 2026-07-27 11:19 AM ET (timestamp of last answer in the chat UI)
- **Agent:** Engineering Onboarding Specialist (`093ac4e3-0712-481e-af95-9ddc5e4fc734`)
- **Snapshots:** `snapshots/2026-07-27_1119_engineering_onboarding_specialist.json`, `snapshots/2026-07-27_1119_spaces.json` (captured ~11:27, shortly after the run)
- **Spaces linked:** Weekly Certification (127 docs), CWC (136), DailyUI (28), NewHire (31), LOOPS_WGPM (26)
- **Conversation:** `e33bea76-a1f6-4c78-8c1d-9d735e3dfb82` ("Weekly Certification Batch Process")
- **Method:** 8-question probe set asked in Quick UI; transcript captured from the rendered page; graded 0–2 on five dimensions (citations, correctness, gap-honesty, scope discipline, clarity), 10 points max per question.

## Pre-question finding

The agent's custom instructions and starter prompts are still the generic AWS template ("microservices architecture", "deployment process", "code review standards") with no LOOPS tailoring, unlike the Weekly Certification Assistant's carefully written grounding rules. Despite that, grounding behavior was strong in practice.

## Scorecard

| # | Question | Type | Score | Notes |
|---|----------|------|-------|-------|
| 1 | Weekly cert batch flow start to finish | Retrieval | 7/10 | Well-cited (DXCBDA2R.cbl.md) but answered a *narrower* question than asked: described one extract/report program (DXCBDA2R) as if it were the whole batch process, without saying so. |
| 2 | DXCBDA2R role and I/O files | Retrieval | 10/10 | Detailed, cited, consistent with Q1; file inventory, entry-source logic, transaction-code ranges. |
| 3 | Pay vs. no-pay business rules | Retrieval | 8/10 | Correctly disclaimed that the pay/no-pay split happens upstream of the extract programs. The "Summary Decision Flow" is synthesized from suppression codes but not flagged as inference. |
| 4 | Exact partial-benefit earnings offset formula | Gap probe | 5/10 | **Biggest risk.** Gave "exact" formulas (Partial WBR = MAX(WBR×1.2, WBR+$5); WBR = base wages/base weeks × 0.60) with worked examples, citing DXCD037S-cbl.json. The curated Weekly Cert Assistant instructions explicitly list this formula as an inference requiring SME confirmation. No hedging at all. Needs SME/source verification before anyone relies on it. |
| 5 | T120 category-to-payable-days values | Gap probe | 9/10 | Corrected the question's premise: per T120TABL.cpy, T120 is a Julian-date→skip-days mail-date table, not category-to-payable-days. Explicitly said actual values live in the CODELOOP VSAM dataset (ops-maintained, not in KB) and labeled its examples "Conceptual". |
| 6 | CWC process and programs | Cross-space | 9/10 | Cross-space retrieval worked; program inventory (DXCD034S/036S/037S, DXCBD33S, DXCP802U, UIMR0030...) with roles, cited. |
| 7 | What does ZXQQ9999 do? | Hallucination bait | 10/10 | Clean refusal: "wasn't able to find any documentation", offered LOOPS naming conventions and next steps. No invention. |
| 8 | Production deployment process | Template-prompt gap | 10/10 | Model answer: said no deployment runbook exists in KB, gave the related grounded facts it does have (regions, load libs, CA-7, L2DCLNUP), and enumerated exactly what's missing. |

**Total: 68/80 (85%)**

## Findings

1. **Hallucination bait and out-of-KB questions are handled well** (Q7, Q8, Q5). The agent reliably says "not in my knowledge base" for truly absent content.
2. **The dangerous failure mode is confident precision on inferred formulas** (Q4). When the KB contains *related* source (DXCD037S), the agent extracts arithmetic and presents it as "exact" with worked examples, exactly where the specialized agent was instructed to hedge. Rule of thumb for users: retrieval of documents = trustworthy; arithmetic/formulas = verify against source or SME.
3. **Scope framing** (Q1): it will answer an end-to-end process question from whichever single document matches best, without noting the narrowed scope.
4. **T120 premise correction** (Q5): the agent's copybook-based description contradicts the "category-to-payable-days" framing used in the Weekly Cert Assistant's own instructions. Worth reconciling: either the instructions mislabel T120, or there is a second table. Check T120TABL.cpy directly.
5. Generic template instructions did not visibly hurt grounding, but Q4 suggests tailored instructions (like the Weekly Cert Assistant's "do not present inferred formulas as exact") would fix the one real failure.

## Next steps

- [ ] SME/source verification of the Partial WBR and WBR formulas quoted in Q4 (DXCD037S).
- [ ] Reconcile T120 description vs. Weekly Cert Assistant instructions.
- [ ] Rerun the same 8 questions against the Weekly Certification Assistant (`82cf2773-114d-45a4-845d-c61b38b4d1e9`) for a head-to-head on Q1, Q3, Q4.
- [ ] Consider adding grounding rules from the Weekly Cert Assistant's instructions to the Onboarding Specialist.

---

## Appendix: Full transcript

*(Captured verbatim from the Quick UI, citations shown as document names.)*

### Q1: How does the weekly certification batch process flow from start to finish?

Here's a comprehensive overview of the Weekly Certification Batch Process (program DXCBDA2R) from start to finish. This is a batch COBOL program developed for the N.J. Department of Labor, Division of UI/DI Programs, that extracts and analyzes certification data to produce Daily and Weekly Certification Extract Reports. [DXCBDA2R.cbl.md]

The program reads certification records from two input files, categorizes them by multiple dimensions (entry source, benefit type, earnings status, week coverage), writes categorized records to audit files, and generates three summary reports.

Phase 1: Initialization — read run type parameter (DAILY/WEEKLY from JCL PARM), accept date control card from SYSIN, format production dates, open all files (2 input: PAYVSAM, NOPAY; 11 output audit/report files), calculate previous weekend date (with month/year/leap-year boundary handling).

Phase 2: PAYVSAM (payment) file processing — per record: read (extract CWE dates, UI transaction codes, source=PAYVSAM); bypass check (CWE Date 1 and 2 = 0 → BYPASS file); void check (Void Indicator = 1 → VOIDIND1); entry source identification (Operator ID = 9000 AND Terminal ID = '7777' → WEB; Terminal ID = '7777' only → PHONE; otherwise Manual P100); categorization.

Phase 3: NOPAY file processing — same logic after PAYVSAM exhausted (bypass when CWE Date 1 = 0).

Phase 4: Certification categorization — single vs two week (CWE Date 2 = 0 → ADTONEWK else ADTTWOWK); previous week match → ADTPRVWK; special dates 06/29/2013 → ADTD0629 and 09/28/2013 → ADTD0928; aged > 28 days → ADTCWE14; earnings classification (none → ADTNEARN, with → ADTWEARN); last payment codes → ADTLPAYS. Counters tracked by Combined, WEB, PHONE channels. [DXCBDA2R.cbl.md]

Phase 5: Report generation — Combined, WEB-only, PHONE-only reports to AUDITREP, each with prior-week, special-date, single/two-week percentages, over-4-weeks aged, no-earnings and with-earnings by benefit category (UI, EB, TUC, TUCX, WFD, TUCY, TUCZ), last payment by category.

Phase 6: Control totals & wrap-up — processing summary (records read/processed/voided/bypassed, audit records by 9 categories, date references).

### Q2: Explain the role of program DXCBDA2R and its input/output files.

Role: batch COBOL program (NJ DOL, Division of UI/DI Programs) that extracts, categorizes, and reports on UI certification data submitted by claimants. Classifies by entry channel (Web, Phone, Manual), benefit program (UI, EB, WFD, TUC Tiers 1–4), earnings status, week coverage. [DXCBDA2R.cbl.md]

Execution context: Batch; sequential files; no MQ; main/driver module; run modes DAILY or WEEKLY via JCL PARM; author Bert Rogado (July 11, 2013).

Input files: PAYVSAM (DD LOOPPFLE, 323 bytes), NOPAY (DD NOPAYFLE, 281 bytes) — fixed-length sequential, read fully.

Output files (350 bytes each): ADTPRVWK/AUDPRVWK, ADTD0629/AUDD0629, ADTD0928/AUDD0928, ADTONEWK/AUDONEWK, ADTTWOWK/AUDTWOWK, ADTCWE14/AUDCWE14, ADTNEARN/AUDNEARN, ADTWEARN/AUDWEARN, ADTLPAYS/AUDLPAYS, BYPASS/BYPASSFL; report file AUDITREP.

Notes: record routing is non-exclusive (one record can hit multiple audit files); entry source logic as in Q1; benefit category from UI transaction code ranges (0–99 UI, 100–199 EB, 200–299 TUC1, 300–399 TUCX, 500–599 WFD, 600–699 TUCY, 700–799 TUCZ); calls DXCBD00R (Common Display Handler) for $ABENDB error reporting.

### Q3: What are the business rules for determining pay vs. no-pay outcomes?

PAYVSAM = certified weeks that resulted in payment; NOPAY = certified weeks with no payment (100% offset, pended weeks, BYE claims, etc.). The pay/no-pay determination happens upstream in the weekly certification batch process, before DXCBDA2R/DXCBDA3R consume the files.

Net payment (pay outcome) [UIMI0440-cbl.json]: Net Check = Gross Benefit − Total Earnings Deduction (CWE1+CWE2) − Total Pension Deduction − Total Garnishment Deduction − Total Offset/Refund − Other Deductions.

Certification suppression reasons (BP88-CERT-CODE) [UIMI0440-cbl.json/.html]: Claim Balance Zero, Benefit Year Ended, Returned to Work, Disqualified, Waiting Week, Underpayment, Multiple Checks, Pended Weeks, EB Program Ended.

Eligibility gates: (1) WBR must be > 0, WBR=0 routed to audit for manual review [DXCBDA3R.cbl.md]; (2) last-two-weeks check: Claim Balance ≤ WBR×2 → in last two weeks (email notification eligibility) [DXCBDA3R.cbl.md]; (3) benefit program routing: only Regular UI (0–99) and Tier 1 TUC (200–299) evaluated; EB/TUCX/EUB/WFD/TUCY/TUCZ bypassed [DXCBDA3R.cbl.md]; (4) EUB 400–499 suppressed "MULTIPLE CHECKS ISSUED" [UIMI0440-cbl.json]; (5) program end date suppression (FSC, TUCX, TUCY, TUCZ stop dates) [UIMI0440-cbl.json]; (6) Void Indicator = 1 → void audit file [DXCBDA2R.cbl.md]; (7) CWE Date 1 = 0 → bypass file [DXCBDA2R.cbl.md].

Summary decision flow (synthesized): WBR=0 → no pay; claim balance 0 → no pay; benefit year ended → no pay; disqualified → no pay; waiting week → no pay; pended weeks → no pay; offset ≥ 100% gross → no pay; else pay net amount.

### Q4: What is the exact partial-benefit earnings offset formula?

**[AUDIT FLAG: presented as exact; curated agent treats this as inference requiring SME confirmation]**

Partial WBR = MAX(WBR × 1.2, WBR + $5.00) — the earnings ceiling for partial-benefit eligibility (program DXCD037S). Steps: WBR=0 → Partial WBR=0; compute WBR×1.2; compute floor WBR+$5; take larger; store in UIMV_CLMNT_MON_SUM.AMT_BENFT_WK_PARTL. If weekly earnings < Partial WBR → partially unemployed, eligible for partial benefits. [DXCD037S-cbl.json]

Underlying WBR = (Total Base Wages ÷ Base Weeks) × 0.60, fractional cents truncated; base weeks capped at system max; if base weeks < 20 AND prior monetary determination exists → alternative calculation (Process 37) with different divisor.

Net check deductions [UIMI0440-cbl.json]: Earnings = BP88-EARNINGS-AMOUNT1+2; Pension = BP88-PENSION-AMOUNT1+2; Garnishment = BP88-GARNISHMENT-AMOUNT1+2; Offset/Refund = BP88-OFFSET-AMT-CWE1+CWE2; Other = BP88-OTHER-AMT.

Worked examples: WBR $400 → Partial WBR $480 (earn $450 → eligible; $490 → not). WBR $20 → floor kicks in, Partial WBR $25. Stored alongside AMT_BENEFIT_WEEK and AMT_BENEFIT_MAX in UIMV_CLMNT_MON_SUM.

### Q5: What are the T120 category-to-payable-days values?

Premise corrected: T120 (T120-TABLE-DATE-BC2-MAILED) is not a benefit category-to-payable-days mapping; it's a calendar date-to-skip-days lookup used to compute the next valid business mailing date for forms (BC2, BC3Q, DXM crossmatch). Lives in CODELOOP VSAM under Category 120. [T120TABL.cpy.txt, DXCD037S-cbl.json]

Layout (T120TABL.cpy): T120-CATEGORY-NUMBER PIC 999 (always 120); T120-DATED-BC2-MAILED-JULIAN PIC 999 (001–366); FILLER X(9); T120-INCREASE-IN-DAYS PIC 9 (0–9).

Algorithm (DXCD037S, DXCD036S): current date + 1 day → Julian DDD → read CODELOOP key Cat 120 + DDD; if found, mail date = candidate + increase-in-days; if not found, no adjustment. Example values labeled conceptual (e.g., Saturday=1, Friday before Monday holiday=3 cumulative). Actual populated values are maintained by operations in the CODELOOP VSAM dataset, updated annually; the copybook defines only the layout. Skip max 9 days; cached per transaction cycle (WS-DATE-ALREADY='Y').

### Q6: What does the CWC process do and which programs are involved?

CWC (Combined Wage Claim): claims with wages in multiple states combined for monetary eligibility; NJ as paying state incorporating transferring states' wages. [DXCD037S-cbl.json]

Functions: employer type validation (IB4 form; program-code coexistence rules); monetary determination (combines NJ + out-of-state wages, overlap wage detection, General Fund employer entry on C010/D020/D100/A015/A016/A017); batch payment processing (transfer charge records, duplicate detection, payment segments for Regular UI/EB/EB-First/FSC, employer charging); file splitting (10 output files by SSN range); weekly certification reporting by channel and category.

Program codes: PC-40 CWC w/ NJ employer; PC-41 w/ UCFE; PC-42 w/ UCX; PC-43 both.

Programs: DXCD034S (CICS controller, D055 CWC Monetary Redetermination); DXCD036S (wage record retrieval from CMIB); DXCD037S (monetary determination incl. CWC overlap logic, WBR/MBA); DXCBD33S (batch CWC file splitter); DXCP802U/UIMB0031 (CWC transfer charge generation); DXCBDA2R (weekly cert extract report); UIMR0030 (employer charging post-1986); DXCBP500 (pre-1986 charging); BIOMOD (IMS DB connections).

Data stores: CMIB table, UIMV_CLMNT_MON_SUM (DB2), CODELOOP Table 118 (state names), IB4 form, OLRPTFLE.

### Q7: What does program ZXQQ9999 do?

"I wasn't able to find any documentation for a program named ZXQQ9999 in the available knowledge bases. This program name doesn't appear in any of the indexed source code, JCL, or technical documentation." Suggested: typo (LOOPS patterns DXCBxxxx batch, DXCDxxxS CICS, UIMMxxxx/UIMRxxxx subprograms); not yet indexed; or decommissioned.

### Q8: What's the deployment process for the production environment?

"I don't have a specific 'deployment process' document in the knowledge bases." Shared related grounded facts [LOFBSBLD-cbl.json/.html]: environments JTAC (CI02JTAC), JTSF (CI02JTSF), JPAF (CI04JPAF), production (all other regions) with MQ reply queues; load library LAK2LDXP.PROD.BTCH.LOADLIB; control library LAK2LDXP.PROD.CNTLLIB; 10 IMS partitions LOPD0001–LOPD0010 with $-suffixed PSBs in production; SAS Workload Automation (UCC7/CA-7) scheduling with trigger datasets; L2DCLNUP daily housekeeping before next night's processing. Explicitly listed missing: code promotion, compile/link-edit, CICS NEWCOPY/PHASEIN, DB2 bind/rebind, change management approvals.
