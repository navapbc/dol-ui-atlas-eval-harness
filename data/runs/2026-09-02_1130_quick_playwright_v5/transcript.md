# 2026-09-02_1130_quick_playwright_v5

- **Backend:** quick (transport: playwright)
- **Bank:** v5 (`question_sha256` 7babe64d260e…)
- **Agent:** engineering_onboarding_specialist (`30b0228b-b58a-43ad-818b-2f262f11108f`)
- **Conversation:** `ea7dc180-ab70-425a-a0d8-31ad73ad2d1b`
- **Model:** Advanced
- **Started:** 2026-09-02 11:17
- **Finished:** 2026-09-02 11:30
- **Status:** complete
- **Questions asked:** 8, answered: 8

## v5-Q1

**Q:** I'm picking up the daily NOPAY certification file generation process. Which job runs it, and what programs execute in sequence? What does each step do?

**A** (11:18):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

The daily certification extracts process — which reads both the LOOPPAY and NOPAY backup files — is run by job L2DCWEXR, classified under system code CWE1 (Daily Process). It has a restart criticality of 1 (highest). Below is the complete step-by-step breakdown.
L2DCWEXR.md
L2DCWEXR.txt

Job L2DCWEXR — Step-by-Step Flow
L2DCWEXR Job Step Sequence

Step

	

Step Name

	

Utility / Program

	

...


1	RECALDSN	IEFBR14	...
2	CLEANUP1	IEFBR14	...
3	COPYVPAY	IDCAMS REPRO	...
4	SORTVPAY	SORT	...
5	COPYNPAY	IDCAMS REPRO	...
6	SORTNPAY	SORT	...
7	CLEANUP2	IEFBR14	...
8	DLYCWEXR	DXCBDA2R (COBOL)	...
9	COPYCWER	IEBGENER	...
View more
Output Files Produced by DXCBDA2R (Step 8)

The COBOL program DXCBDA2R evaluates each LOOPPAY and NOPAY transaction against the DATECARD processing date and routes them into these categorized audit files :
L2DCWEXR.md

ADTPRVWK — Previous week's pay-period transactions
ADTD0629 — Transactions with Deduction Code 0629
ADTD0928 — Transactions with Deduction Code 0928
ADTONEWK — One-week pay cycle transactions
ADTTWOWK — Two-week (bi-weekly) pay cycle transactions
ADTCWE14 — Current Week Earnings over a 14-day period
ADTNEARN — Newly calculated/adjusted earnings
ADTWEARN — Standard weekly earnings
ADTLPAYS — Last/final pay transactions (e.g., termination pays)
VOIDI1FL — Voided/reversed payment transactions
BYPASSFL — Transactions intentionally bypassed
DAILYREP — Formatted Daily Audit Report (132-byte wide)

After the job completes, the Daily Certification Extracts Report is automatically emailed to four DOL recipients (Ronald Marino, Gregory Castellani, Jon Christiansen, Edward Kwiatkowski) with a CC to the DIT-LOOPS distribution list.
L2DCWEXR.md

Conditional Execution Logic

Steps 3–6 and 8–9 are conditional: they only run if every preceding step returned RC=0. Steps 1, 2, and 7 (RECALDSN, CLEANUP1, CLEANUP2) run unconditionally, ensuring cleanup happens even if earlier steps failed.
L2DCWEXR.md

Important: Related but Separate — NOPAYSUP

The knowledge base also documents a separate program called NOPAYSUP, which is not a step inside L2DCWEXR. NOPAYSUP runs after program DXCBDSUP in a different execution context and performs certification suppression — it compares LOOPPAY and NOPAY records by CWE (Current Week Ending) dates and flags the less-current record with suppression code '07'.
NOPAYSUP.txt
NOPAYSUP.md
 This is an upstream process that feeds into the files L2DCWEXR later reads.

What would you like to explore next?

How does DXCBDA2R categorize transactions in DAILY mode?

Walk me through the NOPAYSUP suppression process

What are the restart/recovery procedures for L2DCWEXR?

_Citations:_
- Citation 1
- Citation 2
- Citation 1
- Citation 1
- Citation 1
- Citation 3
- Citation 4

## v5-Q2

**Q:** Our operations runbook says program DXCB098B converts NOPAY EB records to VSAMPAY format in job ZUMDA2R1. Can you pull up its logic for me?

**A** (11:19):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

Good news — the program and job both exist in the knowledge base, but I need to flag an important name correction first.

Name Correction: DXCBO98B, Not DXCB098B

Your runbook says DXCB098B (with a zero), but the actual program name in both the JCL source (ZUMDA2R1.txt) and the COBOL source/analysis (DXCBO98B.txt, DXCBO98B.md) is DXCBO98B — that's the letter O, not zero. The JCL step is:

//DXCBO98B EXEC  PGM=DXCBO98B,COND=(0,NE)


If the runbook has a typo, it's worth correcting to avoid confusion during abend research or load-library lookups.
ZUMDA2R1.txt

What DXCBO98B Does — Overview

DXCBO98B is a batch COBOL program that converts NOPAY Electronic Benefits (EB) records (281-byte, LRECL=281) into PAYVSAM format (360-byte, LRECL=360). It runs as step DXCBO98B in job ZUMDA2R1 and only executes when all prior steps return RC=0 (COND=(0,NE)).
ZUMDA2R1.md
DXCBO98B.md

I/O Files
DXCBO98B I/O Files

DD Name

	

Dataset

	

LRECL

	

...


INFILE	LAK2LDXP.ZUMDA2R1.MAIL.NOPAYEB.DTL	281	...
OUTFILE	LAK2LDXP.ZUMDA2R1.MAIL.VSAMPAY.DTL	360	...
View more
Processing Logic — Step by Step

The program follows a simple read → map → write loop :
DXCBO98B.md

Open files — Opens INFILE (NOPAY) for reading and OUTFILE (PAYVSAM) for writing.
Read first record — Primes the loop; if EOF immediately, skips to step 12.
Map claimant identity — Transfers NOPAY-SSN → EB-SSN, NOPAY-PC → EB-PC, NOPAY-DOC → EB-DOC.
Map geographic/location fields — ZIP-5, ZIP+4, Responsible Local Office, Local Office.
Map dates & time — CWE Dates 1–4, Date Entered System, Time of Entry → EB-TIME-OF-CERT.
Map terminal/operator — Entry Terminal ID → EB-TERMINAL-ID-CERT; Entry Operator ID → EB-OPERATOR-ID-CERT.
Initialize decertification & check defaults — All set to zeroes or spaces (Pseudo Check Number, Actual Check Number, Date Paid, Check Amount, Void Indicator = 0, De-cert Terminal = spaces, De-cert Operator = 0, De-cert Time = 0).
Map financial fields — WBR, WBA, Claim Balance, Earnings (CWE1 & CWE2), Pensions (CWE1 & CWE2), Other Amount, Gross Amount, Integrity Bytes = zeroes.
Map work-week fields — Work-week earnings and indicators for CWE1 & CWE2.
Map health/offset/UI-transfer — Health Amount, Offset CWE1 & CWE2, Transitional UI Pay 1 & 2.
Reformat claimant name — Input: LASTNAME/FIRSTNAME MIDDLENAME → Output: FIRSTNAME MIDDLENAME LASTNAME using UNSTRING with / and space delimiters. Stored in EB-FIRST-MIDDLE-LAST-NAME.
DXCBO98B.txt
DXCBO98B.md
Reformat address — Input STREET/CITY in NOPAY-ADDRESS-SEG01-FORMAT → EB-ADDRESS-LINE1 (street) and EB-ADDRESS-LINE2 built as CITY STATE ZIP.
DXCBO98B.md
Map remaining fields — State code, Suppression Code → EB-CERT-SUPPRESSION; defaults ERI Code = 0, Cert Code = spaces; income tax withheld/taxable for CWE1 & CWE2; tax-year indicators and totals (3 years); SEA indicators CWE1 & CWE2; Print Indicator.
Set policy defaults — EB-NME-FINANCIAL-INST = spaces; EB-PAYMENT-TYPE-IND = '3' (non-check payment type, always).
DXCBO98B.md
Cleanse addresses — Replace all low-value (X'00') characters in EB-ADDRESS-LINE1 and EB-ADDRESS-LINE2 with spaces.
Write output record — Writes the 360-byte EB-RECORD to OUTFILE; increments NUM-TOT-OUTPUT.
Read next / loop — Reads next INFILE record, increments NUM-INPUT; loops back to step 3 until EOF.
Display summary — Prints "E.B. records converted to payvsam" banner with TOTAL INPUT RECORDS and TOTAL OUTPUT RECORDS.
Close files — Closes both files and terminates.
Key Policy Rules (Hardcoded Defaults)

These values are always set regardless of input content :
DXCBO98B.md

Payment Type Indicator = '3'
Check Amount = 0
Actual Check Number = 0
Date Paid = 0
Pseudo Check Number = 0
Void Indicator = 0
Financial Institution Name = spaces
ERI Code = 0
Certification Code = spaces
All de-certification fields = zeroes/spaces
Where It Sits in Job ZUMDA2R1

DXCBO98B runs on the EB mail processing branch of the job, immediately after the INCLEB sort step selects records with the EB indicator in range 100–199 (positions 217–218). The converted output (MAIL.VSAMPAY.DTL) feeds downstream mail and payment processing. It is not on the main check-generation path (that goes through NOPAYADD → VERFYNO2 → UIMI0441).
ZUMDA2R1.md

What would you like to explore next?

Show me all 16 steps of ZUMDA2R1

Build a complete field-mapping table for DXCBO98B

What reads the VSAMPAY output downstream?

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 3
- Citation 4
- Citation 5
- Citation 5
- Citation 3
- Citation 3
- Citation 2

## v5-Q3

**Q:** An engineer's note says CICS transaction LOJ4S200 is one of the entry points for stimulus payment inquiries. Which program handles that transaction?

**A** (11:20):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

The knowledge base does have detailed documentation on LOJ4S200, but I need to flag a couple of corrections to the engineer's note before diving into the logic.

Corrections to the Engineer's Note

LOJ4S200 is a program name, not a transaction ID. The CICS transaction associated with this program is LOJ4. LOOPS naming convention: LOJ*S200 names are COBOL programs in conversation S200; the 4-character transaction IDs are LOJ1, LOJ4, etc.

LOJ4S200 is not an entry point — it's a sub-function reached from LOJ1S200. The documented entry point to the stimulus inquiry subsystem is program LOJ1S200 (transaction LOJ1), which presents the Stimulus Claimant Menu (Screen 820). LOJ4S200 is reached only when the user selects Option 3 on that menu, after SSN validation passes. Control is transferred via XCTL (no terminal context).
LOJ1S200-cbl.json

It handles refund summary inquiries, not general "stimulus payment" inquiries. The documented title is Refund Summary Inquiry (Screen 824), which is one of six sub-functions under the stimulus menu — not a catch-all payment inquiry.
LOJ4S200-cbl.html

Program LOJ4S200 — Refund Summary Inquiry (Screen 824)

Here is the full documented logic (source: LOJ4S200-cbl.html and LOJ4S200-cbl.json):

Environment
Execution: Online CICS
Database: DB2
MQ Calls: None
Module Type: Main/driver module
Screen Map: LMAP824
DB2 Table: UIMT_STIM_REFUNDS
Processing Flow

The program operates in two states — Initial (first-time display) and Continue (user interaction loop) :
LOJ4S200-cbl.json

Initial State (screen state = 0 or 1):

Session Validation — Checks communication area length > 7; if invalid, returns immediately without processing.
LOJ4S200-cbl.html
Screen State Routing — If state is 0 (uninitialized), sets it to 1; routes to initial processing.
LOJ4S200-cbl.json
SSN Formatting — Retrieves SPAD-SSN-DB from the session, splits into WS-SSN1/WS-SSN2/WS-SSN3, assembles as XXX-XX-XXXX into screen field SSNO.
LOJ4S200-cbl.json
Refund Data Retrieval — Executes a DB2 SELECT against UIMT_STIM_REFUNDS using the claimant's SSN (IDN_SSN), fetching AMT_TOT_REF_DUE and AMT_TOT_REF_PAID.
LOJ4S200-cbl.json
No-record handling — If no row found, sets error flag MES-AP-ERRS = 'Y', positions cursor on option field, invokes READ-T200 to display error message 0200 ("no data available for SSN").
LOJ4S200-cbl.json
Amount display — If found, moves amounts to HOLD-TOT-AMT-DUE → TOTAL-AMT-DUEO and HOLD-TOT-AMT-PAID → TOTAL-AMT-PAIDO for currency-formatted display.
LOJ4S200-cbl.json
Screen send — Sends full map LMAP824 with ERASE, sets screen state to 2 (Continue), returns to transaction LOJ4 awaiting user input.
LOJ4S200-cbl.json

Continue State (screen state = 2):

Receive input — Reads LMAP824 map, captures OPT-INPUTI (option) and EIBAID (function key), clears message fields (APMSG1O, APMSG2O, BRCMSGO).
LOJ4S200-cbl.json
Option numeric validation — If OPT-INPUTI is not numeric, clears the display field.
LOJ4S200-cbl.json
Function key validation — Accepts only ENTER or PF1. PF1 sets option to '01'. Any other key → clears option, sets OPT-INPUTL = -1 (cursor position), routes to error handler.
LOJ4S200-cbl.json
Option range validation — If option > 24, clears and redisplays. If option is within 1–24 but not a recognized navigation option for this screen, clears and shows error.
LOJ4S200-cbl.json
Navigation: PF1 / Option 01 — Records 'LOJ4S200' as prior entry (APL-PRIOR-CCT-ENTRY), resets screen state to 1, transfers control back to LOJ1S200 (menu).
LOJ4S200-cbl.json
Redisplay: ENTER with blank/00 — Maintains state at 2, resends LMAP824, awaits further input.
LOJ4S200-cbl.json
Where LOJ4S200 Fits — Stimulus Inquiry Screen Map

For context, LOJ1S200 (the menu) routes to six sub-function programs :
LOJ1S200-cbl.json

LOJ1S200 Stimulus Claimant Menu Navigation

Menu Option

	

Target Program

	

Screen

	

...


1	LOJ2S200	(Claimant Detail)	...
2	LOJ6S200	821	...
3	LOJ4S200	824	...
4	LOJ6S200	821	...
5	LOJ9S200	(unknown)	...
6	LOJ7S200	826	...
View more

So the engineer's note likely meant: "Option 3 on the LOJ1 stimulus menu invokes program LOJ4S200 for refund summary inquiries." It's worth updating the runbook to reflect the correct transaction ID (LOJ4), the correct role (sub-function, not entry point), and the specific scope (refund summary, not general payment inquiry).
LOJ4S200-cbl.html
LOJ1S200-cbl.json

Would you like to explore further?

Pull up the LOJ1S200 menu program details

Show me LOJ7S200 (Screen 826) logic

Show me LOJ6S200 (Screen 821) logic

_Citations:_
- Citation 2
- Citation 1
- Citation 3
- Citation 1
- Citation 3
- Citation 3
- Citation 3
- Citation 3
- Citation 3
- Citation 3
- Citation 3
- Citation 3
- Citation 3
- Citation 3
- Citation 3
- Citation 3
- Citation 2
- Citation 1
- Citation 2

## v5-Q4

**Q:** For the claims certification cycle, is the certification week ending date always a Saturday? Is that enforced anywhere in code I can point to, or is it convention?

**A** (11:21):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

Yes — in the documented programs, the CWE date is always a Saturday, and this is enforced at runtime in code, not just convention. The knowledge base shows both active enforcement (code that checks the value and rejects violations) and derivation by construction (code that computes CWE so it lands on Saturday). Here's the full picture from the documented programs.

Runtime Enforcement (Rejects Non-Saturday CWE Dates)

These programs actively check day-of-week and reject or abort if CWE ≠ Saturday. These are the ones you can point to as enforcement:

Programs That Enforce CWE = Saturday At Runtime

Program

	

Type

	

Mechanism

	

...


DXCA360C	CICS (Screen A252)	Calculates DOWSUB for entered CWE date; checks DOWSUB = 7	...
DXCA016S	CICS (Claim Transfer)	Calculates day-of-week for entered CWE date; checks DOWSUB = 7	...
DXCP028S	CICS (Claim Period Processing)	Validates both CWE start and end dates are Saturday	...
WWCP028S	CICS (Web Claim Period)	Calculates DOWSUB for CWE Hold Date; checks = 7	...
View more

The strongest enforcement points you can cite are :
DXCA360C-cbl.json
DXCA016S-cbl.json
DXCP028S-cbl.json

DXCA360C — the basic claim data entry screen (A252). If an operator enters a CWE that isn't a Saturday, DOWSUB is computed via the date conversion routine, and if it's ≠ 7, the field is error-highlighted with error code 9. The rule is explicitly documented as "CWE Date Must Fall on a Saturday" (Policy Rule R-DXCA360C-cbl-00233).
DXCA360C-cbl.json

DXCA016S — the claim transfer screen. Same check, but with the explicit literal message 'CWE DATE MUST BE A SATURDAY' displayed to the user.
DXCA016S-cbl.json

DXCP028S and WWCP028S — claim period processing programs. These go further: if either the start or end date is not Saturday, the program abends with code 'NSAT' — a hard fatal error, no processing occurs, no records are written.
DXCP028S-cbl.json
WWCP028S-cbl.json

Derivation by Construction (Computes CWE to Always Be Saturday)

These programs don't reject violations — they ensure the CWE is Saturday by computing it that way:

Programs That Derive CWE As Saturday By Construction

Program

	

Type

	

Mechanism

	

...


DXCD071S	CICS (Basic Claim Record Update)	After CWE calculation, checks day-of-week; if not Saturday, advances forward to next Saturday	...
DXCBDSUP	Batch (Daily)	Calculates Julian day number, then adjusts backward to nearest preceding Saturday for CWE alignment	...
LO99SBLD	CICS (Web Payment)	Sets CWE1 from claim record (described as "Saturday end date"), derives week start as CWE − 6 days (= Sunday)	...
LOAASBLD	CICS (Web Benefit Payment)	RTW date derived by subtracting 5 days from CWE-1, which is explicitly stated as "a Saturday" yielding Monday	...
UIMI0443	Batch (Daily)	Derives week FROM date as CWE − 6 days, with comment "the start of the week is always 6 days before the ending Saturday"	...
LOICSBLD	CICS (Web Certification)	Assigns C-CWE1 from DB, then C-CWE2 = C-CWE1 + 7 (preserves Saturday alignment)	...
View more

Key example: DXCD071S is the auto-correction program. It evaluates the day-of-week after all CWE calculations and, if the result is not a Saturday, it advances the date forward to the next Saturday.
DXCD071S-cbl.json
 This is a belt-and-suspenders approach on top of the input validation.

Summary

The Saturday rule is both convention and enforced code, in the documented programs:

Input paths (DXCA360C, DXCA016S) validate at data entry and reject non-Saturday dates with error messages.
Processing paths (DXCP028S, WWCP028S) validate at execution time and abend on violation — the hardest possible enforcement.
Calculation paths (DXCD071S, DXCBDSUP) derive CWE to always land on Saturday by construction, and DXCD071S additionally auto-corrects if it doesn't.

Coverage caveat: This is bounded by the documented programs in the knowledge base. Programs, jobs, or streams outside this coverage may handle it differently, so a universal claim ("every CWE in the system is always Saturday") cannot be confirmed from the knowledge base alone. But within the documented code, the pattern is consistent and actively enforced — not just assumed.

Would you like to dig deeper into any of these?

DXCD071S auto-correction logic

Batch Saturday alignment in DXCBDSUP

Day-of-week calculation mechanism

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 5

## v5-Q5

**Q:** When does the yearly SOIL control-card update run, and what does an operator have to do before kicking it off?

**A** (11:22):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

The knowledge base does not have a process documented by the name "yearly SOIL control-card update." I searched for it specifically and could not match that name to a documented job, scheduled stream, or operator procedure. Let me tell you what the knowledge base does document about SOIL-related control cards and annual date processing, so you can determine if one of these is what you're looking for.

What IS Documented
1. The DATECARD Program — Daily Date Generation (Including Annual Dates)

The batch program DATECARD generates and writes 8 date values to an output file (LAK2LDXP.PROD.CNTLLIB(DATECARD)), and it auto-calculates the annual boundaries each time it runs :
DATECARD.md

Table

Slot

	

Date Calculated

	

How


1	Today's date	System date or input override
2	Nearest Wednesday (week-end date)	Julian arithmetic against 1969 epoch
3	First day of current month	MM=current, DD='01'
4	Last day of current month	Month-end table + leap-year check
5	Quarter begin date	Quarter calendar table lookup
6	Quarter end date	Quarter calendar table lookup
7	First day of current year	MM='01', DD='01' → January 1st
8	Last day of current year	MM='12', DD='31' → December 31st
View more

Slots 7 and 8 are the annual begin/end dates. When the DATECARD program runs on January 2nd, those slots automatically flip to the new year's boundaries. The slots accept overrides — if an operator pre-populates a slot with a real date (not the placeholder 'MMDDYY'), the program uses it as-is instead of calculating.
DATECARD.md

2. How Batch Programs Consume the Annual Dates

Downstream programs (e.g., DXCB236E, DXCB245E, DXCB165U, DXCRD28R, and the SOIL processing program DXCRR05E) all read the B040-DATE-CONTROL-CARD from SYSIN, which carries the full set of 8 dates — including the Annual Begin Date and Annual End Date. These are used as reference boundaries for annual period processing, year-based reporting, and YTD accumulation.
DXCB236E.md
DXCB165U.md
DXCRD28R.md

3. Operator Setup Instructions (from JCL Comments)

The JCL source for ZUMDSRR1 (a SOIL-related batch job) includes explicit operator setup instructions :
ZUMDSRR1.txt

SETUP INSTRUCTIONS
 CONTROL CARD:
   LAK2LDXP.PROD.CNTLLIB(DATECARD),DISP=SHR
   - MAKE SURE THAT THE DATECARD IS SET UP
     WITH THE RUN DATE THAT YOU NEED.


This tells the operator to verify the DATECARD member contains the correct run date before submitting the job.

4. FEDPGM — CICS Control Card Screen Update

The CICS program FEDPGM provides an online screen (MAP3) that allows an operator to manually update a control card record. It validates all fields for cleared/erased conditions, performs date range validation (year must be between current year and current year + 1, month between 1 and 12), and on success rewrites the record with the confirmation message: 'THE RECORD HAS BEEN CHANGED AND NOW CONTAINS THE DATA ON THE SCREEN'.
FEDPGM-cbl.json

5. SOIL Year-to-Date Field on Claim Records

Separately, the SOIL YTD Recovered Amount field (DB01-AMT-YTD-RECOVERED-SOIL) accumulates throughout the year as SOIL transactions are processed by DXCRD03U.
DXCRD03U.md
 Screen A269 in DXCA360C allows operators to manually edit this field.
DXCA360C-cbl.json

What's Missing

The knowledge base does not document:

A specific annually scheduled job whose sole purpose is "update the SOIL control card for the new year"
A runbook or checklist for year-end SOIL control-card rollover
Whether the DATECARD program is re-run manually at year-end, or whether the annual dates auto-roll because DATECARD runs daily as part of the normal schedule

The DATECARD program by design computes the annual begin/end from the current system date each time it runs — so if it runs daily, the year-end rollover would be automatic. But whether it's triggered daily by CA-7, or manually at year-end, or both, is not documented in the knowledge base coverage.

If you have a specific job name or screen number for the process you're thinking of, I can search for it directly. It's also possible this lives in operational runbooks or the Monthly CA-7 schedule, which are outside the current knowledge base coverage.

Would you like me to dig further into any of these?

Search by a name/number I provide

More detail on the FEDPGM control card screen

Map the DATECARD downstream dependencies

_Citations:_
- Citation 1
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 5
- Citation 6
- Citation 7
- Citation 8

## v5-Q6

**Q:** Generate a test suite for NOPAYADD's record handling — cover the main paths and edge cases, with the constants it actually uses.

**A** (11:26):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 2 steps

Here is the complete test suite for NOPAYADD, built entirely from the retrieved source code (NOPAYADD.txt) and business-rules extract (NOPAYADD.md)
NOPAYADD.md
NOPAYADD.txt
.

Provenance Note

Every field name, PIC clause, paragraph name, constant, and 88-level value in the test suite is copied from the retrieved source. All test data (SSNs, addresses, amounts) is synthetic — invented for illustration and not production-representative. The program does not branch on NOPAYIN-RECORD-TYPE or any financial field; it processes every record identically through address reformatting.

NOPAYADD Test Suite — Record Handling

NOPAYADD Test Suite
Derived from NOPAYADD.txt source (COBOL II Batch, Author: Tony End, Jan 4 1995; INSPECT addition: Richard Blumenfeld, July 21 2009)
Provenance Note

Every field name, PIC clause, paragraph name, constant, and 88-level value below is copied from the retrieved NOPAYADD.txt source code and the NOPAYADD.md business-rules extract. Synthetic test data (SSNs, addresses, amounts) is invented for illustration and is NOT production-representative. The program does not branch on NOPAYIN-RECORD-TYPE or any financial field — it processes every input record identically through address reformatting — so record-type values in the test data are included only to confirm pass-through fidelity.

Key Constants and Fields (from source)

Item

	

Source Location

	

Value / Size


NOPAYIN-ADDRESS-SEG01-FORMAT	FD NOPAYIN-FILE, level 03	PIC X(44)
HOLD-STREET	WORKING-STORAGE, AREA1	PIC X(30)
HOLD-CITY	WORKING-STORAGE, AREA1	PIC X(15)
ADDR-LINE1	FD NOPAYOUT-FILE, level 02	PIC X(30)
ADDR-LINE2	FD NOPAYOUT-FILE, level 02	PIC X(30)
NOPAYIN-STATE	FD NOPAYIN-FILE, level 03	PIC XX
NOPAYIN-ZIP-FIRST-FIVE	FD NOPAYIN-FILE, level 05	PIC 9(5)
NOPAYIN-ZIP-LAST-FOUR	FD NOPAYIN-FILE, level 05	PIC 9(4)
TWO-SPACES	WORKING-STORAGE, AREA1	PIC XX (initialized to spaces)
ONE-SPACE	WORKING-STORAGE, AREA1	PIC X (initialized to space)
END-FLAG	WORKING-STORAGE	PIC X; 88 END-OF-FILE VALUE 'Y'
RECS-WRITTEN	WORKING-STORAGE	PIC 9(7) VALUE ZERO
Delimiter used by UNSTRING	1100-PROCESS-ADDRESS paragraph	'/' literal
NOPAYIN-RECORD-TYPE 88s	FD NOPAYIN-FILE	'1'=100% offset, '2'=pended week, '3'=other payment, '4'=current CWE change, '5'=UI claim is BYE, '6'=WW credit
Input LRECL	FD NOPAYIN-FILE, RECORDING MODE F	281 bytes
Output LRECL	FD NOPAYOUT-FILE, RECORDING MODE F	281 + 30 + 30 = 341 bytes
Processing Sequence (paragraphs from source)
200-HSKG — OPEN INPUT / OUTPUT, PERFORM 9000-READ (priming read)
1000-MAIN-PROCESSING (loop UNTIL END-OF-FILE) → a. 1100-PROCESS-ADDRESS — INITIALIZE AREA1 & NOPAYOUT-RECORD; MOVE NOPAYIN-RECORD TO NOPAYOUT-RECORD; UNSTRING on '/'; MOVE street; STRING city/state/zip b. INSPECT ADDR-LINE1 REPLACING ALL LOW-VALUES BY SPACES c. INSPECT ADDR-LINE2 REPLACING ALL LOW-VALUES BY SPACES d. WRITE NOPAYOUT-RECORD e. ADD 1 TO RECS-WRITTEN f. 9000-READ — next record or set END-FLAG = 'Y'
300-WRAP-UP — DISPLAY summary, CLOSE files
Category 1 — Happy-Path Address Reformatting
TC-01: Standard street/city with full state and 5-digit ZIP

Input fields:

NOPAYIN-ADDRESS-SEG01-FORMAT = '123 MAIN ST/NEWARK ' (44 chars, padded)
NOPAYIN-STATE = 'NJ'
NOPAYIN-ZIP-FIRST-FIVE = 07102
NOPAYIN-ZIP-LAST-FOUR = 3344

Expected output:

ADDR-LINE1 = '123 MAIN ST ' (30 chars, space-padded)
ADDR-LINE2 = 'NEWARK NJ 07102 ' (STRING fills left-to-right: city trimmed at double-space, space, state trimmed at single-space, space, zip, space; remainder is spaces from INITIALIZE)
All non-address fields = byte-for-byte copy of input (from MOVE NOPAYIN-RECORD TO NOPAYOUT-RECORD)
RECS-WRITTEN incremented by 1

Verifies: Normal UNSTRING split on '/', STRING formatting with TWO-SPACES / ONE-SPACE delimiters, ZIP+4 last-four digits excluded.

TC-02: City name with interior space (multi-word city)

Input fields:

NOPAYIN-ADDRESS-SEG01-FORMAT = '456 OAK AVE/ATLANTIC CITY '
NOPAYIN-STATE = 'NJ'
NOPAYIN-ZIP-FIRST-FIVE = 08401

Expected output:

ADDR-LINE1 = '456 OAK AVE '
ADDR-LINE2 = 'ATLANTIC CITY NJ 08401 '

Verifies: STRING uses TWO-SPACES (not single space) as the city delimiter — 'ATLANTIC CITY' contains single spaces that are NOT the delimiter; it stops only at the first pair of consecutive spaces in HOLD-CITY.

TC-03: Long street address near 30-char boundary

Input fields:

NOPAYIN-ADDRESS-SEG01-FORMAT = '12345 NORTH BRUNSWICK AVENUE/EDISON '
NOPAYIN-STATE = 'NJ'
NOPAYIN-ZIP-FIRST-FIVE = 08817

Expected output:

ADDR-LINE1 = '12345 NORTH BRUNSWICK AVENUE ' (28 chars of street + 2 spaces padding)
ADDR-LINE2 = 'EDISON NJ 08817 '

Verifies: Street portion fits within HOLD-STREET PIC X(30); no truncation.

Category 2 — Delimiter Edge Cases
TC-04: No '/' delimiter in address field

Input fields:

NOPAYIN-ADDRESS-SEG01-FORMAT = '789 ELM ST TRENTON NJ 08608 ' (no slash)
NOPAYIN-STATE = 'NJ'
NOPAYIN-ZIP-FIRST-FIVE = 08608

Expected output:

HOLD-STREET receives entire field up to 30 chars: '789 ELM ST TRENTON NJ 08608 '
HOLD-CITY remains spaces (AREA1 was INITIALIZE'd; UNSTRING does not populate second receiving field when delimiter not found)
ADDR-LINE1 = '789 ELM ST TRENTON NJ 08608 '
ADDR-LINE2 = ' NJ 08608 ' (spaces delimited by TWO-SPACES = empty, then space+state+space+zip+space)

Verifies: UNSTRING with no delimiter — entire source goes to first INTO field; HOLD-CITY stays at initialized spaces; STRING with an all-spaces city produces leading space before state.

TC-05: '/' at the very beginning of address

Input fields:

NOPAYIN-ADDRESS-SEG01-FORMAT = '/CAMDEN '
NOPAYIN-STATE = 'NJ'
NOPAYIN-ZIP-FIRST-FIVE = 08101

Expected output:

HOLD-STREET = spaces (empty field before delimiter)
HOLD-CITY = 'CAMDEN '
ADDR-LINE1 = ' ' (all spaces — blank street)
ADDR-LINE2 = 'CAMDEN NJ 08101 '

Verifies: Leading delimiter yields empty street; city still parses correctly.

TC-06: '/' at the very end of address

Input fields:

NOPAYIN-ADDRESS-SEG01-FORMAT = '100 BROAD ST/ '
NOPAYIN-STATE = 'NJ'
NOPAYIN-ZIP-FIRST-FIVE = 07102

Expected output:

HOLD-STREET = '100 BROAD ST '
HOLD-CITY = spaces (nothing after delimiter)
ADDR-LINE1 = '100 BROAD ST '
ADDR-LINE2 = ' NJ 07102 ' (empty city → space+state+space+zip+space)

Verifies: Trailing delimiter yields empty city; STRING still produces state/zip.

TC-07: Multiple '/' characters in address

Input fields:

NOPAYIN-ADDRESS-SEG01-FORMAT = 'APT 2/A BLDG/PATERSON '
NOPAYIN-STATE = 'NJ'
NOPAYIN-ZIP-FIRST-FIVE = 07501

Expected output:

HOLD-STREET = 'APT 2 ' (everything before first '/')
HOLD-CITY = 'A BLDG ' (between first and second '/')
ADDR-LINE1 = 'APT 2 '
ADDR-LINE2 = 'A BLDG NJ 07501 '

Verifies: UNSTRING splits on first '/' occurrence; fills two INTO fields sequentially; third segment discarded.

TC-08: Street portion exceeds HOLD-STREET's 30 characters

Input fields:

NOPAYIN-ADDRESS-SEG01-FORMAT = '12345678901234567890123456789012/CITY ' (32 chars before '/')
NOPAYIN-STATE = 'NJ'
NOPAYIN-ZIP-FIRST-FIVE = 07001

Expected output:

HOLD-STREET = '123456789012345678901234567890' (first 30 chars; chars 31–32 truncated)
ADDR-LINE2 = 'CITY NJ 07001 '

Verifies: UNSTRING overflow into a shorter receiving field — COBOL truncates to the PIC size.

TC-09: City portion exceeds HOLD-CITY's 15 characters

Input fields:

NOPAYIN-ADDRESS-SEG01-FORMAT = '1 MAIN/NORTH BERGEN HEIGHTS ' (20 chars after '/')
NOPAYIN-STATE = 'NJ'
NOPAYIN-ZIP-FIRST-FIVE = 07047

Expected output:

HOLD-CITY = 'NORTH BERGEN HE' (first 15 chars; "IGHTS" truncated)
ADDR-LINE2 = 'NORTH BERGEN HE NJ 07047 '

Verifies: City truncation at HOLD-CITY PIC X(15) boundary.

Category 3 — State Field Edge Cases
TC-10: Single-character state with trailing space

Input fields:

NOPAYIN-ADDRESS-SEG01-FORMAT = '1 MAIN ST/SOMETOWN '
NOPAYIN-STATE = 'N ' (one char + space)
NOPAYIN-ZIP-FIRST-FIVE = 00000

Expected output:

ADDR-LINE2 = 'SOMETOWN N 00000 '

Verifies: NOPAYIN-STATE DELIMITED BY ONE-SPACE — stops at the first space, yielding only 'N'.

TC-11: Full two-character state (no trailing space)

Input fields:

NOPAYIN-STATE = 'NY'

Expected output:

State in ADDR-LINE2 = 'NY' (DELIMITED BY ONE-SPACE finds no space → entire PIC XX used)

Verifies: Fully populated state field passes through completely.

Category 4 — Low-Value (Null) Character Cleansing
TC-12: LOW-VALUES embedded in street address

Input fields:

NOPAYIN-ADDRESS-SEG01-FORMAT = '123 MAIN' + X'00' + 'ST/NEWARK '
NOPAYIN-STATE = 'NJ', ZIP = 07102

Expected output:

After INSPECT: ADDR-LINE1 = '123 MAIN ST ' (null replaced with space)

Verifies: INSPECT ADDR-LINE1 REPLACING ALL LOW-VALUES BY SPACES (added by Richard Blumenfeld July 21 2009).

TC-13: LOW-VALUES in city portion (ADDR-LINE2)

Input fields:

NOPAYIN-ADDRESS-SEG01-FORMAT = '55 OAK/CAM' + X'00' + 'DEN '
NOPAYIN-STATE = 'NJ', ZIP = 08101

Expected output:

INSPECT replaces null: ADDR-LINE2 = 'CAM DEN NJ 08101 '

Verifies: INSPECT ADDR-LINE2 REPLACING ALL LOW-VALUES BY SPACES.

TC-14: All-LOW-VALUE address field

Input fields:

NOPAYIN-ADDRESS-SEG01-FORMAT = 44 bytes of X'00'
NOPAYIN-STATE = 'NJ', ZIP = 07102

Expected output:

UNSTRING finds no '/' in all-null data → entire field goes to HOLD-STREET (30 bytes of X'00')
ADDR-LINE1 = 30 spaces (INSPECT replaces all LOW-VALUES)
ADDR-LINE2 = ' NJ 07102 '

Verifies: Full null-cleansing path where entire address is binary zeros.

Category 5 — File-Level and Loop Boundary Tests
TC-15: Empty input file (zero records)

Setup: NOPAYIN-FILE contains no records.

Expected behavior:

200-HSKG: Opens files, 9000-READ → AT END sets END-FLAG = 'Y'
1000-MAIN-PROCESSING loop: never entered
300-WRAP-UP summary output:
*************************************
RESULTS OF NOPAYADD EXECUTION FOLLOWS;
*************************************
THE # OF RECORDS PROCESSED WAS 0000000
*************************************
END OF REPORT////////////////////////

Both files closed; STOP RUN

Verifies: Empty-file handling; priming read; END-FLAG 88-level; RECS-WRITTEN stays at VALUE ZERO.

TC-16: Single-record input file

Setup: NOPAYIN-FILE contains exactly 1 valid 281-byte record.

Expected behavior:

Priming read succeeds; loop runs once; RECS-WRITTEN = 0000001
9000-READ inside loop hits AT END → END-FLAG = 'Y'; loop exits

Verifies: Single-iteration loop; counter increments from 0 to 1.

TC-17: Multi-record file — counter fidelity and re-initialization

Setup: NOPAYIN-FILE contains exactly 5 records.

Expected behavior:

Loop runs 5 times; RECS-WRITTEN = 0000005
Each iteration: AREA1 and NOPAYOUT-RECORD re-initialized (no cross-record bleed)

Verifies: INITIALIZE per iteration prevents residual data; counter accumulation.

Category 6 — Record-Type Pass-Through (No Branching)
TC-18: All six NOPAYIN-RECORD-TYPE values processed identically

The program contains NO conditional logic on NOPAYIN-RECORD-TYPE.

Setup: Six input records, each with a different RECORD-TYPE:

Record

	

NOPAYIN-RECORD-TYPE

	

88-level name (from source)


1	'1'	ONE-HUNDRED-PERCENT-OFFSET
2	'2'	PENDED-WEEK
3	'3'	OTHER-PAYMENT
4	'4'	CURRENT-CWE-CHANGE
5	'5'	UI-CLAIM-IS-BYE
6	'6'	WW-CREDIT

All share: '10 TEST ST/TESTVILLE ', State 'NJ', ZIP 07000.

Expected output:

6 identical ADDR-LINE1/ADDR-LINE2 outputs; each record's NOPAYOUT-RECORD-TYPE matches input
RECS-WRITTEN = 0000006

Verifies: Record-type-agnostic processing; 88-levels defined but never referenced in PROCEDURE DIVISION.

TC-19: Unexpected record-type value (not '1'–'6')

Input: NOPAYIN-RECORD-TYPE = 'X'

Expected output: Processed identically — no abend, no skip.

Verifies: No runtime guard on record type.

Category 7 — Non-Address Field Preservation
TC-20: Financial and identity fields are byte-for-byte copies

Input fields (selected):

NOPAYIN-SSN = packed 123456789
NOPAYIN-WBR = 1234.56
NOPAYIN-WBA = 0567.00
NOPAYIN-CLAIM-BALANCE = packed -000012345.67
NOPAYIN-EARNINGS-AMOUNT1 = 0100.50
NOPAYIN-SUPPRESSION = '07'

Expected output: All values byte-identical in NOPAYOUT-* fields (via MOVE NOPAYIN-RECORD TO NOPAYOUT-RECORD). Only ADDR-LINE1/ADDR-LINE2 (bytes 282–341) differ from the input.

Verifies: Group MOVE preserves all 281 input bytes.

Category 8 — ADDR-LINE2 STRING Capacity Analysis
TC-21: Maximum possible ADDR-LINE2 content

Worst case:

HOLD-CITY: 15 chars (no double-space → all 15 used)
NOPAYIN-STATE: 2 chars
NOPAYIN-ZIP-FIRST-FIVE: 5 chars
Separating spaces: 3

Total: 15 + 1 + 2 + 1 + 5 + 1 = 25 chars → always fits in ADDR-LINE2 PIC X(30).

Verifies: STRING can never overflow ADDR-LINE2 under any input combination.

Summary Matrix

TC

	

Category

	

Key Condition Tested

	

Paragraph / Statement Exercised


01	Happy path	Normal street/city split	1100-PROCESS-ADDRESS: UNSTRING, STRING
02	Happy path	Multi-word city (interior spaces)	STRING DELIMITED BY TWO-SPACES
03	Happy path	Long street near 30-char limit	UNSTRING → HOLD-STREET PIC X(30)
04	Delimiter	No '/' in address	UNSTRING fallback — all to HOLD-STREET
05	Delimiter	'/' at position 1	Empty street, city-only parse
06	Delimiter	'/' at end	Street-only, empty city
07	Delimiter	Multiple '/' characters	UNSTRING stops after 2 INTO fields
08	Overflow	Street > 30 chars	HOLD-STREET PIC X(30) truncation
09	Overflow	City > 15 chars	HOLD-CITY PIC X(15) truncation
10	State	Single-char state + trailing space	STRING DELIMITED BY ONE-SPACE
11	State	Full 2-char state	STRING — no delimiter found → full field
12	Cleansing	Null in street	INSPECT ADDR-LINE1 REPLACING LOW-VALUES
13	Cleansing	Null in city	INSPECT ADDR-LINE2 REPLACING LOW-VALUES
14	Cleansing	All-null address	Full null-cleanse + no-delimiter path
15	File boundary	Empty file	200-HSKG priming read → immediate EOF
16	File boundary	Single record	One-iteration loop
17	File boundary	Multi-record	Counter accumulation, re-INITIALIZE
18	Record type	All six 88-level values	No branching — identical processing
19	Record type	Undefined type value	No guard — passes through
20	Preservation	Financial/identity fields	Group MOVE fidelity
21	STRING sizing	Max ADDR-LINE2 content	STRING never exceeds PIC X(30)

The suite covers 21 test cases across 8 categories, all grounded in the actual COBOL source :
NOPAYADD.txt

What's Covered
Happy path (TC-01–03) — Normal UNSTRING on '/', STRING formatting with TWO-SPACES / ONE-SPACE delimiters, ZIP+4 exclusion
Delimiter edge cases (TC-04–09) — No delimiter, leading/trailing '/', multiple slashes, overflow into HOLD-STREET PIC X(30) and HOLD-CITY PIC X(15)
State formatting (TC-10–11) — NOPAYIN-STATE DELIMITED BY ONE-SPACE with 1-char and 2-char states
Null cleansing (TC-12–14) — The INSPECT ... REPLACING ALL LOW-VALUES BY SPACES statements (added July 2009 by Richard Blumenfeld)
File boundaries (TC-15–17) — Empty file, single record, multi-record counter and re-INITIALIZE isolation
Record-type pass-through (TC-18–19) — All six 88-level values ('1'–'6') plus undefined values; confirms the program has no branching on record type
Field preservation (TC-20) — Group MOVE NOPAYIN-RECORD TO NOPAYOUT-RECORD fidelity for all 281 input bytes
STRING capacity proof (TC-21) — Maximum possible ADDR-LINE2 = 25 chars, always fits in PIC X(30)
Would you like me to take a next step with this test suite?

Generate as a DOCX document

Generate sample input data files

Deep-dive a specific test case

_Citations:_
- Citation 1
- Citation 2
- Citation 2

## v5-Q7

**Q:** I'm rotating off. Put together a handoff summary of the daily check reprint flow — ZUMDA1R1 and DXCB103U and anything downstream — for the engineer replacing me. They won't have this chat history.

**A** (11:29):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

I've gathered everything from the JCL source, the job-level analysis, and the COBOL business-rules documentation for all three layers of this flow. Here's a self-contained handoff summary built from those sources.

Handoff Summary — Daily UI Check Reprint Flow (ZUMDA1R2 → ZUMDA1R1 → DXCB103U)

Handoff Summary — Daily UI Check Reprint Flow

Prepared: September 2, 2026 Scope: The daily batch pipeline that generates UI (Unemployment Insurance) benefit checks for non-direct-deposit claimants and copies reprint-eligible records into a 5-day rolling VSAM file. Covers jobs ZUMDA1R2, ZUMDA1R1, and program DXCB103U.

Provenance: This summary is synthesized from the JCL source (ZUMDA1R1.txt, ZUMDA1R2.txt), the extracted job-level documentation (ZUMDA1R1.md, ZUMDA1R2.md), and the COBOL business-rules documentation (DXCB103U.md, UIMI0440.md). Where a statement draws on a single source, the document is cited inline. Coverage is bounded by the knowledge base — dynamically called programs, operator-DEMANDed jobs, and manually run streams may not appear here.

1. Big Picture — What This Flow Does

Every day, the LOOPS subsystem issues UI benefit checks for claimants who are not on direct deposit. The pipeline:

Extracts eligible payment records from the LoopPay VSAM cluster
Routes them to seven payment delivery channels (paper checks, direct-debit banks, electronic bill pay, etc.)
Validates and formats the paper-check subset into an 806-byte laser-print check detail file
Writes every processed check record into a reprint VSAM so spoiled checks can be reprinted
Copies the day's reprint records into a 5-day rolling reprint VSAM (the DXCB103U step)
Archives everything to tape (permanent) and disk (weekly) GDGs
2. Job Sequence and Dependencies
ZUMDA1R2  ──(produces NONDD.DTL)──►  ZUMDA1R1
                                        │
            ZUMDA1R1 steps (in order):
            ├─ IEFBR14    — cleanup stale UI.CHKS.DTL
            ├─ TEST1      — verify NONDD.DTL is readable
            ├─ VERIFYUI   — validate records (VERFYUI2)
            ├─ UIMI0063   — generate check detail (UIMI0440 via DB2)
            ├─ EMPTYIT    — fallback: create empty UI.CHKS.DTL if UIMI0063 failed
            ├─ BACKUP1    — tape GDG backup (EXPDT=99000, permanent)
            ├─ BACKUP2    — disk GDG backup (weekly)
            └─ DXCB103U   — copy today's UIVSAM → UIVSAM5 (reprint accumulation)

Prerequisite
CICS region CICJPAF must be down before either job runs. Both JCL headers state this explicitly.
Restart rules
Both jobs: restart from the beginning (IEFBR14 step) if any step fails.
ZUMDA1R1 has restart criticality 9 (highest).
3. Upstream Job: ZUMDA1R2 — Payment Channel Routing

Source: ZUMDA1R2.txt, ZUMDA1R2.md

ZUMDA1R2 reads the LoopPay VSAM cluster (LAK2LDXP.TEMP.VSAM.LOOPPAY.CLUSTER) and splits it into seven payment channels. The channel that matters for the check-reprint flow is NONDD (non-direct-deposit).

Step

	

Program

	

What It Does


IEFBR14	IEFBR14	Deletes 7 prior-run output files (DDBNKUI, DDBNKTUC, DDBNKEB, DDPRT, NONDD, EBPAY, DDBNKPUA)
COPY	SORT	Backs up entire LoopPay VSAM → GDG MAIL.LOOPPAY.BCKUP(+1), LRECL 323
REMOVE	SORT	Filters: SKIPREC=1 (skip header), then INCLUDE where pos 45 = '0' AND pos 284 = space / '0' / '1'
UIMI0143	UIMI0143 via DB2	Routes each filtered record to exactly 1 of 7 channels — paper-check records go to NONDD (ZUMDA1R1.NONDD.DTL, LRECL 323)
BACKUP	SORT	NONDD → GDG NONDD.BCKUP(+1), LRECL 323
BACKUP2	SORT	EBPAY → GDG ZUMDA1R2.EBPAY.BCKUP(+1), LRECL 360

Key output consumed downstream: LAK2LDXP.ZUMDA1R1.NONDD.DTL (323-byte FB records — the "Non-Direct-Deposit Detail File"). This is the primary input to ZUMDA1R1.

4. Main Job: ZUMDA1R1 — Check Generation, Backup, and Reprint Copy

Source: ZUMDA1R1.txt, ZUMDA1R1.md

Previously known as L2BPD4. Was split into two jobs in Dec 2004 (ZUMDA1R2 handles the upstream extraction).

Coupling warning: The JCL header says "IF THIS JOB IS CHANGED, JOB LCSLOPCR MUST ALSO BE CHANGED." LCSLOPCR is a parallel/companion job — any structural changes need to be mirrored there.

Step-by-step breakdown
Step 1 — IEFBR14 (Cleanup)

Deletes LAK2LDXP.ZUMDA1R1.UI.CHKS.DTL so the run starts clean.

Step 2 — TEST1 (IDCAMS REPRO, COND=(0,NE))

Reads exactly 1 record from NONDD.DTL into a temp file (&&TEST, LRECL 323). This is a canary test — if the file is empty or inaccessible, everything downstream is skipped.

Step 3 — VERIFYUI (VERFYUI2, COND=(0,NE))

Validates all NONDD records against the DATECARD processing date. Produces a printed verification report to SYSOUT=J. Non-zero RC → all downstream steps skipped.

Step 4 — UIMI0063 (UIMI0440 via IKJEFT01/DB2, COND=(0,NE))

This is the main check generation step. Executes program UIMI0440 under DB2 plan UIMI0440.

Inputs:

DATEIN → PROD.CNTLLIB(DATECARD)
CODELOOP → VSAM.CODES.CLUSTER (code tables 004, 112, 157, 175, 257, 330, 357, 457)
REPRINT → VSAM.UIVSAM.CLUSTER (opened I-O — reads history and writes today's reprint records)
CHECKREC → ZUMDA1R1.NONDD.DTL (the NONDD records from ZUMDA1R2)

Outputs:

PRNTDATA → ZUMDA1R1.UI.CHKS.DTL (806-byte FB check detail records for laser printing)
PRNTDAT2 → DUMMY (secondary output intentionally suppressed)

What UIMI0440 does to each payment record (from UIMI0440.md):

Checks eligibility — BP88-PRINT-IND must be 0, 1, or spaces, AND BP88-VOID-IND must be 0
Original checks get today's system date; reprints (BP88-PRINT-IND = 1) use the DATECARD date
Integrity check — sums pseudo-check-number digits + check amount, negates, compares to BP88-INTEGRITY-BYTES. Advisory only — processing continues even on mismatch
Formats all check fields: SSN (XXX-XX-XXXX), amounts in words, local office address (table 112), payment type codes (EB/EC/TX/TY/TZ/EU/WF/SE), mail dates
Bank account assignment: regular UI → 0003921317963; FSC/TUCX/TUCY/TUCZ → 0003921317992
Writes each record to the REPRINT VSAM (VSAM.UIVSAM.CLUSTER) keyed by sequence# + SSN — handles duplicate keys by incrementing sequence# and retrying
Writes the formatted 806-byte record to the check detail output file
Writes a clone record for audit/mapping
Step 5 — EMPTYIT (IDCAMS, COND=(00,EQ,UIMI0063))

Only fires when UIMI0063 succeeded (RC=0) — wait, re-reading: COND=(00,EQ,UIMI0063) means this step is skipped when UIMI0063 RC = 0. It fires when UIMI0063 failed (RC ≠ 0). Creates an empty placeholder UI.CHKS.DTL (LRECL 806) so downstream backup steps and job L2BPD4L have a valid input file.

Step 6 — BACKUP1 (SORT, unconditional)

Copies UI.CHKS.DTL → tape GDG UI.CHKS.BCKUP(+1). LRECL 806, EXPDT=99000 (permanent retention), DATACLAS=TAPEMEDC on SILO.

Step 7 — BACKUP2 (SORT, unconditional)

Copies UI.CHKS.DTL → disk GDG UI.WKLY.BCKUP(+1). LRECL 806, SYSALLDA.

Step 8 — DXCB103U (COND=(0,NE))

Only runs if all prior steps succeeded. See next section.

5. The Reprint Copy Step: Program DXCB103U

Source: DXCB103U.md, ZUMDA1R1.txt

Purpose

Copies all records from the primary UI Reprint VSAM (UIVSAM.CLUSTER) into the 5-day rolling UI Reprint VSAM (UIVSAM5.CLUSTER), stamping each record with today's run date. This builds a rolling 5-day window of reprint-eligible checks.

JCL DD statements
//SYSIN    DD  DSN=LAK2LDXP.PROD.CNTLLIB(DATECARD),DISP=SHR
//REPRINT  DD  DSN=LAK2LDXP.VSAM.UIVSAM.CLUSTER,DISP=SHR
//REPRINT5 DD  DSN=LAK2LDXP.VSAM.UIVSAM5.CLUSTER,DISP=SHR

Processing logic
Startup banner — displays PROGRAM DXCB103R BEGINNING>>>>>>>>>>>>>>>>>>>>>> (note: the display message says DXCB103R despite the load module being DXCB103U)
Date parsing — reads DATECARD via SYSIN, extracts B040-DAILY-DATE, parses into Month/Day/Year, reassembles as DATE-RUN in YYYYMMDD format
Open REPRINT (input, read-only) — accepts status 00 or 97; anything else → RC 16 ABEND
Open REPRINT5 (output, EXTEND/APPEND mode) — new records are appended after existing ones; same status validation
Position to first record — sets REPRINT-SSN = 0, REPRINT-SEQUENCE = 0, issues START > REPRINT-KEY
Read loop — reads sequentially until EOF:
Maps REPRINT-SSN → REPRINT5-SSN (unchanged)
Maps REPRINT-SEQUENCE → REPRINT5-SEQUENCE (unchanged)
Replaces the date: REPRINT5-DATE = DATE-RUN (today's date, overriding the original)
Maps REPRINT-REST → REPRINT5-REST (everything else copied as-is)
Writes to REPRINT5 in append mode
Increments RECORDS-READ and RECORDS-WRITTEN counters
Completion summary — displays total records read vs. written (should always match on a normal run)
Closes both files
Error handling
Any OPEN, START, READ, or WRITE failure → displays error message with file status, closes both files, sets RC = 16, stops
The REPRINT5 WRITE failure message is: 'A SEVERE PROBLEM WITH THE REPRINT5 FILE EXISTS'
Key behavior to watch
REPRINT5 is opened in EXTEND mode — it accumulates across days. Someone/something else must purge records older than 5 days. That purge process is not documented in this knowledge base.
The date stamp replacement means you can identify which day's run contributed each record by looking at REPRINT5-DATE.
RECORDS-READ should always equal RECORDS-WRITTEN. A mismatch means a write failed mid-run.
6. Key Datasets — Quick Reference

Dataset

	

LRECL

	

Format

	

Who Writes

	

Who Reads

	

Retention


TEMP.VSAM.LOOPPAY.CLUSTER	323	VSAM	Upstream (payment posting)	ZUMDA1R2	Ongoing VSAM
ZUMDA1R1.NONDD.DTL	323	FB	ZUMDA1R2 (UIMI0143)	ZUMDA1R1 (TEST1, VERIFYUI, UIMI0063)	Recreated each run
VSAM.CODES.CLUSTER	—	VSAM KSDS	Operations	UIMI0440 (read-only)	Ongoing VSAM
VSAM.UIVSAM.CLUSTER	—	VSAM KSDS	UIMI0440 (I-O writes)	UIMI0440, DXCB103U (read)	Ongoing VSAM
VSAM.UIVSAM5.CLUSTER	—	VSAM KSDS	DXCB103U (extend/append)	Downstream reprint consumers	Rolling (purge not in KB)
ZUMDA1R1.UI.CHKS.DTL	806	FB	UIMI0440 (or EMPTYIT placeholder)	BACKUP1, BACKUP2, L2BPD4L	Recreated each run
ZUMDA1R1.UI.CHKS.BCKUP(+1)	806	FB	BACKUP1 (SORT COPY)	Recovery/audit	Permanent (EXPDT=99000, SILO tape)
ZUMDA1R1.UI.WKLY.BCKUP(+1)	806	FB	BACKUP2 (SORT COPY)	Recovery	Disk GDG (rolling)
PROD.CNTLLIB(DATECARD)	—	—	Operations	VERFYUI2, UIMI0440, DXCB103U	Control card, maintained externally
7. Common Failure Scenarios and What To Do

Symptom

	

Likely Cause

	

Action


TEST1 fails (RC ≠ 0) — all downstream steps flush	NONDD.DTL is empty or missing	Check ZUMDA1R2 — did it run? Did UIMI0143 produce the NONDD file?
VERIFYUI fails	Date mismatch or corrupt records in NONDD	Check the VERFYUI2 verification report (SYSOUT=J). Verify DATECARD is current.
UIMI0063 integrity warning in sysout	CHECK INTEGRITY PROBLEM EXISTS!	Advisory only — UIMI0440 does NOT stop. Investigate the input LoopPay records, but the checks were still generated.
EMPTYIT runs (creates empty UI.CHKS.DTL)	UIMI0063 step returned RC ≠ 0	The empty file exists so BACKUP1/BACKUP2 don't fail. Investigate why UIMI0440 failed (DB2 plan issue? VSAM file locked?).
DXCB103U ABENDs with INVALID RETURN CODE ON OPEN FOR FILE REPRINT	UIVSAM cluster unavailable or locked	Verify CICS region CICJPAF is down. Check if another job has an exclusive lock on the VSAM.
DXCB103U ABENDs with SEVERE PROBLEM WITH THE REPRINT5 FILE	UIVSAM5 write failure — possibly full, locked, or corrupt	Check VSAM catalog for UIVSAM5 space. May need IDCAMS VERIFY or a cluster redefine.
RECORDS-READ ≠ RECORDS-WRITTEN in DXCB103U output	Mid-run write failure	The program would have ABENDed with a message. Check sysout for the actual file status.
8. Historical Change Log (Selected)

Per the JCL comment blocks (most recent first):

Date

	

Who

	

What


2020-06-15	LAARODM	Latest change to ZUMDA1R1
2020-05-20	LAARODM	Added PUA channel (DDBNKPUA) to ZUMDA1R2 after bank xmit fix
2013-01-15	ODJBLUM	Removed Finalist/Mailstream from ZUMDA1R1
2011-11-09	ODJBLUM	Removed step DXCB103U (temporarily) — later re-added
2011-06-09	ODJBLUM	Added BACKUP2 (weekly disk backup)
2009-02-04	ODJBLUM	Added step DXCB103U to ZUMDA1R1
2004-12-16	ODJHAUG	Split original L2BPD4 into ZUMDA1R2 + ZUMDA1R1
2004-03-23	ODJKUZI	Added UIMI0143 step for direct deposit
2001-01	ODJCHRU	Changed job name from L2BPD4 to ZUMDA1R1, changed NEWBP06S to UIMI0063
1999-07-01	ODJENDD	First Union bank changes — increased REPRINT file from 710 to 723, check file from 699 to 712
9. What Is NOT In This Knowledge Base

The following are known gaps — you'll need to find these through other documentation or SMEs:

UIVSAM5 purge process — DXCB103U appends daily, but nothing here documents what cleans up the 5-day rolling window
LCSLOPCR job — the companion job that must be kept in sync with ZUMDA1R1 changes
L2BPD4L job — mentioned in JCL comments as consuming UI.CHKS.DTL downstream; not in the KB
UIMI0440 DB2 plan and tables — the program uses DB2 (plan UIMI0440) but the database schema is not documented here
CODELOOP table values — the VSAM codes cluster layouts are defined in copybooks (e.g., T120TABL.cpy) but the actual populated values are operations-maintained
CA-7 schedule and triggers — the sequencing of ZUMDA1R2 → ZUMDA1R1 is managed in CA-7; the specific trigger/dependency definitions are outside this KB slice
Code promotion / deployment process — any changes to UIMI0440 or DXCB103U follow a change-management process that is documented elsewhere

This covers the full end-to-end flow from the retrieved JCL and COBOL documentation.
ZUMDA1R1.txt
ZUMDA1R1.md
DXCB103U.md
UIMI0440.md
ZUMDA1R2.md
ZUMDA1R2.txt
 A few things to flag for your replacement:

Key Takeaways for the New Engineer

Three-job chain: ZUMDA1R2 (channel routing) → ZUMDA1R1 (check generation + backup) → the DXCB103U step at the end of ZUMDA1R1 (reprint accumulation). All gated by COND=(0,NE) — any upstream failure skips everything downstream.
ZUMDA1R1.txt
ZUMDA1R1.md

UIMI0440 is the heavy lifter — it's the DB2/COBOL program that formats checks, writes to the REPRINT VSAM, and produces the 806-byte laser-print file. The integrity check is advisory only — it warns but never stops processing.
UIMI0440.md

DXCB103U is a simple copy-and-datestamp — reads all of UIVSAM sequentially, appends to UIVSAM5 with today's date replacing the original. REPRINT5 opens in EXTEND mode and accumulates. The purge mechanism for the 5-day window is not documented in the knowledge base — that's a question for the operations team.
DXCB103U.md

Twin-job coupling — any change to ZUMDA1R1 must also be applied to LCSLOPCR. The JCL header says this explicitly.
ZUMDA1R1.txt

Would you like me to go deeper on any part of this flow?

Deep-dive on UIMI0440

Generate a downloadable DOCX

CA-7 schedule and triggers

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 5
- Citation 6
- Citation 1
- Citation 2
- Citation 4
- Citation 3
- Citation 1

## v5-Q8

**Q:** What do the ZLPDYOR1 through ZLPDYOR9 jobs do in the daily stream?

**A** (11:30):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

The knowledge base does not have any jobs named ZLPDYOR1 through ZLPDYOR9. Here's what I found:

Direct JCL source lookup — Attempts to retrieve ZLPDYOR1.txt and ZLPDYOR2.txt returned empty results, meaning these JCL members are not indexed in the Daily CA-7 v2 space.
Job purpose index (05_job_purpose_index.md) — The large alphabetical job index was returned in several passages covering the ZLPD* range (from ZLPDNER* through ZLPDSTR* and beyond), but no ZLPDYOR* entries appear in any of them.
Keyword searches for "ZLPDYOR" across all available spaces returned no matches.
What This Could Mean

There are a few possibilities:

Typo in the job name — The LOOPS daily stream uses the convention ZLPDxxxN where xxx is a 2–3 character functional code and N is the IMS database partition number (0–9). There are many ZLPD jobs with similar-looking codes. Some close-ish documented families include:

ZLPDEUR0–ZLPDEUR9 (runs program DXCBD66E — new-claim extraction per DB partition)
ZLPDERR1–ZLPDERR9 (error/rerun processing)
ZLPDSTR0–ZLPDSTR9 (plan/resource distribution extraction via EZTPIM2K)

The jobs exist but are outside knowledge-base coverage — The Daily CA-7 v2 space covers 1,018 LOP jobs from the DOLDAILYD061526 forecast. If ZLPDYOR* jobs were added after June 2026, or belong to a non-LOP subsystem, they wouldn't be here.

The jobs are operator-DEMANDed or manually run — Jobs that aren't in the scheduled CA-7 forecast wouldn't have been captured in this space.

Could you double-check the exact spelling? If you have a JCL listing or CA-7 screen showing the job, I can try to match the functional code or program name to something documented here.

How would you like to proceed?

Verify the job name and try again

Search by program or dataset name

Show all ZLPD* job families
