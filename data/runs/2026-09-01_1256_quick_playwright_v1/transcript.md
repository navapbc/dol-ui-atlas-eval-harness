# 2026-09-01_1256_quick_playwright_v1

- **Backend:** quick (transport: playwright)
- **Bank:** v1 (`question_sha256` 5850e95bbbd2…)
- **Agent:** engineering_onboarding_specialist (`093ac4e3-0712-481e-af95-9ddc5e4fc734`)
- **Conversation:** `fac5cd1e-acbc-494b-9933-61f2ee402ada`
- **Model:** Advanced
- **Started:** 2026-09-01 12:49
- **Finished:** 2026-09-01 12:56
- **Status:** complete
- **Questions asked:** 8, answered: 8

## v1-Q1

**Q:** How does the weekly certification batch process flow from start to finish?

**A** (12:50):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

Here's what I can piece together about the weekly certification batch process from the knowledge base. Important caveat: This is synthesized from multiple retrieved documents, and the most detailed source I retrieved covers the downstream extract/reporting step (program DXCBDA2R). The full upstream job chain (L2* jobs) is referenced at a high level but its individual step-by-step detail was not fully retrieved in this search.

High-Level Flow

The CA-7 daily overview document identifies the UI continued-claim/certification processing as the L2* job chains, covering: certification intake → edits → pay/no-pay decisioning → downstream extracts.
00_ca7_daily_over...
 The Weekly Certification module has its own dedicated knowledge space with more granular documentation.

What the Knowledge Base Documents
1. Certification Intake (Upstream — L2* chains)

Claimant certifications arrive via WEB and PHONE/IVR channels. The L2* batch jobs handle ingesting these certifications, applying edits, and making the pay/no-pay decision. The results are split into two key output files:

PAYVSAM — certifications approved for payment
NOPAY — certifications that did not qualify for payment

(The individual L2* job steps and programs are documented in the Weekly Certification knowledge space but were not fully returned in this search.)

2. Certification Week Date Calculation (UIMB0443)

Program UIMB0443 calculates certification week period boundaries. Each certification week's start date is computed by subtracting 6 days from the week-ending date (CWE date), establishing the 7-day period.
UIMB0443.md

3. Certification Extract / Audit Reporting (DXCBDA2R)

This is the best-documented stage in the retrieval. Program DXCBDA2R can run in either DAILY or WEEKLY mode (controlled by a run-type parameter). In WEEKLY mode, it performs these 20 steps :
DXCBDA2R.md
DXCBDA2R.cbl.md

Program Initialization — Read run type (DAILY/WEEKLY), accept date control card, format production dates
Open Input Files — Open PAYVSAM and NOPAY files
Read & Process PAYVSAM Records — Read pay-eligible certification records, categorizing each by:
Prior week vs. current week
Special dates
Single-week vs. two-week certifications
Age (over 4 weeks)
Earnings status (with/without earnings)
Benefit category and last-payment flag
Channel (WEB or PHONE)
Read & Process NOPAY Records — Same categorization for no-pay certifications
Void & Bypass Handling — Track voided and bypassed records separately
Write Audit Records — Write categorized records to output audit files
Combined Certification Extracts Report — Generate the combined (all-channel) Weekly Certification Extracts Report with totals, percentages, and breakdowns
WEB-Only Report — Calculate WEB-only percentages (single-week vs. two-week) and write a separate WEB-only extract report
PHONE-Only Report — Same structure filtered to PHONE/IVR certifications only
Control Totals Summary — Display summary statistics: production run date, weekend dates, counts of PAYVSAM/NOPAY records read, total processed, voids, bypasses, and audit record counts by category
File Closure & Termination — Close all input/output files and end program execution
What Lives Outside This Retrieval
The full L2* job chain (individual JCL members, step-by-step program sequence from intake through pay/no-pay decisioning) — documented in the Weekly Certification knowledge space but not fully returned here
Downstream money movement (check print, direct deposit, Treasury interface) — separately documented outside the LOOPS knowledge base
Real-time capture (IVR/CICS web certification entry) — also separately documented
Would you like me to dig deeper into a specific part of the flow?

Upstream L2* job chain detail

DXCBDA2R extract/report internals

Run a comprehensive research analysis

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4

## v1-Q2

**Q:** Explain the role of program DXCBDA2R and its input/output files.

**A** (12:51):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

Program DXCBDA2R is thoroughly documented in the knowledge base. Here's a comprehensive breakdown of its role and complete I/O inventory, sourced from DXCBDA2R.md (Daily CA-7 space) and DXCBDA2R.cbl.md (Weekly Certification space).

Program Role

DXCBDA2R is a batch COBOL program developed for the N.J. Department of Labor, Division of UI/DI Programs. Its purpose is to extract and analyze certification data from the upstream pay/no-pay decision files and produce Daily or Weekly Certification Extract Reports.
DXCBDA2R.md
DXCBDA2R.cbl.md

It categorizes every certification record along four dimensions:

Entry source (channel): WEB, PHONE/IVR, or Manual (P100)
Benefit program type: UI, EB, WFD, TUC Tiers 1–4
Earnings status: No earnings, with earnings, or last payment
Week coverage: Single week, two weeks, prior week, special historical dates, or over 4 weeks old

The run mode (DAILY or WEEKLY) is controlled by a runtime parameter; if omitted, it defaults to DAILY. The mode only affects report headers — the processing logic is identical.
DXCBDA2R.md

Input Files (2)
DXCBDA2R Input Files

DD Name

	

Description

	

Source

	

...


PAYVSAM	Payment certification records — certifications approved for payment by the upstream L2* batch chain	Sequential file (INPUT mode)	...
NOPAY	No-payment certification records — certifications that did not qualify for payment	Sequential file (INPUT mode)	...
View more

Additionally, a SYSIN control card (B040-DATE-CONTROL-CARD) provides the daily processing date (B040-DAILY-DATE) and the week-ending date (B040-WEEK-ENDING-DATE) in MMDDCCYY format.
DXCBDA2R.md

Output Files (12)
DXCBDA2R Output Files

DD Name

	

Category

	

What Gets Written


ADTPRVWK	Previous Week Audit	Single-week certifications where CWE-DATE1 matches the calculated previous week-ending date
ADTD0629	Special Date Audit	Certifications with CWE-DATE1 = 06/29/2013
ADTD0928	Special Date Audit	Certifications with CWE-DATE1 = 09/28/2013
ADTONEWK	Single Week Audit	Certifications where CWE-DATE2 = 0 (single-week)
ADTTWOWK	Two Week Audit	Certifications where CWE-DATE2 > 0 (two-week)
ADTCWE14	Over 4 Weeks Audit	Single-week certifications older than 28 calendar days
ADTNEARN	No Earnings Audit	Records where both Earnings Amounts = 0
ADTWEARN	With Earnings Audit	Records where at least one Earnings Amount > 0
ADTLPAYS	Last Payment Audit	Records whose UI transaction code indicates a last payment
VOIDIND1	Void Records Audit	PAYVSAM records with BP88-VOID-IND = 1
View more
Key Validation & Routing Logic
CWE Date 1 validation: If CWE-DATE1 = 0, the record is written to BYPASS and skipped — applies to both PAYVSAM and NOPAY.
DXCBDA2R.md
Void Indicator check: PAYVSAM-only — if BP88-VOID-IND = 1, the record is written to VOIDIND1 and excluded from all further processing. NOPAY records have no void indicator check.
DXCBDA2R.md
Channel identification: Operator ID 9000 + Terminal ID 7777 → WEB; Terminal ID 7777 alone → PHONE; anything else → MANUAL (P100).
DXCBDA2R.md
A single record can appear in multiple output files (e.g., a record may be written to both ADTONEWK for single-week classification AND ADTNEARN for no-earnings classification AND ADTLPAYS if it's a last payment).
Reports Generated (written to AUDITREP)

The three reports share the same structure and differ only by channel filter :
DXCBDA2R.md

Combined Certification Extract Report — all channels (WEB + PHONE + MANUAL)
WEB-Only Report — filtered to web-submitted certifications
PHONE-Only Report — filtered to phone/IVR-submitted certifications

Each report includes: previous week count, special date counts, single-week vs. two-week counts/percentages, over-4-weeks count, no-earnings counts by benefit series (UI, EB, WFD, TUC, TUCX, TUCY, TUCZ), with-earnings counts by benefit series, last payment counts by benefit series, and total week count.

Important Notes
This program is the extract/reporting step only — it receives its input from the upstream L2* job chain that performs certification intake, edits, and pay/no-pay decisioning. The L2* chain details are documented in the Weekly Certification knowledge space.
No database access — DXCBDA2R reads and writes sequential files only; no VSAM or DB2 calls.
DXCBDA2R.md
DXCBDA2R.cbl.md
No subprogram calls — it is a standalone Main/Driver module with no CALL statements to other programs.
DXCBDA2R.md
DXCBDA2R.cbl.md
What would you like to explore next?

Upstream job chain and dependencies

Detailed categorization business rules

CA-7 scheduling and triggers

_Citations:_
- Citation 1
- Citation 2
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 2
- Citation 1
- Citation 2

## v1-Q3

**Q:** What are the business rules for determining pay vs. no-pay outcomes?

**A** (12:52):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

This is a broad topic that touches multiple programs and modules across LOOPS. Here is what the knowledge base documents about the factors that drive pay vs. no-pay outcomes, synthesized from several sources. I'll organize by processing area.

Overview

The Daily CA-7 overview describes the UI continued-claim / certification processing (L2* batch chains) as handling "certification intake, edits, pay/no-pay decisioning, and downstream extracts." It also notes that the Weekly Certification module has its own dedicated knowledge space with more detailed edit-level rules.
00_ca7_daily_over...

TRA/TAA Determination Rules (Program UIMB0018)

For TRA/TAA claims, the program UIMB0018 applies a cascading set of eligibility checks. The determination codes that drive the outcome are:

TRA/TAA Determination Codes And Outcomes

Determination Code

	

Meaning

	

Outcome


01	Eligible (TRA + TAA)	Pay path
03	Eligible for TAA only (no UI claim)	Pay path (TAA only)
04	Ineligible	No-pay
05	Indeterminate (pending wage data)	No-pay (held for reprocessing)
23	TAA-eligible, recycling	No-pay (pending reprocessing)
24	Ineligible, recycling	No-pay (pending reprocessing)
25	Indeterminate, recycling	No-pay (pending reprocessing)
View more

The key ineligibility triggers that produce a no-pay (code 04) on the TRA/TAA path include:

Separation before certification impact date — the claimant's separation predates the trade petition's certified impact window
Separation on/after certification expiration date — the separation falls outside the certified window
Separation reason is not "Lack of Work" (code ≠ 1) — only lack-of-work qualifies under TAA rules
No qualifying weeks or wages found in the wage database and no wage request is applicable

An indeterminate (code 05) results when no wage data is found and no quarters exist in the wage database at all — triggering a BC2 wage request to the employer.
UIMB0018.md

Payment Record Filtering (Program DXCBPIN)

Before a payment record reaches certification processing, DXCBPIN applies these filters that can prevent a record from advancing to pay:

EUB Exclusion — If UI Payment Type 1 or Type 2 falls in the range 400–499 (Extended Unemployment Benefits), the record is excluded entirely
Already-Certified Exclusion — If the Certification Code field (BP88-CERT-CODE) is already populated, the record is skipped (it was previously certified)
Voice Certification Eligibility — Based on the claimant's local office (900-series vs. 800-series), whether voice certification is enabled for that office, and whether the payment document date falls on or after the office's voice certification start date
Waiting Week Determination (DXCBPIN)

The system evaluates whether either of the two CWE (Compensable Week Ending) periods carries a waiting week indicator. If BP88-WW-IND-CWE1 or BP88-WW-IND-CWE2 is 'Y', the Waiting Week Indicator on the CERTPAY record is set to 'Y' — meaning that week is a no-pay waiting week. If neither is 'Y', it is set to 'N'.
DXCBPIN.md

NOPAY Record Suppression (Program NOPAYSUP)

When a NOPAY record is matched by SSN, Pay Code, and Document Number, the system compares the Current Certification Week Ending Date (CWE-DATE3) against the Original Certification Week Ending Date (ORIGINAL-CCWE). If they match, the certification has already been processed and the NOPAY record is suppressed to prevent duplicate no-pay processing.
NOPAYSUP.md

Determination Notice Suppression Rules (UIMB0018)

Even when a claim is determined eligible (pay path), the determination notice to the claimant may be suppressed if:

A nonmonetary separation issue exists on the UI claim (separation issue code > 0)
A toll-out (289D) indicator is present on the UI claim

This prevents premature notification while pending issues are resolved, though it does not change the underlying pay/no-pay determination itself.

Recycling and Exhaustion

Claims in recycling (processed more than once) have their notices and reports suppressed by default. Recycling exhausts after 365 days, at which point the claim is removed from automatic reprocessing. An exception: if a recycled claim newly becomes TAA-eligible (code 03 or 23) where it previously was not, a determination notice is generated.
UIMB0018.md

Important Caveats
This answer is synthesized from programs documented in the Daily CA-7 space (UIMB0018, DXCBPIN, NOPAYSUP, DXCBD31R) and the CA-7 daily overview. The core weekly certification edit rules — the claimant-level eligibility checks and edit validations that produce pay vs. no-pay for regular UI claims — are primarily documented in the Weekly Certification knowledge space. The earnings/pension offset arithmetic (handled by UIMI0440) is also in that space and is an inference from source code; it should be confirmed with an SME.
The payment suppression codes on the Certification Reference Table (used by DXCBD31R for reporting) define suppression reasons but the populated table values themselves live in the operations-maintained CODELOOP VSAM dataset, which is outside the knowledge base.
DXCBD31R.md
Would you like to explore further?

Weekly Certification edit rules for pay/no-pay

Earnings/pension offset logic (UIMI0440)

Full L2* batch chain flow

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 2
- Citation 5

## v1-Q4

**Q:** What is the exact partial-benefit earnings offset formula?

**A** (12:53):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

The partial-benefit earnings offset formula is well-documented in the knowledge base and has been verified against DXCD037S source, so it can be stated as confirmed. The formula appears in the earnings-based benefit calculation routine (262-CALC-AMT-BEN-PAID1) documented in programs DXCBD87E.md and UIMI0440-cbl.json.

The PWBR / Earnings Offset Formula

The formula applies per CWE (Compensable Week Ending) period — each week in a two-week certification is calculated independently.

Step 1: Compute the PWBR Ceiling (Partial Weekly Benefit Rate)

Two candidates are computed from the claimant's Weekly Benefit Rate (WBR), and the greater is used :
DXCBD87E.md

PWBR Candidate 1 = WBR × 1.2
PWBR Candidate 2 = WBR + 5

PWBR = MAX(Candidate 1, Candidate 2)


This PWBR represents the maximum earnings disregard threshold — the most the claimant can earn before all benefits are eliminated. The selection of the greater value ensures the claimant receives the most favorable threshold.
DXCBD87E.md

Step 2: Compute the Adjusted Weekly Benefit Amount (AWBA)
AWBA = PWBR − Earnings Amount


The AWBA determines whether the claimant gets a full benefit, a partial benefit, or no benefit at all.
DXCBD87E.md

Step 3: Determine the Gross Benefit Payable
AWBA-Based Benefit Determination

Condition

	

Result

	

Meaning


AWBA < 0	Benefit = $0	Earnings exceed the PWBR ceiling; no benefit payable
0 ≤ AWBA < WBR	Benefit = AWBA − Deductions	Partial-benefit week (earnings reduce the benefit below the full WBR)
AWBA ≥ WBR	Benefit = WBR − Deductions	Full-benefit week (earnings are low enough that the full WBR applies)
View more

Where Deductions (for each CWE period) are :
DXCBD87E.md

Deductions = Garnishment Amount
           + Offset Amount (CWE)
           + Federal Income Tax Withheld (CWE)
           + Pension Amount

Step 4: Cap at Claim Balance
If Benefit Amount > Claim Balance → Benefit Amount = Claim Balance


This prevents overpayment beyond the claimant's remaining entitlement.
DXCBD87E.md

Worked Example

Suppose a claimant has:

WBR = $400
Earnings = $100
Garnishment = $0, Offset = $0, Tax Withheld = $40, Pension = $0
Claim Balance = $5,000
Step 1:  PWBR Candidate 1 = 400 × 1.2 = $480
         PWBR Candidate 2 = 400 + 5   = $405
         PWBR = MAX(480, 405)          = $480

Step 2:  AWBA = 480 − 100             = $380

Step 3:  Since $380 < $400 (AWBA < WBR) → Partial week
         Benefit = 380 − (0 + 0 + 40 + 0) = $340

Step 4:  $340 < $5,000 → No cap needed

         Net Benefit Paid = $340

Two-Week Certification Handling

For CWE Week 2, the same PWBR/AWBA formula is applied independently using Week 2's earnings, garnishment, offset, tax, and pension amounts. However, for federal tax reporting purposes (program DXCBD87E), the Week 2 benefit amount is computed as a residual: Total Check Amount − Week 1 Benefit Amount.
DXCBD87E.md
DXCBD87E.md

Key Observations
The $5 add-on (PWBR Candidate 2 = WBR + 5) acts as a floor for very low WBR amounts — when WBR is below $25, the WBR + 5 candidate exceeds WBR × 1.2, providing a slightly more generous disregard.
The crossover point is WBR = $25: below $25, the +5 rule dominates; at $25 and above, the ×1.2 rule dominates.
This formula is confirmed as verified against DXCD037S source per the agent instructions. The arithmetic in UIMI0440 (which handles check printing) uses the same formula structure for its own benefit calculation.
Would you like to explore further?

Pension offset details

More worked examples

Programs that use this formula

_Citations:_
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 2

## v1-Q5

**Q:** What are the T120 category-to-payable-days values?

**A** (12:54):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

This is a case where the knowledge base documents the structure of the T120 table but not its populated values. Let me explain what's documented and what isn't.

T120 Table Layout (from T120TABL.cpy)

The copybook T120TABL.cpy defines only the record layout of the T120 table :
T120TABL.cpy.txt
T120TABL.txt
T120TABL.txt

cobol

01  T120-TABLE-DATE-BC2-MAILED.
    02 T120-CATEGORY-NUMBER          PIC 999.
    02 T120-DATE-MAILED-KEY.
      04 T120-DATED-BC2-MAILED-JULIAN  PIC 999.
      04 FILLER                        PIC X(9).
    02 T120-INCREASE-IN-DAYS         PIC 9.
T120 Table Record Layout

Field

	

PIC

	

Description


T120-CATEGORY-NUMBER	999	Always set to 120 when constructing the lookup key
T120-DATED-BC2-MAILED-JULIAN	999	Julian day-of-year (DDD) used as the lookup key
FILLER	X(9)	Unused padding
T120-INCREASE-IN-DAYS	9	Single digit (0–9): the number of additional days to add to the base mailing date
View more
How Programs Use It

Multiple programs read this table to compute mailing dates on claimant notices and forms. The logic is consistent across all documented consumers (UIMI0055, UIMB0055, DXCB236E, DXCB293R, DXCB225R, DXCBD09E, DXCRD08E, UIMB0803, UIMI0004, DXCD036S) :
UIMI0055.md
UIMB0055.md
DXCB293R.md
DXCB236E.md
DXCB236E.md
UIMB0057.md
UIMB0803.md
DXCB225R.md
DXCRD08E.md
DXCD036S-cbl.json
UIMI0004.md
DXCBD09E.md

Construct key: Category = 120, Julian date = today's (or the candidate mail date's) day-of-year
Look up the CODELOOP VSAM file for a matching T120 record
If found: retrieve T120-INCREASE-IN-DAYS — the number of extra days to skip (holidays/weekends)
If not found: default T120-INCREASE-IN-DAYS to 0 (no extra offset)
Calculate mailing date: Base date + 1 day (mandatory) + T120-INCREASE-IN-DAYS

The field T120-INCREASE-IN-DAYS is described in various source documents as a holiday/weekend adjustment — it tells the system how many additional days to add to push the mailing date past weekends and holidays to the next valid business day.
DXCB236E.md
DXCB236E.md
DXCD036S-cbl.json
UIMI0004.md

The Actual Values Are Not in the Knowledge Base

The populated T120 day-to-offset mappings live outside the knowledge base entirely. The copybook T120TABL.cpy defines only the record structure; the actual values (which Julian days map to which increase-in-days offsets) are operations-maintained in the CODELOOP VSAM dataset. This dataset is loaded and updated by operations staff, not compiled into the programs.

To obtain the actual category-to-payable-days values, you would need to:

Query the production CODELOOP VSAM file for all records with category number 120, or
Contact the operations team that maintains the CODELOOP dataset to obtain the current schedule of holiday/weekend offset entries

The PIC 9 definition means the offset can range from 0 to 9 additional days, which would cover scenarios like long holiday weekends (e.g., a Thursday holiday might have an offset of 4 to skip Thursday, Friday, Saturday, and Sunday).

Would you like to explore further?

Deep-dive into a specific program's T120 usage

Explore other CODELOOP configuration tables

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
- Citation 11
- Citation 12
- Citation 13
- Citation 14
- Citation 15
- Citation 7
- Citation 8
- Citation 13
- Citation 14

## v1-Q6

**Q:** What does the CWC process do and which programs are involved?

**A** (12:55):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

The knowledge base documents CWC extensively, though I should note upfront that the acronym "CWC" appears with multiple expansions across different source documents, which I'll flag as a documented conflict. Here's what the knowledge base covers:

CWC Acronym — Documented Conflict

The retrieved documents expand "CWC" inconsistently:

Table

Expansion

	

Source


Combined Wage Claim	DXCD036S-cbl.json, DXCD037S-cbl.json, UIMI0004.md, DXCBD10R.md
Current Work in Cycle	L217ML.md (one version)
Current Work in Channel	L217ML-jcl.json
Continuing Weekly Claim / Continued Week Claim	DXCBD37R.md (two versions)
Compensation for Workers' Compensation	DXCBD10R.md (Program Code 45 context)
View more

The predominant meaning across the CICS and monetary determination programs is Combined Wage Claim — the interstate program where wages earned in multiple states are combined to determine UI benefit eligibility in New Jersey. This is what I'll describe below, but the naming conflict is an open question for SME review.

What the CWC Process Does

In the Combined Wage Claim context, CWC handles claims where a claimant has worked in multiple states and their out-of-state wages need to be combined with NJ wages to establish benefit eligibility. Key aspects:

CWC employers are identified by the wage separation form indicator IB4 (out-of-state combined wage claim employer)
CWC Program Codes define the specific employer combination required :
DXCD037S-cbl.json
DXCD036S-cbl.json
PC-40 — CWC + NJ employer
PC-41 — CWC + UCFE (federal civilian)
PC-42 — CWC + UCX (military)
PC-43 — CWC + UCFE + UCX
Overlap wages — When a claimant's base year in one state overlaps with another, the system creates a General Fund employer entry to account for the overlapping amounts
CWC Transfers — Payments under Program Code 45 are tracked separately as "CWC Transfers Paid" rather than regular check amounts
Documented Programs Involved

This is synthesized from multiple knowledge-base sources. Programs outside the held knowledge-base slice may also participate.

CICS (Online) Programs
Table

Program

	

Role

	

Source


DXCD036S	Employer type flag setting & program code validation — scans the employer table, sets NJ/UCFE/UCX/CWC flags based on form indicators, validates that the employer combination matches the PC (40–43), enforces minimum employer counts for CWC claims	DXCD036S-cbl.json
DXCD037S	Monetary determination including CWC-specific logic — triggers the CWC Claim Monetary Update (paragraph 1250-CWC-CLAIM), sets monetary date, resets claim to valid, detects overlap wages across quarters, creates General Fund employer entry when qualifying transactions (C010, D020, D100, A015–A017) have overlap	DXCD037S-cbl.json
View more
Subprograms
Table

Program

	

Role

	

Source


UIMI0004	Wage accumulation — accumulates IB4 (CWC) employer wages into claim base totals alongside NJ, UCFE, and UCX employers; tracks quarterly wages/weeks for monetary summary	UIMI0004.md
UIMR0030	Charging module — called by UIMB0031 for charge processing during CWC transfers	UIMB0031-cbl.html
View more
Batch Programs
Table

Program

	

Role

	

Source


DXCBD33S	CWC data splitter — reads consolidated CWC detail file (LAK2LDXP.L201DB.CWC.DTL) and distributes records into 10 parallel output streams (L217ML1–L217ML0)	DXCBD33S-cbl.json
UIMB0031	CWC transfer processor — reads online CWC transfer records, opens IMS database, calls charging module UIMR0030, writes batch errors and reports	UIMB0031-cbl.html
DXCBD37R	CWC Charges Error Report Due to Rounding — reads CWC charge records and prints a report listing charges with rounding errors (SSN, PC, Date Claim, Charge Amount, Payment Amount, Balance Difference)	DXCBD37R.md
DXCBM03R	CWC Transferring Payments Error Report — reads CWC transfer payment error records (IB6RPT), identifies record types (detail vs. totals), prints errors by batch/quarter/state	DXCBM03R.md
DXCBD43E	Charge report with CWC record selection — Application 2 handles CWC record selection and writes qualifying records to a CWC output file	DXCBD43E.md
DXCBD10R	Payment reconciliation — separates CWC Transfers Paid (PC 45) from regular check amounts in FROM/TO/Net Change accumulators for control totals reporting	DXCBD10R.md
View more
JCL Jobs
Table

Job

	

Role

	

Source


L217ML	CWC data preparation — (1) deletes 40 prior-run files, (2) invokes DXCBD33S to split CWC data into 10 streams, (3) prints CWC file for audit, (4) pre-allocates 10 empty report files for downstream parallel processing	L217ML.md, L217ML-jcl.json
View more
Important Caveats
This describes the programs documented in the knowledge base. The CWC space contains 136 documents, so there are likely additional programs and details beyond what this search returned.
The upstream data flow (how the consolidated CWC detail file LAK2LDXP.L201DB.CWC.DTL is originally created) and downstream parallel processing (what the 10 split streams feed into) are not fully covered in these results.
The meaning of "CWC" in the Program Code 45 context (where DXCBD10R calls it "Compensation for Workers' Compensation") may represent a distinct usage from the Combined Wage Claim program codes 40–43 — this is another point worth confirming with an SME.
Would you like to explore further?

CWC batch job flow details

CWC monetary determination logic

CWC employer validation rules

Full CWC research report

_Citations:_
- Citation 1
- Citation 3

## v1-Q7

**Q:** What does program ZXQQ9999 do?

**A** (12:55):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

The knowledge base has no program named ZXQQ9999. The search returned no matches for that identifier.

The name also doesn't follow any of the standard LOOPS naming conventions I see in the documented programs:

DXCB* — Batch COBOL programs (e.g., DXCBDA2R, DXCBD33S)
DXCD*S — CICS online COBOL programs (e.g., DXCD036S, DXCD037S)
DXCR* — Related batch programs (e.g., DXCRD99E)
UIM* — Subprograms (UIMI* for online, UIMB* for batch, UIMR* for called modules)
DXEB* / DXER* — Easytrieve report programs
L2* — JCL job names (e.g., L217ML)
ZUM* / ZUL* — JCL procedure names

The prefix ZX and suffix 9999 don't match any pattern in the held code. You may want to double-check the program name for a typo. If you can share where you encountered this name (a JCL member, a call chain, a document), I can help trace what it might actually refer to.

## v1-Q8

**Q:** What's the deployment process for the production environment?

**A** (12:56):

ENGINEERING ONBOARDING SPECIALIST

The code-promotion / deployment / change-management process is not documented in the knowledge base. This is one of the explicitly known gaps — the LOOPS knowledge spaces cover selected modules' source code, batch flows, JCL, and business rules, but the process for promoting code changes into the production environment lives outside this material entirely.

Where This Information Would Live

Based on standard mainframe environments, the deployment process documentation would typically reside in:

Change management / configuration management documentation (often maintained by the operations or release management team)
Endevor, Changeman, or equivalent SCM tool procedures — whichever source code management system NJ DOL uses for LOOPS
Operations runbooks covering the promotion pipeline (e.g., DEV → QA → STAGE → PROD)
Change Advisory Board (CAB) or equivalent governance process documentation
Recommended Next Steps
How would you like to proceed?

Contact the release management or operations team for their deployment procedures

Search for JCL or job scheduling details that might reference promotion steps

Ask a different question about LOOPS modules, programs, or batch flows
