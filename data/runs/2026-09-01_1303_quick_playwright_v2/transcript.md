# 2026-09-01_1303_quick_playwright_v2

- **Backend:** quick (transport: playwright)
- **Bank:** v2 (`question_sha256` b34897f2b4ee…)
- **Agent:** engineering_onboarding_specialist (`093ac4e3-0712-481e-af95-9ddc5e4fc734`)
- **Conversation:** `79a83c7e-959b-4f54-bd40-aff8d3181827`
- **Model:** Advanced
- **Started:** 2026-09-01 12:56
- **Finished:** 2026-09-01 13:03
- **Status:** complete
- **Questions asked:** 8, answered: 8

## v2-Q1

**Q:** When a claimant reports earnings during weekly certification, how is the partial weekly benefit rate (PWBR) calculated and how is the final paid amount derived?

**A** (12:57):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

Here is a synthesized explanation of the PWBR calculation and final benefit amount derivation, drawn from multiple documented programs. The PWBR and WBR formulas have been verified against DXCD037S source and may be stated as confirmed.

PWBR Calculation (Confirmed)

The Partial Weekly Benefit Rate (PWBR) is the earnings threshold above which a claimant's benefits begin to be reduced. It is calculated from the claimant's Weekly Benefit Rate (WBR) as follows :
DXCBD55R.md
UIMB0004.md

If WBR = 0, then PWBR = 0 (no further calculation).
If WBR > 0, compute two candidates:
Candidate A = WBR × 1.2
Candidate B = WBR + $5.00
PWBR = the greater of Candidate A or Candidate B

An important detail from DXCBD55R.cbl: when the PWBR is stored on the BC3 monetary determination form, the cents are truncated (the result is whole dollars only).
DXCBD55R.md

The PWBR is computed at monetary determination time by subprogram UIMB0004 and stored as AMT_BENFT_WK_PARTL on the monetary summary record.
UIMB0004.md

Final Paid Amount Derivation (4-Step Process)

When a claimant reports earnings for a Compensable Week Ending (CWE) period, the earnings-based benefit calculation routine (paragraph 262-CALC-AMT-BEN-PAID1 in DXCBD87E.cbl) follows this four-step process :
DXCBD87E.md
DXCBD87E.md

Step 1 — Compute PWBR

Same formula as above: PWBR = MAX(WBR × 1.2, WBR + 5)

Step 2 — Compute Adjusted Weekly Benefit Amount (AWBA)
AWBA = PWBR − Reported Earnings

Step 3 — Determine Gross Benefit Amount

Three possible outcomes based on the AWBA :
DXCBD87E.md
DXCBD87E.md

Table

Condition

	

Result

	

Formula


AWBA < 0 (earnings exceed PWBR)	No benefit payable	Benefit Amount = $0
0 ≤ AWBA < WBR (partial week)	Partial week benefit	Benefit = AWBA − Deductions
AWBA ≥ WBR (full week)	Full week benefit	Benefit = WBR − Deductions
View more

Where Deductions are the sum of:

BP88-GARNISHMENT-AMOUNT1 (Garnishment)
BP88-OFFSET-AMT-CWE1 (Overpayment offset)
BP88-INC-TAX-WITHHELD-CWE1 (Federal income tax withheld)
BP88-PENSION-AMOUNT1 (Pension deduction)
Step 4 — Cap at Remaining Claim Balance

If the calculated benefit exceeds the claimant's remaining Claim Balance (BP88-CLAIM-BALANCE), it is capped at the Claim Balance to prevent overpayment.
DXCBD87E.md
DXCBD87E.md

CWE Period 2 Difference

For a payment that covers two compensable weeks, there is a documented difference in the CWE Period 2 AWBA calculation: pension is subtracted within the AWBA step rather than in the deductions step :
DXCBD87E.md

AWBA (Week 2) = PWBR − Earnings₂ − Pension₂


This differs from CWE Period 1 where pension is only subtracted as a deduction after the AWBA comparison.

Worked Example (Synthetic Data)

The following values are invented for illustration only — they are not production-representative.

Suppose WBR = $400, Earnings = $150, no deductions:

Candidate A = $400 × 1.2 = $480
Candidate B = $400 + $5 = $405
PWBR = $480 (greater of the two)
AWBA = $480 − $150 = $330
Since $330 < $400 (WBR) → Partial week: Benefit = $330
If Claim Balance ≥ $330 → Final Paid = $330
Source Programs
Table

Program

	

Role

	

Space


UIMB0004.cbl	Computes PWBR at monetary determination	Daily CA-7
DXCBD55R.cbl	Computes PWBR for BC3 form (truncates cents)	Daily CA-7
DXCBD87E.cbl	Earnings-based benefit calculation for federal tax records	Daily CA-7
View more

Note: This describes the benefit calculation as implemented in the documented programs above. Upstream weekly certification capture (IVR/CICS) and downstream money-movement (check print, direct deposit) are separately documented and outside the current knowledge-base coverage.

What would you like to explore next?

Transaction pay code routing logic

CWE Week 2 residual calculation details

WBR calculation at monetary determination

_Citations:_
- Citation 1
- Citation 2
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 3
- Citation 4
- Citation 3
- Citation 4
- Citation 3

## v2-Q2

**Q:** Does a claimant's SSN affect their certification schedule or mail dates?

**A** (12:57):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

Yes — the claimant's SSN affects both their certification schedule (which week they certify) and their mail dates (which day of the week documents are mailed). The SSN is used in two distinct ways, and several programs implement this logic. Here is a synthesized summary drawn from multiple documented sources.

1. Mail Date Staggering — SSN Last Digit (Even vs. Odd)

The last digit (9th character) of the claimant's unpacked SSN is extracted and classified as even or odd to determine the day-of-week a certification document is mailed. The purpose is to distribute mail volume evenly across the week. The offset is added to a base CWE date (CWE Date 4 if present, otherwise CWE Date 3; if neither exists, mail date is set to zeros).
UIMI0443.md
UIMI0441.md

Standard UI (Regular Phone Claims)
Table

SSN Last Digit

	

Offset

	

Target Mail Day


Even (0, 2, 4, 6, 8)	+3 days	Tuesday
Odd (1, 3, 5, 7, 9)	+2 days	Monday
View more

Source: UIMI0440.cbl and UIMI0441.cbl

Extended / Supplemental Programs (FSC, TUC, EUC, EB)
Table

SSN Last Digit

	

Offset

	

Target Mail Day


Even (0, 2, 4, 6, 8)	+5 days	Thursday
Odd (1, 3, 5, 7, 9)	+4 days	Wednesday
View more

Source: UIMI0440.cbl and UIMI0441.cbl

BC-9 Form Mail Dates (Non-Certification Conversations)

For BC-9 form generation (program UIMI0326.cbl), two mail dates are calculated from the CWE base date :
UIMI0326.md

Table

SSN Last Digit

	

1st Mail Date Offset

	

2nd Mail Date Offset

	

...


Even	+3 days	+17 days	...
Odd	+2 days	+16 days	...
View more
Next Call-In Date (New Hire — DXNHCM04.cbl)

The same even/odd pattern applies when computing the next call-in date: even SSN → +3 days (Tuesday), odd SSN → +2 days (Monday).
DXNHCM04.md

Second Certification Date for No-Pay Records (UIMI0328.cbl)

For no-pay records with conversation code C010 or P100, the second certification date offset uses :
UIMI0328.md

Even SSN → +30 days (Tuesday)
Odd SSN → +29 days (Monday)
2. Biweekly Certification Week Assignment — SSN Last Four Digits

A completely separate mechanism uses the last four digits of the SSN to determine which week a claimant is scheduled to certify in the biweekly mail certification cycle. This is implemented in program DXCBDSUP.cbl (the CERT-SCHEDULE-CHECK routine).
DXCBDSUP.md
DXCBDSUP.md

Group Assignment
Table

SSN Last 4 Digits

	

Group


0001 – 4999	Group 1
5000 – 9999	Group 2
View more
Even vs. Odd Scheduling Years

The scheduling year (determined from the payment's date-entered-system) is classified as even or odd, and group assignments alternate accordingly :
DXCBDSUP.md
DXCBDSUP.md

Even year: Week 1 → Group 1 certifies; Week 2 → Group 2 certifies; subsequent weeks alternate (odd week-groups → Group 1, even week-groups → Group 2)
Odd year: Reversed — Week 1 → Group 2 certifies; Week 2 → Group 1 certifies; subsequent weeks follow the reversed pattern

If a claimant's payment falls in their "off" week (out-of-schedule), the system sets SUPP-CWE2-FLAG = 'Y', zeroes out BP88-CWE-DATE4, and rewrites the record to bring the claimant back into their correct biweekly cycle.
DXCBDSUP.md
DXCBDSUP.md

Note: This legacy scheduling logic applies only to payment records with document dates on or before March 5, 1994. Records after that date are excluded and use a newer scheduling method (the newer method is not fully documented in the current knowledge base).
DXCBDSUP.md

Summary

The SSN affects LOOPS certification processing in two independent ways:

Last digit (even/odd) → determines the day of the week mail is sent and the claimant is expected to call in, via an offset added to the CWE base date. Implemented in UIMI0440, UIMI0441, UIMI0326, UIMI0328, and DXNHCM04.
Last four digits (< 5000 vs. ≥ 5000) → determines the biweekly certification week (Group 1 vs. Group 2), alternating by even/odd scheduling year. Implemented in DXCBDSUP.

Coverage caveat: This answer is bounded by the documented programs in the knowledge base. Programs, jobs, or streams outside this coverage may handle certification scheduling differently; a universal claim cannot be confirmed from the knowledge base alone.

Would you like to explore any of these areas further?

Mail date calculation mechanics

Biweekly scheduling algorithm deep-dive

SSN formatting for certification output

_Citations:_
- Citation 1
- Citation 2
- Citation 5
- Citation 6
- Citation 7
- Citation 8
- Citation 9
- Citation 8
- Citation 9
- Citation 8
- Citation 9
- Citation 8

## v2-Q3

**Q:** What TRANS-UI-PAY1 transaction code values appear in pay/no-pay processing and how are they handled?

**A** (12:59):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

The TRANS-UI-PAY1 field (also referred to as NOPAYIN-TRANS-UI-PAY1 or BP88-TRANS-UI-PAY1 depending on the record layout) is a numeric transaction code that serves three distinct purposes in pay/no-pay processing: it classifies the benefit program type, triggers a Waiting Week Credit record type override, and drives Direct Deposit output file routing. Here is a synthesized summary drawn from multiple documented programs.

1. Waiting Week Credit — Values 1 and 2

When TRANS-UI-PAY1 equals 1 or 2 and TRANS-UI-PAY2 equals zero (no secondary payment), the record type (NOPAYIN-RECORD-TYPE) is overridden to '6', classifying the record as a Waiting Week Credit. If either condition is not met (PAY1 is not 1 or 2, or PAY2 is non-zero), the existing record type is preserved unchanged.
UIMB0442.md
UIMI0441.md
UIMB0441.md

This override is implemented identically in the pay-side programs UIMI0441 / UIMB0441 and the no-pay-side programs UIMI0442 / UIMB0442.

2. Program Type Classification — Range-Based (100–799)

The code drives assignment of the two-character Program Type (F37-PROGRAM-TYPE) and the FSC Program Literal (F49-FSC-LIT1) on check/notice output records. The ranges and their assignments are:

TRANS-UI-PAY1 Program Type Ranges

Code Range

	

Program Type (

	

F37

	

...


100–199	EB	EB	...
200–299	EC	EC	...
300–399	TX	TX	...
400–499	EU	EU	...
500–599	WF	WF	...
600–699	TY	TY	...
700–799	TZ	TZ	...
Outside all above	(unchanged)	(unchanged)	...
View more

Source programs: UIMI0441.cbl, UIMI0442.cbl, UIMB0441.cbl, UIMB0442.cbl (identical logic in all four).
UIMI0441.txt
UIMB0441.txt
UIMI0442.txt
UIMB0442.txt

Evaluation order quirk

In the COBOL source, the ranges are not evaluated in simple ascending order. The actual IF-ELSE chain is: 100–199 → 200–299 → 300–399 → 400–499 → 600–699 → 700–799 → 500–599. The 500–599 (WF) check comes last. Because the chain is mutually exclusive (IF-ELSE), this ordering has no correctness impact — but it matters when reading the source.
UIMI0441.txt
UIMB0441.txt

FSC Literal override chain

The FSC Literal field (F49-FSC-LIT1) is assigned through the same range-based chain, but with two additional independent overrides evaluated afterward:

WF override: If the WFD-TUI condition is true (500–599), the FSC literal is unconditionally set to 'WF', overriding any prior assignment from the chain (EB, EC, TX, TY, TZ, or EU).
UIMI0441.md
UIMI0442.md
SE override: If the Self-Employment Assistance indicator on either CWE week equals '1', the FSC literal is overridden to 'SE', superseding everything including WF.
3. Direct Deposit Routing — in UIMI0143 / UIMB0311

Program UIMI0143.cbl (and its counterpart UIMB0311) uses the same BP88-TRANS-UI-PAY1 field to route Direct Deposit ACH bank records to the correct output file:

TRANS-UI-PAY1 Direct Deposit Routing

Code Range

	

Output File

	

Program Category


200–399	DDBNKTUC	TUC (Trade / Federal Supplemental)
600–799	DDBNKTUC	TUC (Trade tiers)
100–199	DDBNKEB + EBPAY	Extended Benefits
Other (< 100 or 400–499 or 500–599)	DDBNKPUA or DDBNKUI	PUA or Regular UI (determined by DB2 lookup)
View more

For non-DD records, the same code determines whether the record is written to EBPAY (100–199) or to NONFILE (everything else).
UIMI0143-cbl.json
UIMI0143-cbl.json

4. Payment Type Classification — in DXCBP09R and UIMI0443

Program DXCBP09R.cbl extracts BP88-TRANS-UI-PAY1 into TRANS-UI-PAY-RANGE for downstream payment type classification. The 200–299 range is classified as 'TUC' (Federal Supplemental Compensation).
DXCBP09R.md

Program UIMI0443.cbl similarly copies BP88-TRANS-UI-PAY1 into the TRANS-UI-PAY-RANGE field, noting that the 400–499 range indicates "multiple checks were issued for the same period."
UIMI0443.md

5. CWE Date Toggle — in DXNHCM04

In the New Hire processing program DXNHCM04.cbl, TRANS-UI-PAY1 or TRANS-UI-PAY2 is assigned to the output PAYNOPAY-TRANS-UI-CODE depending on which CWE date (DATE1 vs DATE2) is the most current. If no valid CWE date exists (the date is zero), the transaction UI code is overridden to zero regardless of the prior assignment.
DXNHCM04.md

6. Record Reformatting — in NOPAYRFM

Program NOPAYRFM.cbl transfers TRANS-UI-PAY1 from the NOPAY source record directly into BP88-TRANS-UI-PAY1 on the PAYVSAM output record as-is, with no transformation. The same applies to TRANS-UI-PAY2.
NOPAYRFM.md

Summary
TRANS-UI-PAY1 Usage Summary

Value / Range

	

Effect

	

Where Implemented


1 or 2 (with PAY2 = 0)	Record type overridden to '6' (Waiting Week Credit); check message set to 'WAITING WEEK CREDIT ISSUED.'	UIMI0441, UIMI0442, UIMB0441, UIMB0442
100–199	Program type = EB; FSC literal = EB; DD routed to DDBNKEB/EBPAY	UIMI0441, UIMI0442, UIMI0143
200–299	Program type = EC; FSC literal = EC; DD routed to DDBNKTUC; classified as 'TUC'	UIMI0441, UIMI0442, UIMI0143, DXCBP09R
300–399	Program type = TX; FSC literal = TX; DD routed to DDBNKTUC	UIMI0441, UIMI0442, UIMI0143
400–499	Program type = EU; FSC literal = EU; indicates multiple checks in UIMI0443	UIMI0441, UIMI0442, UIMI0443
500–599	Program type = WF; FSC literal = WF (unconditional override)	UIMI0441, UIMI0442
600–699	Program type = TY; FSC literal = TY; DD routed to DDBNKTUC	UIMI0441, UIMI0442, UIMI0143
700–799	Program type = TZ; FSC literal = TZ; DD routed to DDBNKTUC	UIMI0441, UIMI0442, UIMI0143
Outside all ranges	No program type assigned; field unchanged	UIMI0441, UIMI0442
Zero (set by DXNHCM04)	Override when no valid CWE date exists	DXNHCM04
View more

Note: This summary is synthesized from the documented programs in the knowledge base. The label on values 1 and 2 as "Waiting Week Credit" is derived from the code behavior (record type set to '6' and check message 'WAITING WEEK CREDIT ISSUED') — the knowledge base does not contain an explicit code-table definition for these low-value codes. Programs, jobs, or streams outside the knowledge base coverage may use TRANS-UI-PAY1 in additional ways not captured here.

Would you like to dig deeper into any of these areas?

Waiting Week Credit downstream effects

FSC Literal override chain details

DXCBP09R payment type classification

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 5
- Citation 6
- Citation 7
- Citation 4
- Citation 5
- Citation 2
- Citation 8
- Citation 9
- Citation 10
- Citation 11
- Citation 12
- Citation 13
- Citation 14

## v2-Q4

**Q:** What are the valid program code values and their descriptions in Table 109?

**A** (13:00):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

This is an important question, and the answer requires distinguishing between what the knowledge base documents about the Table 109 layout and code references versus the actual populated descriptions, which live outside the knowledge base.

Table 109 Layout

The copybook T109TABL (from the LOOPS - Daily CA-7 space) defines the structure of a Table 109 record, but not its populated values :
T109TABL.txt
T109TABL.txt

01  T109-TABLE-PROGRAM-CODES.
    02 T109-CATEGORY-NUMBER      PIC 999.
    02 T109-PC-KEY.
      04 T109-PROG-CODE          PIC 99.
      04 FILLER                  PIC X(10).
    02 T109-PC-LEVEL             PIC 9.
    02 T109-EMPLOYER-TYPE        OCCURS 5 TIMES.
      04 T109-FILLER-T109A       OCCURS 1 TIMES  PIC X.
    02 T109-PC-DESCRIPTION       PIC X(20).
    02 T109-PRG-CODE-EB          PIC 99.
    02 T109-LI-PROGCODE-EC       PIC 99.


Each entry carries a 2-digit program code (T109-PROG-CODE), a 3-digit category number, a 1-digit level, 5 employer-type flags, a 20-character description, and two related program-code fields for EB and EC.

Program Code Numbers Referenced in Source

Multiple programs define literal constants that correspond to the program codes expected in Table 109. The following codes appear as LIT-nn values across programs like UIMI0004.txt, DXCBD43E.txt, and DXCRD28R.txt
UIMI0004.txt
DXCBD43E.txt
DXCRD28R.txt
 :

Table 109 Program Code Numbers Referenced In Source

Program Code

	

Appears In (Literals)

	

Notes


10	DXCBD43E, DXCRD28R	Standard program code
11	UIMI0004, DXCBD43E, DXCRD28R	Standard program code
12	UIMI0004, DXCBD43E, DXCRD28R	Standard program code
14	UIMI0004, DXCBD43E, DXCRD28R	Standard program code
20	UIMI0004, DXCBD43E, DXCRD28R	Standard program code
21	UIMI0004, DXCBD43E, DXCRD28R	Standard program code
22	UIMI0004, DXCBD43E, DXCRD28R	Standard program code
23	UIMI0004, DXCBD43E, DXCRD28R	Standard program code
30	UIMI0004, DXCBD43E, DXCRD28R	Standard program code
31	UIMI0004, DXCBD43E, DXCRD28R	Standard program code
View more

Additionally, program UIMI0003.cbl lists program codes 10, 20, 21, 22, 23, 30, 31, 40, 41, 42, 43, 44, 45, 60, 61, 99 as "standard program codes" that cannot use Local Office 988.
UIMI0003.md

Special Handling of Program Code 99

Program code 99 is a reserved special code that bypasses the Table 109 lookup entirely. In DXCBD41R.cbl, when PC = 99 :
DXCBD41R.md
DXCBD41R.md

If the Payment Type Indicator = 3 → description is set to 'SUSPENSE CHECKS'
If the Payment Type Indicator = 4 → description is set to 'MISSING/SPOILED CHKS'
If combined with Transaction Code = P941 → the T109 search is skipped entirely with no description loaded

For all other program codes, the system searches Table 109 using T109-PROG-CODE as the key. If the code is not found, the description fields are set to 'INVALID PROG CODE' and an error (code 720) is logged with the claimant's SSN and date paid.
DXCBD41R.md
DXCBD41R.md

What Is Not in the Knowledge Base

The actual T109-PC-DESCRIPTION text values (the 20-character descriptions for each program code) are not in the knowledge base. Like the T120 table, the T109TABL copybook defines only the record layout. The populated values — the program code numbers, their descriptions, category numbers, levels, employer types, and EB/EC cross-reference codes — are operations-maintained in the CODELOOP VSAM dataset at runtime. To obtain the actual description text for each code (e.g., what code 10 or code 40 is called), you would need to:

Query the CODELOOP VSAM dataset directly (table number 109), or
Consult the operations/SME team that maintains those reference tables
Summary

The knowledge base documents 21 distinct program code numbers (10–14, 20–23, 30–31, 40–45, 52, 55, 60–61, 99) referenced across source programs. The copybook T109TABL provides the record layout, and DXCBD41R.cbl documents how the codes are looked up and how code 99 is handled specially. However, the human-readable descriptions for codes other than 99 live in the CODELOOP VSAM dataset and are outside the knowledge base's coverage.

What would you like to explore next?

CODELOOP VSAM access patterns

T109 category and employer-type fields

EB and EC cross-reference codes in Table 109

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 5
- Citation 6
- Citation 7
- Citation 8
- Citation 7
- Citation 8

## v2-Q5

**Q:** What are all the possible SG11 nonmon issue code values?

**A** (13:01):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

This is an important question, and I need to be upfront about what the knowledge base documents versus what it does not contain.

What the Knowledge Base Documents

The field SG11-NON-PRIMARY-ISSUE is defined as PIC S999 COMP-3 (a 3-digit signed packed-decimal), and each SG11 nonmonetary segment also carries an array SG11-NON-ISS-CD that OCCURS 5 TIMES, each also PIC S999 COMP-3.
UIMB0018.txt
 This means the field can technically hold any 3-digit numeric value. The knowledge base does not contain a complete enumeration table of all valid nonmonetary issue codes. The full set of valid values is likely operations-maintained in a reference table (possibly in the CODELOOP VSAM dataset or a similar lookup), which is outside the held knowledge base.

What I can provide is every issue code value that is explicitly referenced and checked in the documented source programs. This is a synthesized list drawn from multiple programs and spaces:

SG11 Nonmonetary Issue Codes Referenced In Source Programs

Issue Code

	

Description

	

Source Program(s)

	

...


4	Refusal of Work / Separation-in-Question	UIMB0018, UIMB0025, UIMI0025	...
5	Separation-in-Question	UIMB0018	...
15	Pension	UIMB0018	...
17	Garnishment	UIMB0018	...
19	Fraud	UIMI0025	...
20	Fraud	UIMI0025	...
39	Gross Misconduct / Separation-in-Question	UIMB0018, UIMB0025, UIMI0025	...
43	School Employee / Separation-in-Question	UIMB0018, UIMB0025, UIMI0025	...
54	Retirement	UIMB0025, UIMI0025	...
87	(Excluded from transfer)	UIMI0025	...
View more
How These Codes Are Used

The documented programs use these issue codes in three main ways :
UIMB0018.txt
UIMB0025.md
UIMB0018.md

Separation-in-Question Analysis (UIMB0018): Issue codes 4, 5, 39, and 43 on SG11 segments are saved to an analysis table and later associated with qualifying separations for TRA/TAA determination.

Special Amount Capture (UIMB0018): Issue code 15 captures pension amounts; issue code 17 captures garnishment amounts. All other codes go to the separation analysis table.

Disqualification Checking (UIMB0025, UIMI0025): Issue codes 4, 39, 43, and 54 are checked for permanent/open-ended disqualifications (end date = all nines). If found, the system generates the message 'CLMT NEEDS 6X WBR IN 4 WEEKS OF WORK'.
UIMB0025.md

Transfer Filtering (UIMI0025): Issue code 87 is unconditionally excluded from non-monetary segment transfer. Issues 19 and 20 are routed to a separate fraud processing path.
UIMI0025.md

A Note on Description Conflicts

There is a minor conflict in the descriptions between sources :
UIMB0025.md
UIMI0025.md

UIMB0025.md describes issue 4 as "Refusal of Work" and issue 43 as "School Employee"
UIMI0025.md describes issue 4 as "Disqualification" / "adjudication" and issue 43 as "fraud" / "Disqualification"

These may reflect different contextual uses of the same codes, or a documentation inconsistency. I'd recommend confirming with an SME which descriptions are authoritative.

What Is Not in the Knowledge Base

The complete table of all valid nonmonetary issue code values and their descriptions is not documented in the held knowledge base. The 10 codes above are only those explicitly tested in the documented programs. There are almost certainly additional valid issue codes (the field supports values 0–999) that are used by other parts of the LOOPS system not covered here. To obtain the full list, you would need to consult:

The CODELOOP VSAM dataset (or whichever reference table stores nonmonetary issue code definitions)
The operations/SME team that maintains the issue code reference data
Would you like to explore further?

Search for more issue code references

Deep-dive on a specific issue code

SG11 segment structure overview

_Citations:_
- Citation 1
- Citation 1
- Citation 2
- Citation 3
- Citation 2
- Citation 4
- Citation 2
- Citation 4

## v2-Q6

**Q:** Does the compensable week ending (CWE) date always fall on a Saturday for every program code?

**A** (13:02):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

This is an excellent question, and the knowledge base has very thorough documentation on this topic. The short answer is: in the documented programs, the Saturday CWE is derived by construction, not enforced by runtime validation — and skeleton program codes don't get a CWE at all.

How the CWE Is Handled by Program Code Category

There are two distinct categories in the documented programs:

1. Skeleton Program Codes — No CWE Calculated

For skeleton program codes (11, 12, 50, 51, 70, 71, 72, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 88), the CWE date calculation is skipped entirely. The skeleton flag (C010-SKEL-FLAG) is set to '1', and neither a Current Week Ending date nor a Benefit Year End date is calculated or stored. Processing jumps directly to the base period calculations.
UIMI0003.md

This is consistent across all documented new-claim programs:

UIMB0003 (batch new claims)
UIMI0003 (CICS new claims)
UIMI0025 (interstate new claims)
2. Standard (Non-Skeleton) Program Codes — CWE = Claim Date + 6 Days

For all non-skeleton program codes, the CWE is computed as Date of Claim + 6 days and stored in C010-DATE-CURRENT-CWE.

This works because NJ UI claims must be filed on a Sunday (for non-skeleton, non-exempt codes). The UIMI0003 source explicitly validates this: if the Date of Claim does not fall on a Sunday, the claim is rejected with error message 'DATE OF CLAIM MUST FALL ON SUNDAY'.
UIMI0003.md
 Since Sunday + 6 = Saturday, the CWE is always a Saturday by construction.

Notable exception: Program Code 45 and claims filed before a specific effective date bypass the Sunday day-of-week check entirely.
UIMB0003.md
 UIMB0025 also uses a different CWE calculation for PC 45 — it subtracts 7 days and then adjusts backward to the nearest preceding Sunday, rather than adding 6 days forward.
UIMB0025.md

Derived, Not Enforced

The 00_ca7_daily_overview.md document states this explicitly :
00_ca7_daily_over...

"In the held daily programs, the Saturday week-ending date (CWE) is produced by construction, not validated at runtime."

It lists the specific mechanisms across programs:

UIMB0018 — uses DAYS-TO-PREV-SATURDAY-VALUES day-of-week offset tables to snap a date to the prior Saturday
UIMB0248 — computes day-of-week (REM of INTEGER-OF-DATE by 7) and only performs weekly-report work in the Saturday branch; its explicit non-Saturday guard (IF WS-WEEKDAY NOT = 'SATURDAY') is commented out in source
DXCBDA2R — paragraph 1300-GET-PREV-WEEKEND-DATE computes the previous weekend date with month-length addends
DXCBDSUP — computes the Saturday CWE boundary for mail-certification scheduling using day-of-week offset tables
DXCBD23U — computes the "Saturday of the CWE week" by calculating a forward offset from the CWE date using day-of-week remainder mapping
Summary
Table

Program Code Category

	

CWE Behavior

	

Source Programs


Skeleton (11, 12, 50, 51, 70–88)	CWE not calculated; skeleton flag set to '1'	UIMB0003, UIMI0003, UIMI0025
Standard non-skeleton (10, 20, 21, etc.)	CWE = Date of Claim + 6 days; claim date must be Sunday, so CWE is always Saturday by construction	UIMB0003, UIMI0003
PC 45 (Interstate Benefit)	CWE calculated differently (backward from claim date minus 7, adjusted to preceding Sunday); Sunday claim-date check is bypassed	UIMB0025, UIMB0003
Downstream programs	Various programs snap dates to Saturday using offset tables, but none actively reject a non-Saturday CWE at runtime (the UIMB0248 guard is commented out)	UIMB0018, UIMB0248, DXCBDA2R, DXCBDSUP, DXCBD23U
View more

Bottom line: In the documented programs, the Saturday CWE pattern holds by derivation (the code constructs it to be Saturday), but no documented program actively validates or rejects a non-Saturday CWE at runtime. The UIMB0248 source had such a guard, but it is commented out. Skeleton program codes receive no CWE at all. This analysis is bounded by the knowledge base coverage — programs, jobs, or streams outside the held slice may handle it differently, so a universal claim that CWE is always Saturday system-wide cannot be confirmed from the knowledge base alone.

Would you like to explore further?

CWE in interstate claim type determination

DXCBD23U disqualification date calculation

CWE offset table mechanisms

_Citations:_
- Citation 1
- Citation 1
- Citation 2
- Citation 4
- Citation 5

## v2-Q7

**Q:** What does program UIMB0447 do and which files does it read and write?

**A** (13:02):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

The knowledge base does not contain documentation for a program named UIMB0447. The search returned no source code, business rule extracts, or analysis documents matching that program ID.

Closest Documented Programs

Based on LOOPS naming conventions (UIMB* = batch programs, UIM* = subprograms), here are the nearest documented programs that you may have intended:

Table

Program

	

Description

	

Space


UIMB0047	Daily batch sync of Labor Load File to DB2 Table 14 (Employee Access Control)	Daily CA-7
UIMB0147	New Hires Crossmatch (LLR/Return-to-Work) batch processing — generates claimant/employer letters, inserts DB2 crossmatch records, IMS remarks	Daily CA-7
UIMB0441	Pay-side output formatting and routing (check/DD/notice generation)	Daily CA-7
UIMB0442	No-pay-side output formatting and routing	Daily CA-7
View more
Possible Explanations
Typo in the program name — if you meant UIMB0047 (Table 14 employee access control) or UIMB0441 (pay output processing), I can provide a detailed walkthrough of either.
Program exists but is outside the knowledge base — the held knowledge base covers selected LOOPS modules, not the entire system. UIMB0447 may exist in a module or job stream that hasn't been analyzed and indexed.
Would you like details on one of these nearby programs, or can you double-check the program name?

Tell me about UIMB0047

Tell me about UIMB0147

Tell me about UIMB0441

Tell me about UIMB0442

## v2-Q8

**Q:** How do I log on to the production mainframe, and what is the production region for LOOPS?

**A** (13:03):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

The knowledge base does not contain documentation for the mainframe logon procedure or the production region identifiers for LOOPS. This information falls outside the scope of the held knowledge spaces.

What Is Not Covered

The following topics are not documented in the knowledge base:

Logon procedures (TSO, CICS, ISPF session setup)
Production region names/identifiers (CICS region IDs, LPAR names, system IDs)
Credentials, access provisioning, or RACF setup
Code promotion / deployment / change management processes

These are operations-maintained artifacts — they live with the infrastructure and security teams, not in the program source analysis documents that the knowledge base covers.

Where to Find This Information

You would need to consult:

Your team's onboarding documentation or runbook — the infrastructure team or your project lead should have a mainframe access guide with region names, CICS transaction IDs, and TSO logon procedures
The RACF / security administrator — for access provisioning and credentials
The operations / systems programming team — for LPAR, CICS region, and environment mapping (development, QA, production)

If you have access to any of those documents and can share them, I'm happy to help you interpret or navigate them. I can also answer questions about what the LOOPS programs do once you're connected — that's well within the knowledge base coverage.
