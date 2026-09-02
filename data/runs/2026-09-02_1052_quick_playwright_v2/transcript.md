# 2026-09-02_1052_quick_playwright_v2

- **Backend:** quick (transport: playwright)
- **Bank:** v2 (`question_sha256` b34897f2b4ee…)
- **Agent:** engineering_onboarding_specialist (`30b0228b-b58a-43ad-818b-2f262f11108f`)
- **Conversation:** `8cd10715-ef2d-4a8d-93b8-4478e3e3cb27`
- **Model:** Advanced
- **Started:** 2026-09-02 10:43
- **Finished:** 2026-09-02 10:52
- **Status:** complete
- **Questions asked:** 8, answered: 8

## v2-Q1

**Q:** When a claimant reports earnings during weekly certification, how is the partial weekly benefit rate (PWBR) calculated and how is the final paid amount derived?

**A** (10:44):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

This is well-documented across several LOOPS CICS programs. Here's a synthesized walkthrough of the end-to-end logic, confirmed against source. The PWBR and WBR formulas have been verified against DXCD037S source and may be stated as confirmed.

Step 1: Establish the Working WBR

Before any PWBR math, the system may cap the claimant's WBR at the remaining program balance. If the claimant's WBR exceeds the remaining balance for the applicable program (UI, EB, FSC, or EUB), the working WBR (D072-WBR-PAY) is reduced to the remaining balance. If the balance is already exhausted (zero or negative), no cap is applied and the system proceeds with the original WBR.
WWCD072S-cbl.json

Step 2: Calculate the PWBR Threshold

Two candidate values are computed :
WWCD072S-cbl.json

Option A: WBR × 1.2 (120% of the Weekly Benefit Rate)
Option B: WBR + $5.00

The final PWBR is the greater of Option A and Option B. This ensures that claimants with very low WBR values still get a meaningful earnings disregard (the $5 floor), while claimants with higher WBRs use the 20% formula.
WWCA041S-cbl.json
LOIGSBLD-cbl.json

Note: During payment-segment preparation in WWCP028S.cbl and DXCP028S.cbl, a simpler form — WBR + (WBR × 0.20) with truncation — is used solely to classify earnings for transaction code assignment (partial vs. full). The full MAX-of-two-options formula is applied later in WWCD072S.cbl when the actual Weekly Benefit Amount is calculated.
WWCP028S-cbl.json
DXCP028S-cbl.json

Step 3: Classify Earnings & Assign Transaction Codes

Based on the PWBR threshold, the system assigns a Transaction UI Code to the payment segment :
WWCP028S-cbl.json

Transaction Code Assignment By Earnings Level

Earnings Level

	

First (Waiting) Week

	

Continued Week


Zero earnings	011 — Full benefit	017 — Full benefit
Earnings > 0 but < PWBR	012 — Partial benefit	018 — Partial benefit
Earnings ≥ PWBR	019 — No benefit payable	019 — No benefit payable
View more

These base codes may be overridden by extension-program-specific codes (e.g., 111/112/119 for EB, 211/212/219 for FSC, 411/412/419 for EUB, etc.) if the claimant is on an active benefit extension.
WWCP028S-cbl.json

Step 4: Calculate the Weekly Benefit Amount (WBA)

Using the final PWBR from Step 2 :
WWCD072S-cbl.json

Preliminary WBA = PWBR − Earnings
Cap: If WBA > WBR → set WBA = WBR (the claimant cannot receive more than their full weekly rate)
Floor: If WBA < 0 → set WBA = 0 (no negative benefit)
Step 5: Apply Pension Offset → Adjusted Weekly Benefit Amount (AWBA)

If the claimant has a pension offset on record :
WWCD072S-cbl.json

AWBA = WBA − Pension Offset Amount
If AWBA ≤ 0 and pension offset > 0 → AWBA is set to $0 and the payment segment backup flag is set to 'C' (indicating the pension fully eliminated the benefit)
If AWBA ≤ 0 and pension offset = 0 → AWBA is set to $0 with no special flag (benefit exhaustion unrelated to pension)
If AWBA > 0 → the value is accepted as-is

The AWBA is the final net amount that flows into payment processing.

Worked Example

Suppose a claimant has WBR = $400 and reports $300 in earnings on a continued week:

Option A: $400 × 1.2 = $480; Option B: $400 + $5 = $405 → PWBR = $480 (Option A wins)
Earnings $300 < PWBR $480 → Transaction Code 018 (partial benefit, continued week)
WBA = $480 − $300 = $180; $180 < $400 (WBR), so no cap needed
If pension offset = $0 → AWBA = $180 (final paid amount)
Source Programs
WWCP028S.cbl / DXCP028S.cbl — Payment segment preparation and transaction code assignment (CICS space)
WWCD072S.cbl — WBA/AWBA calculation with balance caps and pension offset (CICS space)
WWCA041S.cbl — Weekly Benefit Amount calculation rule summary (CICS space)
LOIGSBLD.cbl — Web certification PWBR validation (CICS space)
Would you like to explore a related topic?

Earnings offset details (inferred from source — SME review recommended)

Benefit extension code override logic

Balance-cap scenarios near claim exhaustion

_Citations:_
- Citation 1
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 5
- Citation 4
- Citation 4
- Citation 1
- Citation 1

## v2-Q2

**Q:** Does a claimant's SSN affect their certification schedule or mail dates?

**A** (10:45):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

Yes — the claimant's SSN affects LOOPS behavior in two distinct ways: it determines the day of the week the claimant must certify, and it controls the mail date printed on the check/certification document. There is also a deeper biweekly scheduling group mechanism that uses the last four digits.

1. Certification Day Assignment (SSN Last Digit — Odd/Even)

For web and phone certification, the system classifies the claimant's SSN based on its last digit :
LO99SBLD-cbl.json

Even last digit (0, 2, 4, 6, 8) → Claimant must certify on Tuesday
Odd last digit (1, 3, 5, 7, 9) → Claimant must certify on Wednesday

If a claimant attempts to certify on the wrong day (e.g., an odd-SSN claimant certifying on Tuesday), the system sets Error Code 5, which suppresses the second certification week (CWE2) payment eligibility — only the first week remains payable. This is documented in LO99SBLD.cbl (CICS space).
LO99SBLD-cbl.json

2. Mail Date Calculation (SSN Last Digit — Odd/Even)

When the check-printing programs (UIMI0440, UIMI0443, UIMI0442) calculate the mail date printed on the certification document, they use the last digit of the SSN to stagger mailing across different days :
UIMI0440.md
UIMI0443.md
UIMI0442.md

Mail Date Offset By SSN Parity And Program Type

Program Type

	

SSN Last Digit

	

Delta Days from CWE

	

...


Regular UI	Even (0,2,4,6,8)	+3	...
Regular UI	Odd (1,3,5,7,9)	+2	...
Extended (FSC/TUCX/TUCY/TUCZ/EB)	Even (0,2,4,6,8)	+5	...
Extended (FSC/TUCX/TUCY/TUCZ/EB)	Odd (1,3,5,7,9)	+4	...
View more

The base date is the latest Certification Week Ending (CWE) date — CWE Date 4 if present, else CWE Date 3. The delta days are added via the external date arithmetic routine DAT2K, and the result is formatted as MM/DD/YY for field F9-MAIL-DTE.
UIMI0440.md
UIMI0443.md

For the BC-9 form (no-pay scheduling), an additional second mail date offset is also applied: +17 days for even SSN, +16 days for odd SSN from the CWE base.
UIMI0326.md

3. Biweekly Certification Schedule Group (SSN Last Four Digits)

A separate, deeper scheduling mechanism uses the last four digits of the SSN to assign claimants to one of two groups for the biweekly certification cycle :
DXCAPIN-cbl.json
DXCBDSUP.md

Group 1: SSN last four digits 0001–4999
Group 2: SSN last four digits 5000–9999

The system classifies each year as either an "Even Year" or "Odd Year" based on a predefined perpetual cycle table (not simply calendar even/odd). The group determines which biweekly weeks a claimant is scheduled to certify :
DXCBDSUP.md

Biweekly Certification Schedule By Year Type And SSN Group

Year Type

	

Week 7 (DDD-1=7)

	

Week 14 (DDD-1=14)

	

...


Even Year	Group 1 scheduled	Group 2 scheduled	...
Odd Year	Group 2 scheduled	Group 1 scheduled	...
View more
Weeks where DDD-1 is not a multiple of 7 → all claimants are always scheduled regardless of group.
DXCAPIN-cbl.json
If a claimant certifies in a week they are not scheduled for, the system sets SUPP-CWE2-FLAG = 'Y', suppressing the second week's payment.
DXCC060S-cbl.json
In batch, DXCBDSUP also validates this schedule and will zero out CWE-DATE4 to reset claimants who are off their schedule.
DXCBDSUP.md

This logic appears in multiple programs: DXCAPIN.cbl, DXCC060S.cbl, LOAK025S.cbl (CICS space), DXCBDSUP.cbl (Daily CA-7 space), and LO99SBLD.cbl (CICS space).
LO99SBLD-cbl.json
DXCAPIN-cbl.json
DXCBDSUP.md
DXCC060S-cbl.json
LOAK025S-cbl.json

Summary

This answer is synthesized from multiple programs across both CICS and batch spaces. In short:

SSN last digit (odd/even) → determines the certification day (Tue/Wed) and the mail date offset on checks
SSN last four digits (< 5000 vs ≥ 5000) → determines the biweekly group for the perpetual certification schedule cycle
Certifying on the wrong day or in the wrong biweekly week suppresses the second week's payment eligibility
Would you like to explore any of these areas further?

Even/Odd Year cycle table details

Batch suppression logic in DXCBDSUP

BC-9 form date calculation differences

_Citations:_
- Citation 1
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 2
- Citation 3
- Citation 5
- Citation 6
- Citation 7
- Citation 7
- Citation 6
- Citation 8
- Citation 7
- Citation 1
- Citation 6
- Citation 7
- Citation 8
- Citation 9

## v2-Q3

**Q:** What TRANS-UI-PAY1 transaction code values appear in pay/no-pay processing and how are they handled?

**A** (10:47):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

This is a deeply documented topic across multiple CICS and batch programs. The TRANS-UI-PAY1 field encodes both the benefit program and the payment situation in a single numeric code. Here is a synthesized summary from the knowledge base.

Encoding Structure

The code follows a hundreds-digit = program convention, with the ones/tens digits indicating the payment position and earnings status within that program :
WWCP028S-cbl.json
DXCP028S-cbl.html
DXCP028S-cbl.json

Table

Hundreds Digit

	

Program


0xx	Regular UI
1xx	Extended Benefits (EB)
2xx	Federal Supplemental Compensation (FSC/EC)
3xx	Trade Unemployment Compensation Extension X (TUCX)
4xx	Emergency Unemployment Benefits (EUB)
5xx	Workforce Development (WFD)
6xx	Trade Unemployment Compensation Y (TUCY)
7xx	Trade Unemployment Compensation Z (TUCZ)
View more
Regular UI Base Codes (0xx)

These are assigned in CICS programs WWCP028S, DXCP028S, DXCP031S, and DXCD072S :
WWCP028S-cbl.json
DXCP028S-cbl.json
WWCP028S-cbl.html
DXCP031S-cbl.json

Regular UI Transaction Codes (TRANS-UI-PAY1 < 100)

Code

	

Week Type

	

Earnings Condition

	

...


001	Waiting Week Credit	N/A	...
002	Waiting Week Credit	N/A	...
005	Pended Waiting Week	No earnings	...
006	Pended Waiting Week	Earnings < PWBR	...
007	First Compensable Week	No earnings	...
008	First Compensable Week	Earnings > 0	...
009	Continuation	Benefit amount > 0	...
011	First Week (Pend)	No earnings	...
012	First Week (Pend)	0 < Earnings < PWBR	...
013	Last Payment	No earnings	...
View more

*Sources: WWCP028S.cbl
WWCP028S-cbl.json
WWCP028S-cbl.html
 , DXCP028S.cbl
DXCP028S-cbl.json
 , DXCP031S.cbl
DXCP031S-cbl.json
 , DXCD072S.cbl
DXCD072S-cbl.json
 *

Extension Program Codes

After the base Regular UI code is determined, benefit extension checks may override the code. The pattern is consistent: base + suffix, where the suffix mirrors the UI meaning :
WWCP028S-cbl.json
DXCP028S-cbl.html
DXCP028S-cbl.json
WWCP028S-cbl.html
LOAK025S-cbl.json

Extension Program Transaction Code Pattern

Suffix

	

Meaning

	

EB (1xx)

	

...


+07	First payment, no earnings	107	...
+08	First payment, with earnings	108	...
+09	First payment, no earnings (alt)	109	...
+10	First payment, with earnings (alt)	110	...
+11	First week (pend), no earnings	111	...
+12	First week (pend), partial earnings	112	...
+13	Last payment, no earnings	113	...
+14	Last payment, with earnings	114	...
+15	Middle payment, no earnings	115	...
+16	Middle payment, with earnings	116	...
View more

*Cells marked "—" mean the specific code was not retrieved from the knowledge base; it does not necessarily mean it doesn't exist. Sources: WWCP028S.cbl
WWCP028S-cbl.json
WWCP028S-cbl.html
 , DXCP028S.cbl
DXCP028S-cbl.json
 , DXCD072S.cbl
DXCD072S-cbl.json
WWCD072S-cbl.json
 , LOAK025S.cbl
LOAK025S-cbl.json
 *

How Transaction Codes Are Assigned

The assignment logic differs by processing context:

1. Pended Payment Processing (DXCP028S, WWCP028S) — The system classifies the week into three types based on the claimant's basic benefit record, then applies earnings against the PWBR threshold (WBR + 20% of WBR) :
WWCP028S-cbl.json
DXCP028S-cbl.json

Waiting Week (indicator = 1 in DXCP028S): codes 005/006/019
First Compensable Week (indicator = 1 in WWCP028S, 2 in DXCP028S): codes 011/012/019
Continued Week (indicator = 3): codes 017/018/019
After the base code is set, extension checks evaluate EB → EUB → FSC → TUCX → TUCY → TUCZ → WFD → EB(2009+) and may override with the program-specific code

2. Online Payment Processing (DXCP031S, DXCD072S) — Uses codes 007/008/009/013/014/015/016/019/021, with the additional first/middle/last payment distinction based on remaining balance and benefit year end checks

3. Payment Trigger / Extension Auto-Filing (LOAL026S) — After writing the LOOPPAY record, if TRANS-UI-PAY1 = 13, 14, 213, or 214, the system triggers TUC or TUCX extension auto-filing by evaluating CWE+1 against the entitlement period tables (Table 157 for TUC, Table 257 for TUCX)

Downstream Handling

No-Pay Notice Output (UIMI0442) — The TRANS-UI-PAY1 range determines the program type printed on BC-9 no-pay notices :
UIMI0442.md

UIMI0442 No-Pay Program Type By TRANS-UI-PAY1 Range

TRANS-UI-PAY1 Range

	

Program Type (F37)


< 100 (or unmatched)	Not set (regular UI)
100–199	EB
200–299	EC
300–399	TX
400–499	EU
500–599	WF
600–699	TY
700–799	TZ
View more

Waiting Week Credit Override (UIMI0441) — If TRANS-UI-PAY1 = 1 or 2 and the secondary pay code is zero, the record type is overridden to '6' (Waiting Week Credit)

Batch Check Classification (DXCBD50E, DXCBD40E) — For Series-7 batch checks, a payment type value derived from TRANS-UI-PAY maps to batch transaction codes :
DXCBD50E.md
DXCBD40E.md

0 → BP88 (Regular UI)
1 → EB88
2/3/6/7 → FS88 (FSC)
4 → EU88 (EUB)
5 → WF88 (WFD)

Void/Redeposit Processing (WWCP040S) — The code is classified into program buckets: UI (< 100), EB (100–199), FSC (200–299), TCX (300–399), EUB (400–499), WFD (500–599). Unrecognized codes produce error 685.
WWCP040S-cbl.json

Key Decision: Code 019

Code 019 is universal — it appears across all week types and all program contexts. It always means earnings ≥ PWBR and no benefit is payable for that week. The PWBR threshold is WBR + 20% of WBR.
WWCP028S-cbl.json
DXCP031S-cbl.json

This summary is synthesized from multiple programs across both CICS and Daily CA-7 batch spaces. The "—" entries in the extension code table reflect codes not retrieved from the knowledge base; an SME or direct source review should be consulted to confirm the complete set for each program.

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 1
- Citation 3
- Citation 4
- Citation 5
- Citation 1
- Citation 4
- Citation 3
- Citation 5
- Citation 6
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 7
- Citation 1
- Citation 4
- Citation 3
- Citation 6
- Citation 8
- Citation 7
- Citation 1
- Citation 3
- Citation 10
- Citation 12
- Citation 13
- Citation 14
- Citation 1
- Citation 5

## v2-Q4

**Q:** What are the valid program code values and their descriptions in Table 109?

**A** (10:48):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

This is an important distinction in the LOOPS knowledge base. The layout of Table 109 is documented, and the program code values referenced in source code can be identified, but the actual descriptions (T109-PC-DESCRIPTION text) are not in the knowledge base — they live in the CODELOOP VSAM dataset, which is operations-maintained.

Table 109 Record Layout

The copybook T109TABL (from T109TABL.txt) defines the structure :
T109TABL.txt

cobol

01  T109-TABLE-PROGRAM-CODES.
    02 T109-CATEGORY-NUMBER      PIC 999.
    02 T109-PC-KEY.
      04 T109-PROG-CODE          PIC 99.
      04 FILLER                  PIC X(10).
    02 T109-PC-LEVEL             PIC 9.
    02 T109-EMPLOYER-TYPE        OCCURS 5 TIMES.
      04 T109-FILLER-T109A       OCCURS 1 TIMES PIC X.
    02 T109-PC-DESCRIPTION       PIC X(20).
    02 T109-PRG-CODE-EB          PIC 99.
    02 T109-LI-PROGCODE-EC       PIC 99.

Each record carries: a 2-digit program code, a 1-digit level, 5 employer-type bytes, a 20-character description, and cross-references to related EB and FSC/EC program codes.

Program Codes Referenced in Source

From 88-level conditions and literal definitions across multiple programs, the following program codes appear in source and can be grouped by their condition-name classifications :
DXCR227M.txt
DXCR227E.txt
DXCRD28R.txt

Table 109 Program Codes Referenced In Source

Code

	

Source Condition Name

	

Inferred Category

	

...


10	UI-PROG-CODE	UI (Regular Unemployment Insurance)	...
20	UCFE-UCX-PROG-CODE	UCFE / UCX (Federal Employees / Ex-Servicemembers)	...
21	COMB-PROG-CODE	Combined Wage Claim	...
22	COMB-PROG-CODE	Combined Wage Claim	...
23	UCFE-UCX-PROG-CODE	UCFE / UCX	...
30	UCFE-UCX-PROG-CODE	UCFE / UCX	...
31	COMB-PROG-CODE	Combined Wage Claim	...
40	UI-PROG-CODE	UI (Regular Unemployment Insurance)	...
41	COMB-PROG-CODE	Combined Wage Claim	...
42	COMB-PROG-CODE	Combined Wage Claim	...
View more
Program Code Levels (T109-PC-LEVEL)

The level value controls which CICS transactions accept a given program code :
DXCC010S-cbl.json
LO9P128P-cbl.json
LO9GC23P-cbl.json

Level 1 — Valid for Claim Entry and EB processing (also extracts the related FSC program code from T109-LI-PROGCODE-EC)
Level 2 — Valid for Claim Entry and TUCX extension processing
Level 3 — Valid for TUCX extension and carries EUB filing restrictions
Level 4 — Valid for Claim Entry
What Is Not in the Knowledge Base

The actual T109-PC-DESCRIPTION text values (the 20-character descriptions like "NJ UNEMP INSURANCE" or similar) are populated at runtime from the CODELOOP VSAM dataset. The copybook T109TABL defines only the record layout — the values are operations-maintained, just as with other CODELOOP tables (e.g., Table 120). The knowledge base does not contain a dump or listing of CODELOOP contents.
T109TABL.txt

Similarly, the cross-reference fields T109-PRG-CODE-EB and T109-LI-PROGCODE-EC (which map each base program code to its corresponding EB and FSC program codes) are populated from CODELOOP, not hard-coded in the copybook.

To get the complete list of codes with their exact descriptions, you would need to consult the CODELOOP VSAM dataset directly or request an operations extract of Table 109 (category 109).

Would you like to explore further?

How specific program codes like 21, 22, 23 are validated

Table 109 usage in claim entry or EB/EUB processing

Other CODELOOP reference tables

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 5
- Citation 6
- Citation 7
- Citation 1

## v2-Q5

**Q:** What are all the possible SG11 nonmon issue code values?

**A** (10:49):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

The knowledge base does not contain a formal code table listing all valid SG11 nonmonetary issue code values with their official descriptions. The issue code field (DB11-NON-ISS-CD / SEG11-ISS-CD) is a 2-digit numeric value, and each nonmonetary segment (Segment 11) can hold up to 5 issue code entries.
DXCD061S-cbl.json

However, I can synthesize the issue codes that are explicitly referenced by name and function in the documented programs. This is a synthesized compilation — not a single authoritative source.

Issue Codes Referenced in Source Code
SG11 Nonmonetary Issue Codes Referenced In Source

Code

	

Description (from source)

	

Processing Category

	

...


0	Stop/empty — no issue code present; also treated as exempt	Stop condition / Exempt	...
3	WFD qualifying issue	General disqualification	...
13	Certified Time (see conflict note below)	Certified time — bypasses disqualification conflict check	...
15	Pension	Pension offset — bypasses disqualification conflict check	...
17	Labor Dispute / Wages in lieu of notice	Excluded from nonmonetary table in CMIB processing; bypasses conflict check	...
18	Identity theft / reversal	Special processing — identity reversal	...
19	Fraud overpayment / Fraud disqualification	Fraud — adds 119 days to nonmon date for end date; always added to table regardless of date overlap	...
20	Fraud penalty / Fraud disqualification alternate	Fraud — same handling as 19	...
23	Certified Time alternate	Certified time — same handling as 13	...
24	WFD qualifying issue	General disqualification	...
View more
Documented Conflict: Issue Code 13 Description

There is a conflict across sources for issue code 13 :
DXCP020S-cbl.json
WWCD072S-cbl.json

DXCP020S describes it as "Monetary Redetermination"
DXCD072S and WWCD072S describe it as "Certified Time"
DXCP331S groups it with 15, 17, and 48 as "pension-related codes" (which appears to be a broader processing-category label rather than an individual description)

This should be flagged for SME review to confirm the authoritative description.

Processing Groups (from CMIB payment processing)

The nonmonetary table construction logic in DXCD072S and WWCD072S classifies issue codes into these processing groups :
WWCD072S-cbl.json

Certified time (codes 13, 23, 48) — always added to the table; cert-time flag = 0
Pension (code 15) — added with pension dollar amount
Fraud (codes 19, 20) — always added regardless of date overlap; includes reduction amount
Labor dispute (code 17) — explicitly excluded from the nonmonetary table
Exempt from disqualification conflict check (codes 0, 13, 15, 17, 48) — DXCP151S skips these during disqualification table building
General disqualification (all other codes) — added only if their date range overlaps the CMIB processing period
What Is Not in the Knowledge Base

The complete enumerated list of all valid nonmonetary issue codes is not documented in the held code. The issue code is a 2-digit numeric field, and values beyond those listed above may exist in production. The full code table with official descriptions would be maintained as operations/reference data — likely in a CODELOOP VSAM table or an external reference document outside the knowledge base. An SME or operations staff member would need to be consulted for the authoritative complete list.

Would you like to explore a specific issue code further?

Fraud issue codes (19, 20)

Certified time processing

Exempt code handling in weekly certification

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 3

## v2-Q6

**Q:** Does the compensable week ending (CWE) date always fall on a Saturday for every program code?

**A** (10:50):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

Great question. The source code is quite clear on this — let me synthesize what the documented programs say.

Short Answer: Yes, in the documented programs — but with important nuances

In every program in the knowledge base that validates or computes a CWE date, Saturday is the required day of the week. However, not all program codes receive a CWE date at all, and one program code has a special calculation path. Here's the full picture:

CWE Must Be Saturday — Enforced by Multiple Programs

Multiple programs independently enforce (validate at runtime) and derive (compute by construction) the Saturday requirement:

DXCA360C (Screen A252 — basic claim data entry): Validates the CWE date field; if the day of week ≠ Saturday (day-of-week = 7), error code 9 is raised.
DXCA360C-cbl.json
DXCA016S (claim transfer screen): States explicitly: "A fundamental business rule for Unemployment Insurance requires that the Current Week Ending (CWE) date must always fall on a Saturday." Any non-Saturday CWE is rejected.
DXCA016S-cbl.json
DXCP020S (payment screen): Validates both CWE1 and CWE2 fall on the correct day (DOWSUB = 7); error 128 is raised if not.
DXCP020S-cbl.json
DXCBD23U (batch disqualification processing): Derives the disqualification end date by computing the Saturday of the calendar week containing the CWE.
DXCBD23U.md
CWE Calculation at Claim Creation: Program Code Matters

The claim creation program MACROLST reveals two paths :
MACROLST-cbl.json

Standard program codes — CWE is calculated as Date of Claim + 6 days. Since NJ UI claims begin on a Sunday (the DOC is a Sunday), adding 6 produces a Saturday. This is derivation by construction, not a runtime check on the day of week.

Skeleton/special program codes — the CWE calculation is skipped entirely and no CWE date is stored. These program codes are:

11 (EB), 12 (EB Reopen), 45 (Interstate Agent), 50 (Garnishment/UCX), 70 (UCX Military), 71 (UCX Reopen), 72 (UCX Extended), 75 (UCFE Federal), 76 (UCFE Special), 77 (UCFE Reopen), 78 (UCFE Extended), 79 (Special Federal), 80–84 (TRA variants), 88 (DUA)

These claims do not operate on the standard weekly certification schedule, so the question of "Saturday or not" doesn't apply — they have no CWE.

Special Case: UCX Program Code 30

For Program Code 30 (UCX — Military), the CWE is calculated differently depending on the claim date :
DXCD022S-cbl.json
DXCD112S-cbl.json

Claim date on or after 03/04/1990: CWE = Claim Date + 6 days (same as standard)
Claim date before 03/04/1990: CWE = the later of (Claim Date + 6 days) or (Separation Date + 35 days, adjusted forward to the next Saturday)

In both branches the resulting date is still a Saturday — the pre-1990 path explicitly rounds to the next Saturday.

Combined Program Codes (22, 23, 31, 42, 43) with UCX Wages

For these combined codes with Federal Set Rate = 'Y', DXCD051S validates that the CWE has reached the UCX separation boundary (separation date + 28 days, adjusted to the nearest Saturday).
DXCD051S-cbl.json
 Again, the boundary itself is Saturday-aligned.

A Documented Conflict in DXCP020S Mermaid Labels

There is a labeling inconsistency in DXCP020S: the Mermaid diagram labels for the CWE2 day-of-week check say "Does CWE2 fall on a Sunday?" while the rule descriptions and acceptance criteria consistently say the validation checks for DOWSUB = 7 meaning Saturday.
DXCP020S-cbl.json
 The rule description text is authoritative ("All compensable week ending dates must fall on a Saturday"), and the diagram label appears to be a documentation error. This should be flagged for SME review.

Summary
CWE Saturday Requirement By Program Code Category

Program Code Category

	

CWE Assigned?

	

Always Saturday?

	

...


Standard UI (e.g., 01, 02, 20, 21, etc.)	Yes	Yes	...
UCX PC 30 (post 03/04/1990)	Yes	Yes	...
UCX PC 30 (pre 03/04/1990)	Yes	Yes	...
Combined UCX (22, 23, 31, 42, 43)	Yes	Yes	...
Skeleton/special (11, 12, 45, 50, 70–79, 80–84, 88)	No	N/A — no CWE set	...
CWE validated on screens / payment	—	Saturday enforced	...
View more

Bottom line, in the documented programs: For every program code that receives a CWE date, that date is always Saturday — both by derivation (the arithmetic produces Saturday) and by enforcement (runtime validation rejects non-Saturdays). Program codes that are skeleton or special claims never get a CWE date at all.

Coverage caveat: This conclusion is bounded by the held code. Programs, jobs, or streams outside the knowledge base may handle CWE dates differently — a universal claim cannot be confirmed from the knowledge base alone.

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 5
- Citation 6
- Citation 7
- Citation 8
- Citation 3

## v2-Q7

**Q:** What does program UIMB0447 do and which files does it read and write?

**A** (10:51):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

The knowledge base does not contain a program named UIMB0447. No source code, business rules document, or JCL reference for that program ID was found in any of the connected spaces (Weekly Certification, Daily CA-7, CICS, or CA-7 All).

Possible Typo?

Based on LOOPS naming conventions (UIMB* = batch main programs, UIMI* = batch subprograms), here are the closest documented programs that might be what you're looking for:

UIMB0047 / UIMI0047 — A daily batch program that synchronizes a Labor input file against DB2 Table 14 (UIMV_EMPL_ACC_CNTL) to add, reactivate, or inactivate employee access control records
UIMB0147 / UIMI0147 — A batch New Hire crossmatch program that processes crossmatch records against UI benefit claims and generates letters and reports
UIMB0004 — A batch monetary determination program that calculates WBR, MBA, and employer charges and generates output forms (BC2, BC3, IB4, etc.)

Could you double-check the program name? If you meant one of the programs above, I can provide a detailed breakdown of its purpose and file I/O.

Did you mean one of these programs?

UIMB0047 / UIMI0047

UIMB0147 / UIMI0147

UIMB0004

## v2-Q8

**Q:** How do I log on to the production mainframe, and what is the production region for LOOPS?

**A** (10:52):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

The knowledge base does not document the mainframe logon procedure — that falls under operations/infrastructure documentation, which is outside the scope of the held LOOPS source code and analysis documents. However, the source code does reveal the production CICS region identifiers and related environment details.

What the Knowledge Base Documents: Production Region Identifiers

From the CICS programs that perform environment identification, the following CICS Application IDs (APPLIDs) are documented:

LOOPS CICS Region Identifiers From Source Code

APPLID

	

Environment

	

Notes

	

...


CI04JPAF	Production (Primary)	Used as the definitive production check across all programs	...
CI04JPAD	Production (Secondary)	Treated as production for restart user ID selection	...
CI02JTAC	Test (Region AC)	Dedicated test environment with its own MQ queues	...
CI02JTSF	Test (Region SF)	Dedicated test environment with its own MQ queues	...
View more
Production Service User IDs (from Source)

The programs hard-code environment-specific service user IDs for automated CICS transactions:

Production: LAKLDXP (used by LO8RCPLT to start transaction LO93) and LAKLDYP (used by LOD1GETQ for LOD1 restart)
Test/Non-Production: LAKLDXT (used by both programs in non-production regions)
Production MQ Queues (from Source)

The production CICS region CI04JPAF uses a dedicated MQ request queue: LAK2LDXP.LOOPS.REQUEST.CICJPAF

Security: ACF2 Authorization

The source code confirms that LOOPS uses ACF2 for mainframe security. Every CICS transaction checks authorization by calling program ACF2INT2 with a 300-byte communication area containing the resource name (e.g., LAALOOPSLO8J). A return value of 'D' in field WS-DENY-ALLOW means access denied.
LO8RCPLT-cbl.json

What Is NOT in the Knowledge Base

The following are not documented in the held code and would need to be obtained from your operations or infrastructure team:

TSO/ISPF logon procedures (hostnames, IP addresses, VTAM terminal definitions)
ACF2 user provisioning (how to request or activate a mainframe logon ID)
CICS region connection details (how to connect a 3270 terminal or emulator to CI04JPAF)
VPN or network access requirements for reaching the mainframe
Code promotion / deployment / change-management process

For the actual logon procedure, I'd recommend reaching out to your mainframe operations or infrastructure team, or checking for an onboarding/access-request document that would typically be maintained outside of the application source code.

_Citations:_
- Citation 1
