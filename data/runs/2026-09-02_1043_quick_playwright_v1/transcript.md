# 2026-09-02_1043_quick_playwright_v1

- **Backend:** quick (transport: playwright)
- **Bank:** v1 (`question_sha256` 5850e95bbbd2…)
- **Agent:** engineering_onboarding_specialist (`30b0228b-b58a-43ad-818b-2f262f11108f`)
- **Conversation:** `4d6ed1fc-6bc4-4978-94c0-790fdd1c5425`
- **Model:** Advanced
- **Started:** 2026-09-02 10:36
- **Finished:** 2026-09-02 10:43
- **Status:** complete
- **Questions asked:** 8, answered: 8

## v1-Q1

**Q:** How does the weekly certification batch process flow from start to finish?

**A** (10:37):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

Great question. The weekly certification process in LOOPS spans both real-time (CICS) processing and batch reporting/extract processing. I found documentation on several key programs involved. Here's a synthesized overview — note that this is assembled from multiple source documents, and the full end-to-end process may include upstream and downstream steps not fully covered in the knowledge base.

Phase 1: Certification Intake (Real-Time / CICS)

Claimants submit their weekly certifications through one of three channels :
LOAI021S-cbl.json

WEB — Operator ID = 9000, Terminal ID = '7777'
PHONE (IVR) — Terminal ID = '7777' only
Manual (P100) — Staff-entered via CICS terminal

The CICS program LOAI021S handles the online weekly certification payment processing. Key steps include :
LOAI021S-cbl.json

Transaction Routing — Accepts transactions P100, P102, P110, P120. Invalid transaction codes redirect the user to the prompt screen via transaction LOAI.
Field Initialization — Zeroes out 11 working fields (WBA week 1/2, CWE dates, pensions, 50% amounts, remaining claim balance, etc.).
Earnings vs. PWBR Comparison — Compares each week's earnings against the Partial Wage Benefit Rate:
Less than PWBR → claimant qualifies for partial benefit (L)
Equal to PWBR → indicator set to E
Greater than PWBR → no benefit for that week (G), with message "EARNINGS GREATER THAN PWBR" displayed
Benefit Calculations — Performs validations, benefit calculations, garnishment computations, and tax withholding determinations.
Session Preservation — Returns control via CICS transaction LO4U with the full communication area preserved.
Phase 2: Batch Payment Transfer (CICS Batch)

Program DXCP025S handles the batch payment transfer step :
DXCP025S-cbl.json

Extension Balance Capture — For TUC extension programs (TUCX/TUCY/TUCZ), the system writes remaining balance, potential weeks, and weeks paid to temporary storage before check printing.
Bi-Weekly Schedule Verification — For EC (Extended Compensation) claimants, verifies the correct bi-weekly certification schedule. Off-schedule claimants get their second CWE date suppressed.
Receipt CWE Date Copy — Copies the receipt certification week ending date to the payment record.
Database Release — Terminates the IMS PSB connection (without end-of-task) to free resources.
Transfer to Check Printing — XCTL to program DXCP026S for check printing and charging.
Phase 3: Batch Extract and Reporting

Program DXCBDA2R is the batch extract/report program that processes the output of the certification cycle.
DXCBDA2R.cbl.md
DXCBDA2R.cbl.md
 Its 20-step flow:

Initialization — Reads run type (DAILY or WEEKLY), accepts date control card, formats production dates
Previous Weekend Date Calculation — Subtracts 7 days from the week-ending date (with month/year/leap-year boundary handling)
PAYVSAM File Processing — Reads each payment certification record sequentially:
Void handling — Records with Void Indicator = 1 → written to VOIDIND1 audit file
Bypass handling — Records where both CWE Date 1 and CWE Date 2 = 0 → written to BYPASS file
NOPAY File Processing — Reads no-payment certifications with same categorization logic
Entry Source Classification — Classifies each record as WEB, PHONE, or Manual P100
Certification Categorization — Each valid record is classified by:
Single-week vs. two-week (based on CWE Date 2)
Previous-week match
Aged certification (>28 days old)
Earnings status (no earnings vs. with earnings)
Benefit category (UI 0–99, EB 100–199, TUC 200–299, TUCX 300–399, WFD 500–599, TUCY 600–699, TUCZ 700–799)
Last payment detection (codes 13/14 within each series)
Report Generation — Three summary reports are produced:
Combined (all channels)
WEB-only
PHONE-only
Control Totals Display — Shows PAYVSAM/NOPAY records read, processed, voided, bypassed, and audit records written by category
Phase 4: Void / Decertification (As Needed)

Program WWCP042S handles void and batch decertification processing :
WWCP042S-cbl.json

Routing decision — Check serial number = 7 with void indicator and link flag 'Y' → batch decertification; void indicator alone → online void; otherwise → redeposit
Batch decertification — Voids all CWE weeks, resequences payment table by CWE date, reloads payments from DB, reverses charges, updates LOOPPAY/OPIDPAY/DB2 tax records
Important Caveats
This description is synthesized from multiple knowledge base sources (DXCBDA2R.cbl.md, LOAI021S-cbl.json, DXCP025S-cbl.json, WWCP042S-cbl.json). Each covers its own program's role; I have assembled them into a process flow.
The real-time capture (IVR, CICS web front-end) and money movement steps (check print, direct deposit, Treasury) are related but separately documented and may not be fully represented here.
The CA-7 job schedule that orchestrates these batch steps (job names, triggers, dependencies) is available in the Daily CA-7 space but was not the focus of this search.
Would you like to explore further?

CA-7 job schedule for weekly certification

More detail on the DXCBDA2R extract program

LOAI021S payment processing details

Run a full Research analysis on this topic

_Citations:_
- Citation 1
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 5

## v1-Q2

**Q:** Explain the role of program DXCBDA2R and its input/output files.

**A** (10:38):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

DXCBDA2R is a well-documented batch COBOL program written by Bert Rogado (dated July 11, 2013) for the N.J. Department of Labor, Division of UI/DI Programs. Its purpose is to extract and analyze weekly certification data, producing Daily or Weekly Certification Extract Reports. Here is a comprehensive breakdown from the source documents (DXCBDA2R.cbl.md and DXCBDA2R.md).
DXCBDA2R.cbl.md
DXCBDA2R.md

Program Role

DXCBDA2R is a main/driver batch module that reads certification records from two input files, categorizes each record along multiple dimensions, writes categorized records to audit extract files, and generates three summary reports. It does not access any database or MQ — it operates exclusively on sequential flat files.
DXCBDA2R.cbl.md

The program supports two run modes controlled by a JCL PARM value: DAILY (default) or WEEKLY, which only affects the report headers/titles.
DXCBDA2R.cbl.md

Input Files (2)
DXCBDA2R Input Files

Logical Name

	

Physical Dataset Pattern

	

Description


PAYVSAM	LAK2LDXP.JOBNAMES.PAYVSAM.DTL	Payment certification records — certifications where a benefit payment was issued. Contains CWE dates, UI transaction codes, earnings amounts, operator/terminal IDs, and a Void Indicator field.
NOPAY	LAK2LAGP.JOBNAMES.NOPAY.DTL	No-payment certification records — certifications where no benefit payment was issued (e.g., excess earnings, disqualification). Contains the same categorization fields but uses NOPAY-prefixed field names.
View more

Additionally, a SYSIN control card is required at runtime containing the daily processing date (B040-DAILY-DATE) and the week-ending date (B040-WEEK-ENDING-DATE), both in MMDDCCYY format.
DXCBDA2R.cbl.md

Output Files (12)

The program produces 9 category-specific audit extract files, 2 exception audit files, and 1 summary report file:

DXCBDA2R Output Files

Logical Name

	

Purpose

	

Records Written When...


ADTPRVWK	Previous Week Audit	Single-week cert where CWE Date 1 matches the calculated previous weekend date
ADTD0629	06/29/2013 Audit	Single-week cert where CWE Date 1 = 06/29/2013
ADTD0928	09/28/2013 Audit	Single-week cert where CWE Date 1 = 09/28/2013
ADTONEWK	Single Week Audit	Certification has CWE Date 2 = 0 (single-week)
ADTTWOWK	Two Week Audit	Certification has CWE Date 2 > 0 (two-week)
ADTCWE14	Over 4 Weeks Audit	Single-week cert where CWE Date 1 is >28 days before the run date
ADTNEARN	No Earnings Audit	Both Week 1 and Week 2 earnings amounts = 0
ADTWEARN	With Earnings Audit	At least one earnings amount > 0
ADTLPAYS	Last Payment Audit	UI transaction code matches a last-payment code (e.g., 13/14, 113/114, etc.)
VOIDIND1	Void Audit	PAYVSAM record with Void Indicator = 1
View more
Record Classification Logic

Each valid record goes through a multi-dimensional classification. The program categorizes every certification along these axes:

Entry Source — WEB (Operator ID = 9000 + Terminal ID = '7777'), PHONE (Terminal ID = '7777' only), or Manual P100 (all others)
Week Coverage — Single-week (CWE Date 2 = 0) vs. Two-week (CWE Date 2 > 0)
Certification Age — For single-week certs: >28 days old = "over 4 weeks"
Earnings Status — No earnings (both weeks zero) vs. With earnings (at least one non-zero)
Benefit Category — Based on UI Transaction Code ranges: UI (0–99), EB (100–199), TUC (200–299), TUCX (300–399), WFD (500–599), TUCY (600–699), TUCZ (700–799)
Last Payment — Transaction codes 13/14 within each series (e.g., UI: 13–14, EB: 113–114, etc.)
Record Processing Decision Flow

For each record read, the program follows this decision path :
DXCBDA2R.cbl.md

CWE Date 1 = 0? → Write to BYPASS, increment bypass counter, skip to next record
(PAYVSAM only) Void Indicator = 1? → Write to VOIDIND1, increment void counter, skip to next record
Classify entry source → WEB / PHONE / Manual P100
CWE Date 2 = 0? (single-week path):
Check previous weekend date match → ADTPRVWK
Check special date 06/29/2013 → ADTD0629
Check special date 09/28/2013 → ADTD0928
Check if >28 days old → ADTCWE14
Write to ADTONEWK
CWE Date 2 > 0? → Write to ADTTWOWK
Earnings check → Write to ADTNEARN or ADTWEARN with benefit category counting
Last payment check (both Week 1 and, for two-week certs, Week 2) → ADTLPAYS
Reports Produced

After all records from both files are processed, three summary reports are written sequentially to AUDITREP :
DXCBDA2R.cbl.md
DXCBDA2R.md

Combined (All Channels) — Totals across WEB + PHONE + Manual
WEB-Only — Using WB- prefixed counters
PHONE-Only — Using PH- prefixed counters

Each report includes: previous-week count, special-date counts (06/29/2013, 09/28/2013), single-week vs. two-week counts with percentages, over-4-weeks count, no-earnings by benefit category, with-earnings by benefit category, and last-payment by benefit category.

Control Totals

At program end, a control totals summary is displayed to the console showing :
DXCBDA2R.cbl.md
DXCBDA2R.md

PAYVSAM records read, NOPAY records read, total read
Records processed, voided, and bypassed
Audit records written by category (previous week, special dates, single/two-week, over-4-weeks, no-earnings, with-earnings, last-payment)
Important Caveats
Note on special dates: The hardcoded checks for 06/29/2013 and 09/28/2013 appear to be historical tracking from when the program was originally written (July 2013). These may produce zero counts in current production runs but the checks remain in the code.
DXCBDA2R.cbl.md
Note on NOPAY void handling: Void indicator checking applies only to PAYVSAM records — the NOPAY file has no void-indicator evaluation.
DXCBDA2R.cbl.md
This description covers the DXCBDA2R program itself. The upstream jobs that produce the PAYVSAM and NOPAY input files, and the downstream consumers of the audit extract files and AUDITREP report, are documented separately in the CA-7 job schedules.
Would you like to explore further?

Upstream job dependencies for DXCBDA2R

Record layout details for input files

CA-7 scheduling for DXCBDA2R

_Citations:_
- Citation 1
- Citation 2
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 2
- Citation 1
- Citation 2
- Citation 1
- Citation 1

## v1-Q3

**Q:** What are the business rules for determining pay vs. no-pay outcomes?

**A** (10:39):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

This is a rich topic. The pay vs. no-pay determination in LOOPS involves a multi-layered decision chain that spans several programs. Here's a synthesized summary drawn from multiple documented source programs. Note: this is a synthesis across multiple modules — I'll cite each source. The arithmetic formulas for PWBR and WBA are confirmed against source code in DXCD037S (as noted in the grounding rules) and corroborated across the programs below; the earnings offset arithmetic in UIMI0440 is inferred and should be validated with an SME.

1. The Core Gate: Earnings vs. PWBR (Partial Weekly Benefit Rate)

The single most important rule controlling pay vs. no-pay is the PWBR comparison. The PWBR formula is confirmed across multiple programs:

PWBR = the greater of (WBR × 1.20) or (WBR + $5.00)

This is documented in LOIGSBLD-cbl , LOAASBLD-cbl , DXCD053S-cbl , WWCD053S-cbl , and DXCP028S-cbl.
LOIGSBLD-cbl.json
LOAASBLD-cbl.json
DXCD053S-cbl.json
WWCD053S-cbl.json
DXCP028S-cbl.json

Earnings ≥ PWBR → No pay for that week. The WBA is set to zero and the transaction code is set to an overpayment code (e.g., 25 for regular UI, 125 for EB, 225 for FSC, etc.)
Earnings < PWBR → Pay (partial benefit). The WBA = PWBR − Earnings, capped at the full WBR
2. The Benefit Calculation Chain (When Pay Is Issued)

When earnings are below PWBR, the payment is computed in stages:

WBA (Weekly Benefit Amount) = PWBR − Earnings
WBA cap: WBA cannot exceed the claimant's full WBR
AWBA (Adjusted Weekly Benefit Amount) = WBA − Pension Deduction. If pension ≥ WBA, AWBA = 0
After AWBA, garnishments and tax withholding are applied to arrive at the net check amount
3. Pre-Payment Validation: "Dirty Claim" Flags → Pend (No Pay)

Before a payment is issued, the system runs certification validation checks. If any check fails, the claim is flagged as "dirty" (DIRTY-CLAIM = 'Y'), which pends the payment (holds it for adjudication = no immediate pay). The documented dirty-claim triggers include:

Documented Dirty Claim Triggers (No-Pay / Pend Conditions)

Condition

	

Reason Code

	

Remarks Code

	

...


Week 1 earnings ≥ PWBR but Week 2 earnings < PWBR and > 0	01	EARNS>PWBR	...
Week 1 partial earnings (0 < earns < PWBR) with hours > 32	14	PTHRS>32	...
Both weeks partial earnings < PWBR but hours > 32 in both	01	EARNS>PWBR	...
Week 1 zero earnings, Week 2 partial earnings with hours > 32	14	PTHRS>32	...
Return-to-Work date falls within Week 1 certification period	02	RTW DATE	...
Return-to-Work date equals Week 2 begin date	02	RTW DATE	...
Vacation or holiday pay reported	(flagged dirty)	(manual review)	...
Fraud flag set (No-Pay Fraud Flag = Y)	(blocked)	(fraud)	...
View more

Sources:

4. No-Pay Record Types

When a no-pay outcome occurs, the system classifies the reason using no-pay record types as documented in DXCP025S-cbl :
DXCP025S-cbl.json

Record Type '2' — Payment is pended (held for adjudication). This takes priority over other no-pay classifications.
Other no-pay types are assigned based on earnings-vs-PWBR outcomes, disqualifications, or certification answer conflicts.
5. Return-to-Work Date Conflict → No-Pay

A specific no-pay trigger occurs when the claimant provides a Return-to-Work (RTW) date that conflicts with the certification period :
LOIDSBLD-cbl.json

If the RTW date falls within Week 1 (RTW ≥ Week 1 begin date AND RTW ≤ Week 1 CWE date) → WS-NO-PAY-FLAG = 'Y', reason code 02, remark RTW DATE
If the RTW date equals the Week 2 begin date → Same no-pay flags are set
If the RTW date is not provided or does not fall within either period → No RTW-related flags are set
6. Pended Payment (Held for Adjudication)

A payment can also be pended (effectively no-pay until released) when :
LOAK025S-cbl.json

POT-PAY-PEND = '1' — Payment is held pending review
System pend (dirty reason 0000000005) → Claimant receives Message ID 03 ("payment held pending review")
Adjudication pend (any other dirty reason) → Message ID 02 ("flagged for adjudication review")
7. Remaining Benefit Amount Exhausted → No (Further) Pay

When the remaining benefit balance (CLMREMO) reaches zero, the system evaluates whether the claimant may be eligible for an extension program :
LOAI021S-cbl.json

TUC extension — checked against Table 157 (CODELOOP) if UI pay code ≤ 199 and CWE+1 falls within the TUC entitlement period
TUCX extension — checked against Table 257 if UI pay code > 199
The system enforces a 21-day window (CWE date + 21 days must not have passed), with offices 997 and 999 exempt
If no extension applies → Message: REMAINING BENEFIT AMOUNT IS 0
8. Routing of Dirty Claims

When a claim is flagged dirty, it is routed for adjudication based on the type of issue :
LOIDSBLD-cbl.json

Address change only → Routed to RCC Center (Priority 1, lighter review)
Address change + other issues → Routed to Adjudication Center (Priority 2)
Other issues only (no address change) → Routed to Adjudication Center (Priority 3)
No dirty reasons → Claim proceeds as clean — no routing required
Summary Decision Flow

At a high level, the pay/no-pay decision follows this logic:

Is earnings ≥ PWBR for this week? → No pay (WBA = 0)
Is there a dirty-claim condition? (RTW conflict, hours > 32 with partial earnings, vacation pay, fraud flag) → Pend (no immediate pay)
Is remaining benefit balance exhausted? → No pay (check for extension eligibility)
Otherwise → Compute WBA = PWBR − Earnings, apply pension offset → AWBA, apply garnishments/tax → Net check
Important Caveats
This synthesis is drawn from multiple CICS and batch modules: LOIGSBLD-cbl, LOIDSBLD-cbl, LOAASBLD-cbl, LOAI021S-cbl, DXCP025S-cbl, DXCD053S-cbl, DXCBD53S-cbl, WWCD053S-cbl, WWCP042S-cbl, DXCP028S-cbl, and LO9JC23R-cbl. Each handles a specific slice of the decision chain.
The earnings offset arithmetic (how earnings deductions are calculated in UIMI0440) is not fully documented in the knowledge base — that calculation is an inference and should be confirmed with an SME.
Additional no-pay conditions may exist in programs outside the current knowledge base coverage (e.g., disqualification holds from nonmonetary adjudication, school attendance issues).
What would you like to explore next?

Deep dive into PWBR/WBA calculation

Program-level dirty claim processing map

Pended payment release process

Full payment processing pipeline

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 5
- Citation 10
- Citation 11
- Citation 12
- Citation 13
- Citation 11

## v1-Q4

**Q:** What is the exact partial-benefit earnings offset formula?

**A** (10:40):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

The retrieved sources confirm the formula with excellent cross-program consistency. Here is the exact partial-benefit earnings offset formula as verified against source code:

Step 1: Compute the PWBR (Partial Weekly Benefit Rate)

The PWBR is the earnings threshold — the maximum a claimant can earn before losing all benefits for the week. It is the greater of two candidates:

PWBR = MAX( WBR × 1.20 , WBR + $5.00 )

The code first computes WBR × 1.2, then computes WBR + $5.00, and if the second value is greater, it overrides the first.
WWCA041S-cbl.json
DXCD072S-cbl.json

Why the $5 floor? For low-wage claimants whose WBR is $25 or less, 20% of WBR would be less than $5. The WBR + $5 alternative guarantees a minimum earnings disregard of at least $5 above the WBR.
DXCD072S-cbl.json

Crossover point: WBR × 1.2 = WBR + $5 → 0.2 × WBR = $5 → WBR = $25. Below $25 WBR, the + $5 method wins; at $25 and above, the × 1.2 method wins or ties.

Step 2: Compare Earnings to PWBR
If Earnings ≥ PWBR → WBA = 0 (no benefit payable for that week)
If Earnings < PWBR → proceed to Step 3
Step 3: Compute the Raw WBA

WBA = PWBR − Earnings

This is the preliminary benefit amount before caps.
DXCD054S-cbl.json
WWCD072S-cbl.json
DXCD053S-cbl.json
LO9JC23R-cbl.json

Step 4: Apply the WBR Cap

If WBA > WBR → WBA = WBR

The WBA can never exceed the claimant's established Weekly Benefit Rate.
WWCA041S-cbl.json
WWCD072S-cbl.json

Step 5: Apply the Zero Floor

If WBA < 0 → WBA = 0

A negative WBA (which would occur if earnings exceed PWBR during a rounding or recalculation scenario) is floored at zero.
DXCD072S-cbl.json
WWCD072S-cbl.json

Step 6: Apply the Remaining Balance Cap

If WBA > Claim Remaining Balance → WBA = Claim Remaining Balance

The WBA cannot exceed the remaining UI balance (DBWS-BAL-CLAIM-REM) or, for EB payments, the EB remaining balance (DBWS-AMT-REM-EB).
DXCD072S-cbl.json

Step 7: Pension Offset → AWBA

AWBA = WBA − Pension Amount

If the claimant receives pension income, it is subtracted dollar-for-dollar to arrive at the Adjusted Weekly Benefit Amount (AWBA).
DXCD072S-cbl.json
WWCD072S-cbl.json

Complete Formula (Pseudocode)

LOOPS Partial-Benefit Earnings Offset Formula – Pseudocode


─── INPUTS ───
  WBR       = claimant's Weekly Benefit Rate
  EARNINGS  = claimant's reported weekly earnings
  PENSION   = claimant's weekly pension amount
  BAL_REM   = remaining claim balance (UI or EB)

─── STEP 1: PWBR ───
  PWBR_A  = WBR × 1.20
  PWBR_B  = WBR + $5.00
  PWBR    = MAX(PWBR_A, PWBR_B)

─── STEP 2: EARNINGS GATE ───
  IF EARNINGS ≥ PWBR THEN
      WBA = 0                          ── no benefit payable
      EXIT
  END-IF

─── STEP 3: RAW WBA ───
  WBA = PWBR − EARNINGS

─── STEP 4: WBR CAP ───
  IF WBA > WBR THEN
      WBA = WBR
  END-IF

─── STEP 5: ZERO FLOOR ───
  IF WBA < 0 THEN
      WBA = 0
  END-IF

─── STEP 6: BALANCE CAP ───
  IF WBA > BAL_REM THEN
      WBA = BAL_REM
  END-IF

─── STEP 7: PENSION OFFSET ───
  AWBA = WBA − PENSION

─── OUTPUT ───
  AWBA = Adjusted Weekly Benefit Amount (net payable)

Worked Example
Table

Input

	

Value


WBR	$400
Earnings	$200
Pension	$0
Claim Remaining	$3,000
View more
PWBR = MAX(400 × 1.2, 400 + 5) = MAX($480, $405) = $480
Gate: $200 < $480 → proceed
Raw WBA = $480 − $200 = $280
WBR cap: $280 ≤ $400 → no cap needed
Floor: $280 ≥ $0 → OK
Balance cap: $280 ≤ $3,000 → no cap needed
AWBA = $280 − $0 = $280 payable
Verification Status

This formula is confirmed against the following source programs:

WWCA041S-cbl — the most complete single-module rendition (WBR × 1.2, WBR + $5 comparison, earnings gate, WBA = PWBR − earnings, WBR cap)
DXCD072S-cbl — paragraph 4440-CALC-WBA (WBR × 1.2, WBR + $5 floor, WBA = PWBR − earnings, cap at WBR, floor at zero, cap at remaining balance)
WWCD072S-cbl — identical logic across multiple key functionalities
DXCD053S-cbl / WWCD053S-cbl — EB payment calculation path (same PWBR/WBA formula)
DXCP043S-cbl — effective PWBR as higher of WBR × 1.2 or WBR + $5
DXCP021S-cbl — Available Amount = PWBR − earnings
DXCP028S-cbl — PWBR = WBR + (WBR × 0.20)
LOAI021S-cbl — CICS weekly cert screen (same PWBR gate + WBA = PWBR − earnings, capped at WBR)
LO9JC23R-cbl — batch certification (WBA = PWBR − earnings, capped at WBR)
DXCD054S-cbl — payment recalculation (WBA = PWBR − earnings)

This is one of the most consistently implemented formulas in the LOOPS codebase — the same arithmetic appears in at least 10 independent programs across both CICS and batch modules.

_Citations:_
- Citation 1
- Citation 2
- Citation 2
- Citation 4
- Citation 5
- Citation 6
- Citation 7
- Citation 1
- Citation 5
- Citation 2
- Citation 5
- Citation 2
- Citation 2
- Citation 5

## v1-Q5

**Q:** What are the T120 category-to-payable-days values?

**A** (10:41):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

The knowledge base documents the structure of Table T120 but not the populated values — those live outside the knowledge base entirely, as explained below.

What the Knowledge Base Documents About T120

T120 is a mailing-date / business-day calendar table, not a "payable-days" table (the knowledge base has no process by the name "category-to-payable-days"). Its purpose is to determine how many additional days to add to a candidate mailing date so that mailings land on valid business days, skipping weekends and holidays.

T120 Record Layout

From the copybook T120TABL.cpy
T120TABL.cpy.txt
T120TABL.txt
 :

T120TABL.cpy – Record Layout


01  T120-TABLE-DATE-BC2-MAILED.
    02 T120-CATEGORY-NUMBER           PIC 999.
    02 T120-DATE-MAILED-KEY.
      04 T120-DATED-BC2-MAILED-JULIAN PIC 999.
      04 FILLER                       PIC X(9).
    02 T120-INCREASE-IN-DAYS          PIC 9.

How the Key Works
T120-CATEGORY-NUMBER — always set to 120 by every consuming program
T120-DATED-BC2-MAILED-JULIAN — the 3-digit Julian day-of-year (001–366) of the candidate mailing date
T120-INCREASE-IN-DAYS — a single digit (PIC 9, values 0–9) representing the number of additional days to add to reach the next valid business mailing date
How Programs Use It

The pattern, confirmed across multiple batch and CICS programs, is:

Compute a candidate mailing date (typically today + 1 day)
Convert it to Julian day-of-year
Look up T120 with category 120 + that Julian day
If T120-INCREASE-IN-DAYS = 0 → the candidate date is already a valid business day; use it as-is
If T120-INCREASE-IN-DAYS > 0 → add that many days to the candidate date to skip the weekend or holiday

This is documented in programs including DXCC097S (CICS ERI group scheduling) , DXCC031S (CICS) , DXCC090S (CICS) , DXCC098S (CICS) , UIMI0055 (batch WFD notice printing) , UIMI0037 (batch) , DXCB293R (batch) , and LOW2C226 (CICS).
UIMI0055.md
DXCC097S-cbl.json
DXCC031S-cbl.json
DXCB293R.md
DXCC090S-cbl.html
DXCC098S-cbl.json
UIMI0037.txt
LOW2C226-cbl.json

Where the Actual Values Live

The populated T120 day-by-day values (the actual mapping of each Julian date to its increase-in-days number) are not in the knowledge base. The copybook T120TABL.cpy defines only the record layout. The values themselves are operations-maintained in the CODELOOP VSAM dataset and are updated (typically annually) by the operations team to reflect the coming year's weekend and holiday calendar.

To get the current T120 values, you would need to:

Query the CODELOOP VSAM file on the mainframe (category 120, keys 001–366)
Or contact the operations / production support team that maintains the yearly business-day calendar
Would you like to explore a related topic?

Walk through T120 usage in a specific program (e.g., DXCC097S or UIMI0055)

Learn about other configuration tables in the CODELOOP VSAM

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 5
- Citation 6
- Citation 7
- Citation 8
- Citation 9
- Citation 10

## v1-Q6

**Q:** What does the CWC process do and which programs are involved?

**A** (10:42):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

Important note on the name "CWC": The knowledge base documents two expansions for the abbreviation "CWC":

Combined Wage Claim — used in DXCP800S, DXCD037S, DXCD051S, UIMI0004, and most other programs
Charge With Credit — used in DXCP801S specifically for the transfer batch balance function

These likely describe different aspects of the same process (the claim type vs. the financial transfer mechanism), but I'm flagging the two documented expansions rather than merging them. What follows is a synthesized summary drawn from multiple source programs.

What CWC Does

CWC handles interstate unemployment claims where a claimant has wages earned in multiple states. When a claimant files in New Jersey but worked in other states, a CWC claim combines those out-of-state wages with NJ wages to determine monetary eligibility and benefit amounts. CWC claims use program codes PC-40, PC-41, PC-42, and PC-43.
DXCD037S-cbl.json
 A CWC employer is identified by the IB4 wage separation form indicator.
UIMI0004.md
DXCD037S-cbl.json

Key CWC Programs by Function
CICS Online — Employer Maintenance & Claim Setup
DXCD023S (Screen 295) — Maintains CWC employer information on existing UI claims within conversation D020. Allows operators to update employer wages, weeks, hold indicators, and separation form data. Can initiate a monetary determination by calling DXCD034S when all employer wage info is entered.
DXCD023S-cbl.html
CICS Online — Monetary Determination & Validation
DXCD037S — The core monetary determination common module. For CWC claims specifically, it detects overlapping wages across base year quarters and triggers creation of a General Fund employer entry via the 1250-CWC-CLAIM paragraph when overlap wages exist.
DXCD037S-cbl.json
DXCD051S — Claim validation during monetary redetermination. Enforces four CWC-specific validations :
DXCD051S-cbl.json
Error 822 — CWC Set Rate and Federal Set Rate cannot both be active
Error 823 — CWC Set Rate is active but no special CWC employer (IB4 form, list number 0, ≥ 20 base weeks) was found
Error 820 — Special CWC employer does not have the required IB4 form
Error 821 — Special CWC employer has fewer than 20 base weeks
DXCD056S (Screen 335) — CWC Transaction Monetary Redetermination for program code 45. Adjusts maximum employer liability based on another state's monetary determination, recalculates employer percentages, updates IMS segments, and generates BC-3 and IB-4.2/3 notices.
DXCD056S-cbl.json
DXCD057S (Screen 340) — Displays CWC Transfer Monetary Redetermination results for confirmation. Read-only; shows employer FEINs, max UI/EB/EUC amounts, and affidavit flags.
DXCD057S-cbl.json
CICS Online — Charge Transfer Batch Entry
DXCP800S (Screen 570) — CWC Batch Data Entry. Operators enter IB-6 transfer data from other states for CWC claims based on NJ wages. Validates batch header fields and up to 10 detail lines per page (SSN, benefit amounts). Supports multi-page entry (up to 6 pages) before transferring control to DXCP801S.
DXCP800S-cbl.json
DXCP801S (Screen 575) — CWC Transfer Batch Balance. Compares system-calculated totals against operator-entered totals for regular claims, sharable claims, EB, FSC, total charged, reimbursed/credit amounts, and claimant counts. On balance, writes detail and summary records to a report file.
DXCP801S-cbl.html
Batch — Employer Type Classification & Program Code Validation
UIMI0004 (batch subprogram) — Classifies each employer by form type; sets CWC-EMP-SW = 'Y' when form is IB4.
UIMI0004.md
UIMB0004 (CICS subprogram) — Same employer type classification logic in the online context.
UIMB0004-cbl.json
Batch — Reporting
DXCBW35R — Claims Activity Report (ETA-539). Tallies CWC as one of the four program types (UI, CWC, UCFE, UCX) across all benefit types and activity categories.
DXCBW35R.md
DXCBW39Z — Download record extraction for the claims activity report, extracting CWC counts for waiting weeks, pending weeks, compensated weeks, and other categories.
DXCBW39Z.cbl.md
Interstate Export
INPOSW06 — Routes interstate export records; CWC-related record types include IB4QO, IB4RO, and IB05O for weekly certifications.
INPOSW06-cbl.json
Data Mapping
LOF9SBLD — Maps CWC state code and CWC work begin date from the communication area to database records.
LOF9SBLD-cbl.json
DXCA016S — Classifies CWC employers during cross-program claim adjustment processing.
DXCA016S-cbl.json
Coverage Caveat

This summary is synthesized from the programs documented in the knowledge base. The CWC process likely involves additional upstream and downstream steps (initial claim intake, IB4 form receipt from other states, money movement, Treasury) that are outside the current knowledge base coverage. The interstate claim capture (IVR, CICS web) and check-print/direct-deposit functions are separately documented.

What would you like to explore next about CWC?

CWC overlap & general fund processing in DXCD037S

CWC validation rules and error codes

CWC charge transfer batch entry flow

_Citations:_
- Citation 3
- Citation 2
- Citation 3
- Citation 5
- Citation 3
- Citation 6
- Citation 7
- Citation 8
- Citation 1
- Citation 4
- Citation 2
- Citation 9
- Citation 10
- Citation 11
- Citation 12
- Citation 13
- Citation 14

## v1-Q7

**Q:** What does program ZXQQ9999 do?

**A** (10:43):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

The knowledge base has no program named ZXQQ9999. The search returned no matching documents.

The name does not follow any of the standard LOOPS naming conventions:

DXCB* — Batch programs (e.g., DXCBDA2R)
DXCD*S — CICS online programs (e.g., DXCD037S)
DXCC* — CICS common/utility programs (e.g., DXCC097S)
DXCP*S — CICS payment processing programs (e.g., DXCP025S)
DXCR* — Batch reformat programs (e.g., DXCRD99E)
UIM* — Subprograms (e.g., UIMI0440)
BC* — Base-claim modules
L2* — JCL jobs
WWCD*S / WWCP*S — Parallel (WW-prefixed) variants of DXCD/DXCP programs
LOAI* / LOA* / LOI* / LOF* — CICS session-builder and I/O modules

The prefix ZX and the QQ pattern don't match any documented LOOPS naming scheme. You may want to:

Double-check the program name for a typo
Check if it belongs to a non-LOOPS subsystem — the Z prefix sometimes appears in utility or operations-maintained programs (e.g., ZUMDA3R1 appears as a job name in the missing checks detection process), but ZXQQ9999 specifically is not documented
Ask the person who referenced it which system or module it belongs to
Would you like me to search for something similar?

Search for ZX* or QQ* programs

Try a different program name

## v1-Q8

**Q:** What's the deployment process for the production environment?

**A** (10:43):

ENGINEERING ONBOARDING SPECIALIST (V2)

The code-promotion / deployment / change-management process is outside the knowledge base entirely. This is a known gap — the LOOPS knowledge spaces cover program source code, batch job schedules, CICS screens, and business rules, but do not document the operational deployment pipeline.

What the Knowledge Base Does Not Cover
How code moves from development → QA → staging → production
Change-management approval workflows (e.g., change tickets, CAB review)
JCL or tooling used to compile, link-edit, and promote load modules
Environment-specific configuration (dataset naming, CICS region setup)
Rollback procedures
Where This Information Would Live

Typically for a mainframe LOOPS environment, the deployment process would be documented in:

Change Management / Configuration Management documentation — often maintained by the release management or operations team
ISPF/Endevor or equivalent SCM tool documentation — if a source code management tool is in use
Operations runbooks — maintained by the production support team
Project-specific deployment guides — sometimes kept in SharePoint, Confluence, or similar platforms

I'd recommend reaching out to the release management team or production support / operations team for this information. If you know which tool or process name they use (e.g., Endevor, ChangeMan, custom JCL promotion scripts), I can check whether any references appear in the knowledge base, but as of now none are documented there.
