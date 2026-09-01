# 2026-09-01_1331_quick_playwright_v5

- **Backend:** quick (transport: playwright)
- **Bank:** v5 (`question_sha256` 7babe64d260e…)
- **Agent:** engineering_onboarding_specialist (`093ac4e3-0712-481e-af95-9ddc5e4fc734`)
- **Conversation:** `06f3fe79-be0d-4582-b3a9-086dd5f7a687`
- **Model:** Advanced
- **Started:** 2026-09-01 13:21
- **Finished:** 2026-09-01 13:31
- **Status:** complete
- **Questions asked:** 8, answered: 8

## v5-Q1

**Q:** I'm picking up the daily NOPAY certification file generation process. Which job runs it, and what programs execute in sequence? What does each step do?

**A** (13:22):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

The daily NOPAY certification file generation is handled within the broader Daily Certification Extracts job. Here's the complete breakdown.

Job: L2DCWEXR

This job belongs to subsystem CWE1 (Daily Process) and generates the Daily Certification Extracts Report using both the PAYVSAM (Loop Pay) and NOPAY backup GDG files. It has a Restart Criticality of 1 (highest).
L2DCWEXR.md

Important context: The NOPAY file is processed together with the LOOPPAY file in a single job — they are not generated independently.

Step-by-Step Execution Sequence
L2DCWEXR Job Steps

\#

	

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
The 12 Output Files from DXCBDA2R (Step 8)

The core COBOL program categorizes transactions based on the DATECARD processing date and writes them to these audit buckets :
L2DCWEXR.md

ADTPRVWK — Previous week's pay period transactions
ADTD0629 — Deduction Code 0629 transactions
ADTD0928 — Deduction Code 0928 transactions
ADTONEWK — One-week pay cycle transactions
ADTTWOWK — Two-week (bi-weekly) pay cycle transactions
ADTCWE14 — Current Week Earnings over a 14-day period
ADTNEARN — Newly calculated/adjusted earnings
ADTWEARN — Standard weekly earnings
ADTLPAYS — Last/final pay transactions (e.g., terminations)
VOIDI1FL — Voided/reversed payment transactions
BYPASSFL — Transactions bypassed from standard processing
DAILYREP — Formatted Daily Audit Report (132-byte records)
Key Design Points
Conditional gating: Steps 3–6 and 8–9 are skipped if any prior step returns a non-zero RC. Steps 1, 2, and 7 run unconditionally.
L2DCWEXR.md
Shared access: Both GDG backups are opened in shared mode, so other concurrent jobs are not blocked.
L2DCWEXR.md
Header skip: Both IDCAMS REPRO steps skip the first record (header/control record) of their respective VSAM backups.
L2DCWEXR.md
Record sizes: LOOPPAY = 323 bytes; NOPAY = 281 bytes.
L2DCWEXR.md
Restart: The JCL header documents restart procedures — most data-preparation steps restart from CLEANUP1; the two cleanup steps restart from themselves.
L2DCWEXR.txt
A Note on NOPAYSUP

The knowledge base also documents a separate program called NOPAYSUP, which suppresses duplicate certifications between the LOOPPAY and NOPAY files. It executes after DXCBDSUP has completed suppression on the LOOPPAY file, in a different job context — not within L2DCWEXR itself.
NOPAYSUP.txt
NOPAYSUP.txt

What would you like to explore next?

How does DXCBDA2R categorize transactions?

Tell me about the NOPAYSUP suppression program

What are the restart procedures for L2DCWEXR?

What upstream jobs produce the NOPAY and LOOPPAY backups?

_Citations:_
- Citation 1
- Citation 1
- Citation 1
- Citation 2
- Citation 1
- Citation 1
- Citation 3
- Citation 4
- Citation 5

## v5-Q2

**Q:** Our operations runbook says program DXCB098B converts NOPAY EB records to VSAMPAY format in job ZUMDA2R1. Can you pull up its logic for me?

**A** (13:23):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

Good news — both DXCBO98B and job ZUMDA2R1 are well-documented in the knowledge base. However, I need to flag a naming correction first.

Name Clarification

Your runbook says DXCB098B, but the program name in both the JCL source and the COBOL analysis document is actually DXCBO98B (letter O, not digit 0). This follows the LOOPS DXCB* batch naming convention. Please verify your runbook — the program the knowledge base documents is DXCBO98B.
ZUMDA2R1.txt
DXCBO98B.md

Program DXCBO98B — NOPAY EB → PAYVSAM Converter

This is a batch COBOL program (Main/Driver module, sequential file access, no MQ). It reads 281-byte NOPAY EB records from INFILE and writes 360-byte PAYVSAM-format EB records to OUTFILE.
DXCBO98B.md

Where It Runs in Job ZUMDA2R1

The JCL comment directly above the step reads: *T.M.CONVERT NOPAY EB RECORD TO VSAMPAY. It executes at step DXCBO98B, conditioned COND=(0,NE) (skipped if any prior step fails).
ZUMDA2R1.txt

INFILE → LAK2LDXP.ZUMDA2R1.MAIL.NOPAYEB.DTL (281-byte FB, produced by the earlier INCLEB sort step which filters NOPAY VSAM records where Transitional UI Pay is between X'0064' and X'00C7')
OUTFILE → LAK2LDXP.ZUMDA2R1.MAIL.VSAMPAY.DTL (360-byte FB, newly created)
Processing Logic (24 Functional Steps)

The program follows a simple open → prime read → loop → summary → close pattern:

1. Open Files — Opens NOPAY input (read) and PAYVSAM output (write).

2. Prime Read — Reads the first NOPAY record; if EOF immediately, skips to step 23.

3–21. Per-Record Conversion Loop — For each record:

Table

\#

	

Functionality

	

What Happens


3	Map Claimant ID	NOPAY-SSN → EB-SSN; NOPAY-PC → EB-PC; NOPAY-DOC → EB-DOC
4	Map Geographic Fields	ZIP (5+4 digits), Responsible Local Office, Local Office — all direct transfers
5	Map Dates/Times	CWE Dates 1–4, Date Entered System transferred as-is; NOPAY-TIME-OF-ENTRY → EB-TIME-OF-CERT (repurposed as certification time)
6	Map Terminal/Operator	Entry Terminal ID → Cert Terminal ID; Entry Operator ID → Cert Operator ID
7	Set Decert/Check Defaults	Pseudo Check #, Actual Check #, Check Amount, Date Paid, Time of Decert → zeroes; Decert Terminal ID → spaces; Decert Operator ID → zero; Void Indicator → 0 (active)
8	Map WBR/WBA	Weekly Benefit Rate and Weekly Benefit Amount — direct transfer
9	Map Financial Amounts	Claim Balance, Earnings (CWE1/CWE2), Pension (CWE1/CWE2), Other Amount, Gross Amount
10	Map Work-Week Fields	Work-Week Earnings and Work-Week Indicators for CWE1 and CWE2
11	Map Health/Offset/UI	Health Amount, Offset Amounts (CWE1/CWE2), Transitional UI Payments (CWE1/CWE2)
12	Reformat Name	Input: LASTNAME/FIRSTNAME MIDDLENAME → split on /, split on space → reassemble as FIRST MIDDLE LAST in EB-FIRST-MIDDLE-LAST-NAME
View more

22. Loop — Read next NOPAY record, increment NUM-INPUT if found, set EOF='Y' if not; repeat steps 3–21.

23. Display Summary — Always runs (even if input was empty). Prints banner "E.B. records converted to payvsam" with TOTAL INPUT RECORDS (NUM-INPUT) and TOTAL OUTPUT RECORDS (NUM-TOT-OUTPUT).

24. Close Files — Close INFILE then OUTFILE.

Key Policy Rules (Hard-Coded Defaults)
Payment Type Indicator is always '3' — no exceptions
All decertification fields zeroed/blanked — these are new certifications, not decerts
Financial Institution Name always blank — NOPAY records have no banking info
Check Amount, Actual Check #, Pseudo Check #, Date Paid all zero — no payment is being issued at conversion time
Important Context Within ZUMDA2R1

This program is one step in a larger pipeline. The NOPAY EB records it consumes were pre-filtered by the INCLEB SORT step (which selects records from the NOPAY VSAM cluster where positions 217–218 have a binary value between X'0064' and X'00C7', i.e., Transitional UI Pay values of 100–199). The VSAMPAY output from DXCBO98B feeds into downstream mailing/check-generation processing in the remaining job steps.
ZUMDA2R1.txt
ZUMDA2R1.md

What would you like to explore next?

Walk me through the entire ZUMDA2R1 job flow

Show me the complete field mapping with positions

Trace the downstream consumers of the VSAMPAY output

_Citations:_
- Citation 1
- Citation 2
- Citation 2
- Citation 1
- Citation 1
- Citation 3

## v5-Q3

**Q:** An engineer's note says CICS transaction LOJ4S200 is one of the entry points for stimulus payment inquiries. Which program handles that transaction?

**A** (13:24):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

The knowledge base has no transaction by the name LOJ4S200, and I need to flag a structural issue with that identifier before we go further.

CICS Transaction ID Length Issue

Standard CICS transaction IDs are 1–4 characters long. LOJ4S200 is 8 characters, which means it cannot be a valid CICS transaction ID. The engineer's note may be conflating two different identifiers — possibly a 4-character transaction ID and a screen/conversation code. Here are some possibilities to check:

LOJ4 as the transaction + S200 as something else (a screen number, a segment identifier, or a conversation type)?
The documented LOOPS CICS transaction IDs in the knowledge base include LO4W (Online Payment), LO21 (Voice Payment), LODK, LODQ, and LODR (web-based inquiries) — none of which is LOJ4.
The conversation ID A200 is documented as an Inquiry type, classified as read-only. It's possible someone wrote "S200" when they meant "A200."
What Is Documented for "Stimulus"

The word "stimulus" in the knowledge base refers exclusively to batch mailroom processing, not a CICS inquiry transaction :
DXCB116E.md
L2DFACLT.md

Job L2DFACLT filters journal records for transaction types C010/C030/C060, transforms them into 500-byte Stimulus records via program DXCB116E, sorts them, and consolidates via program DXCBO29E to produce a STIMULUS GDG output file.
L2DFACLT.md
L2DFACLT.md
These are batch programs, not online CICS screens.
Recommendations

I cannot confirm or describe what LOJ4S200 is or which program handles it — the knowledge base has no process, program, screen, or transaction by that name. Before I can help further:

Check the runbook for a typo — could the transaction be LO4W (4 chars, Online Payment) and the screen/conversation A200 (Inquiry)?
If the intent is truly stimulus payment inquiry, the batch job L2DFACLT and its programs (DXCB116E, DXCBO29E) are the documented stimulus artifacts — but they're batch, not online inquiry.
The CSD (CICS System Definition) file — which would map transaction IDs to programs — is noted as missing from the knowledge base , so even valid transaction-to-program mappings cannot be confirmed from the held source.
code_issues_20260...
Would you like to explore one of these angles further?

Check LO4W or A200 conversation details

Review the batch stimulus processing (L2DFACLT)

Let me verify the name in our runbook first

_Citations:_
- Citation 1
- Citation 2
- Citation 2
- Citation 3
- Citation 4

## v5-Q4

**Q:** For the claims certification cycle, is the certification week ending date always a Saturday? Is that enforced anywhere in code I can point to, or is it convention?

**A** (13:25):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

Great question — this is well-documented in the knowledge base and the answer has an important nuance. Here's the full picture:

Short Answer: Derived by Construction, Not Enforced at Runtime

The overview document (00_ca7_daily_overview.md) states this directly :
00_ca7_daily_over...

"In the held daily programs, the Saturday week-ending date (CWE) is produced by construction, not validated at runtime."

In other words: every program that produces a CWE date computes it so it always lands on a Saturday — but in the documented programs, no active runtime guard rejects a non-Saturday value if one somehow got in.

Programs That Derive Saturday by Construction

Here are the documented mechanisms, each of which you can point to:

Table

Program

	

Mechanism

	

Source


UIMB0018	Uses DAYS-TO-PREV-SATURDAY-VALUES day-of-week offset tables to snap any date to the prior Saturday	
DXCBDSUP	Calls F6ADDF6 to get DOWSUB (1=Sun … 7=Sat), then applies a SUBTRAHEND/ADDVALUE table to step back to the preceding Saturday from a Julian day number	
DXCBDA2R	Paragraph 1300-GET-PREV-WEEKEND-DATE computes the previous weekend date using month-length addends	
UIMB0248 / UIMI0248	Computes REM(INTEGER-OF-DATE, 7) — only triggers weekly report when result = 6 (Saturday); non-Saturday dates silently skip the weekly report path	
UIMI0443	Derives the certification week FROM date by subtracting 6 days from the CWE TO date — implicitly assumes CWE is Saturday, producing a Sunday start	
QCREC3E	Computes expected CWE by adding 6 days to claim date (Sunday) → Saturday	
DXCBD65R	Adds day-of-week offsets to advance to the next Saturday; special policy rule: if base year begin date itself falls on Saturday (DOWSUB=7), it advances 7 days to the following Saturday rather than using the same day	
View more
The Commented-Out Guard

The closest thing to a runtime enforcement check was in UIMB0248. The BRE analysis describes a "confirm the week-ending date is a Saturday" validation rule, but the overview document explicitly notes :
00_ca7_daily_over...

"the corresponding guard in UIMB0248 source (IF WS-WEEKDAY NOT = 'SATURDAY' ..., lines 014650–014670) is commented out."

This means the validation exists in the source code but is inactive. UIMB0248 simply branches on the Saturday path and silently does nothing for non-Saturday inputs — it doesn't reject them.

What You Can Point An Engineer To
For the clearest derivation logic: DXCBDSUP — its CERT-SCHEDULE-CHECK paragraph has a full DOWSUB → SUBTRAHEND/ADDVALUE table that walks any payment date back to the preceding Saturday, with Julian-day arithmetic and leap-year handling.
DXCBDSUP.md
DXCBDSUP.md
For the "why no guard?" context: 00_ca7_daily_overview.md and the UIMB0248 source — the guard existed but was commented out.
00_ca7_daily_over...
For the policy rule: DXCBD65R — explicitly labeled as a Policy Rules entry: "Saturday is Never Used as the Same-Day Week Ending Date".
DXCBD65R.md
Coverage Caveat

This answer is bounded by the programs in the knowledge base. Programs, jobs, or streams outside the held slice (e.g., CICS online screens, IVR capture, or money-movement processes) may handle it differently, so a universal "Saturday is always enforced system-wide" claim cannot be confirmed from the knowledge base alone. Within the documented batch programs, Saturday is derived by construction in every case, but not validated at runtime in any.

Would you like to explore any of these further?

Deep dive into DXCBDSUP's CERT-SCHEDULE-CHECK

Examine UIMB0248's Saturday logic

DXCBD65R base-year Saturday policy

_Citations:_
- Citation 1
- Citation 1
- Citation 2
- Citation 9
- Citation 1
- Citation 8

## v5-Q5

**Q:** When does the yearly SOIL control-card update run, and what does an operator have to do before kicking it off?

**A** (13:26):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

The knowledge base has limited coverage of the specific "yearly SOIL on-request control-card run" you're asking about. Here's what is documented and what isn't:

What the Knowledge Base Says

The terminology glossary (06_terminology_glossary.md) describes SOIL as, among other things, a "yearly on-request control-card run".
06_terminology_gl...
 The key phrase is on-request — this indicates it is not on a fixed automated CA-7 schedule but is instead manually initiated (DEMANDed) by operations when the yearly cycle calls for it. The glossary does not document a specific calendar date or schedule trigger.

What the B040 Control Card Looks Like

The B040-DATE-CONTROL-CARD structure (from VERFYUI2.cbl.csv) includes annual-period fields that would need to be updated for a yearly run :
VERFYUI2.cbl.csv
VERFYUI2.cbl.csv

B040-ANNUAL-BEGIN-DATE — 9(8), position 49, "Annual beginning date for yearly processing"
B040-ANNUAL-ENDING-DATE — 9(8), position 57, "Annual ending date for yearly processing"

Every SOIL batch program (DXCRR05E, DXCRR78E, etc.) reads this control card from SYSIN at initialization and loads all date fields — daily, weekly, monthly, quarterly, and annual — into working storage.
UIMB0059.md
UIMI0061.md
DXCBD134.md

What the Daily SOIL Jobs Document (for Reference)

The documented daily SOIL jobs (ZLPD02U0–ZLPD02U9 for adjustment/balance processing, ZLPD09U0–ZLPD09U9 for balance reconciliation) follow a clear prerequisite pattern before execution :
ZLPD02U0.md
ZLPD02U2.md
ZLPD02U3.md

IDCAMS VERIFY (mandatory, unconditional first gate) — verifies three VSAM files: the IMS database data component (e.g., LOPD0002), the index component (LOPX0002), and the business codes reference table (VSAM.CODES.CLUSTER), using the VERIFY03 control card from the production control library
All three must return RC=0 or all downstream SOIL processing is blocked
IMS databases must be locked with exclusive access; CODES can be shared
The DATECARD control card with correct date values must be supplied via SYSIN
What Is NOT in the Knowledge Base

The knowledge base does not document:

When exactly the yearly on-request SOIL run is triggered (e.g., calendar year-end, state fiscal year-end, or at Treasury's request)
The specific job name or job stream for the yearly run (as distinct from the daily ZLPD02U* / ZLPD09U* jobs)
The operator procedure for preparing and submitting the yearly run — specifically, how the B040-ANNUAL-BEGIN-DATE and B040-ANNUAL-ENDING-DATE values are set and who approves them
Whether the yearly run uses the same DXCRR05E/DXCRR78E programs with different date-card parameters, or a different program entirely

These details live in the operations runbook and the CA-7 DEMAND procedures, which are outside the held documentation.

Recommendation

This is an area where you'd need to consult with the operations team or scheduling SME who manages the CA-7 DEMAND queue and the DATECARD maintenance procedures. The pattern for the daily SOIL jobs (VSAM VERIFY → exclusive IMS lock → DATECARD via SYSIN → DXCRR05E/DXCRR78E execution) is well-documented and likely applies to the yearly run as well, but confirming that — and the timing and operator checklist — requires the ops runbook.

Would you like to explore a related SOIL topic?

Daily SOIL job flow step-by-step

B040 control card structure detail

DXCRR05E program logic deep dive

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

## v5-Q6

**Q:** Generate a test suite for NOPAYADD's record handling — cover the main paths and edge cases, with the constants it actually uses.

**A** (13:28):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

I have all the source-level detail I need from NOPAYADD.txt and NOPAYADD.md in the Daily CA-7 space. Let me synthesize a comprehensive test suite grounded in the actual program constants and logic.

Provenance note: Every constant, field name, field size, delimiter, 88-level value, and paragraph name below is copied from the retrieved NOPAYADD.txt source code (COBOL source, LIBRMASTRALL / CA-7 daily schedule slice). The test case expected results are derived from the source logic — specifically from paragraphs 1100-PROCESS-ADDRESS, 1000-MAIN-PROCESSING, 200-HSKG, 9000-READ, and 300-WRAP-UP — and should be confirmed against actual program execution before being treated as an acceptance baseline. All sample data is synthetic.

NOPAYADD Test Suite — Record Handling

NOPAYADD Test Suite — Record Handling

Program: NOPAYADD (COBOL II Batch, LIBRMASTRALL) Purpose: Reformat the combined address field in NOPAY records (splitting at / delimiter) and write reformatted records to the output file before the FINALIST process. Sources: NOPAYADD.txt (source), NOPAYADD.md (business rules) — Daily CA-7 space Provenance: Expected outputs are derived from source paragraphs (1100-PROCESS-ADDRESS, 1000-MAIN-PROCESSING, 300-WRAP-UP). Confirm against actual execution.

Key Constants & Field Sizes (from WORKING-STORAGE and FD)

Item

	

Source Definition

	

Notes


HOLD-STREET	PIC X(30)	Max street length; part of AREA1
HOLD-CITY	PIC X(15)	Max city length; part of AREA1
ADDR-LINE1	PIC X(30)	Output address line 1 (street)
ADDR-LINE2	PIC X(30)	Output address line 2 (city/state/zip)
TWO-SPACES	PIC XX	STRING delimiter for city trimming
ONE-SPACE	PIC X	STRING delimiter for state trimming; also inserted as separator
NOPAYIN-ADDRESS-SEG01-FORMAT	PIC X(44)	Combined input address field
NOPAYIN-STATE	PIC XX	2-char state code
NOPAYIN-ZIP-FIRST-FIVE	PIC 9(5)	First 5 digits of ZIP; part of NOPAYIN-ZIP-PLUS-FOUR
NOPAYIN-ZIP-LAST-FOUR	PIC 9(4)	ZIP+4 portion — excluded from output
RECS-WRITTEN	PIC 9(7) VALUE ZERO	Records-written counter; max 9,999,999
END-FLAG / END-OF-FILE	PIC X / 88-level VALUE 'Y'	EOF sentinel
NOPAYIN-RECORD-TYPE 88-levels	'1'=100% offset; '2'=pended week; '3'=other payment; '4'=current CWE change; '5'=UI claim is BYE; '6'=WW credit	Not used by NOPAYADD logic, but present in the record
RECORDING MODE	F (fixed-length) on both FDs	Record length: 281 bytes (post-Y2K)
Low-value cleansing	INSPECT ADDR-LINE1 REPLACING ALL LOW-VALUES BY SPACES (same for LINE2)	Added by R. Blumenfeld, July 2009
Summary messages	'RESULTS OF NOPAYADD EXECUTION FOLLOWS;', 'THE # OF RECORDS PROCESSED WAS ', 'END OF REPORT////////////////////////'	Exact strings from 300-WRAP-UP
TC-01: Happy Path — Standard Address with / Delimiter

Objective: Verify normal address splitting, city/state/ZIP formatting, and record count.

Input (NOPAYIN-FILE — 1 record):

Field

	

Value


NOPAYIN-ADDRESS-SEG01-FORMAT	'123 MAIN ST/NEWARK ' (44 chars, padded)
NOPAYIN-STATE	'NJ'
NOPAYIN-ZIP-FIRST-FIVE	07102
NOPAYIN-ZIP-LAST-FOUR	1234
NOPAYIN-RECORD-TYPE	'1' (ONE-HUNDRED-PERCENT-OFFSET)
All other fields	Valid synthetic values

Expected Output (NOPAYOUT-FILE — 1 record):

Field

	

Expected Value

	

Derivation


ADDR-LINE1	'123 MAIN ST ' (30 chars)	UNSTRING extracts left of / → HOLD-STREET → ADDR-LINE1
ADDR-LINE2	'NEWARK NJ 07102 ' (30 chars)	STRING: HOLD-CITY delimited by TWO-SPACES + ONE-SPACE by SIZE + NOPAYIN-STATE delimited by ONE-SPACE + ONE-SPACE by SIZE + NOPAYIN-ZIP-FIRST-FIVE + ONE-SPACE by SIZE
All non-address fields	Identical to input	MOVE NOPAYIN-RECORD TO NOPAYOUT-RECORD preserves all before reformatting

Expected SYSOUT (from 300-WRAP-UP):

*************************************
RESULTS OF NOPAYADD EXECUTION FOLLOWS;
*************************************
THE # OF RECORDS PROCESSED WAS 0000001
*************************************
END OF REPORT////////////////////////

TC-02: Empty Input File

Objective: Verify the program handles an empty NOPAYIN-FILE — no records written, counter stays at zero, summary still displays.

Input: 0 records in NOPAYIN-FILE.

Expected:

NOPAYOUT-FILE contains 0 records
END-FLAG set to 'Y' on the priming read in 200-HSKG; 1000-MAIN-PROCESSING loop is never entered
SYSOUT shows RECS-WRITTEN = 0000000
THE # OF RECORDS PROCESSED WAS 0000000

TC-03: No / Delimiter in Address Field

Objective: Exercise the UNSTRING fallback — when NOPAYIN-ADDRESS-SEG01-FORMAT has no /, the entire 44-char field goes into HOLD-STREET (truncated to 30 chars) and HOLD-CITY stays at its initialized value (spaces, from INITIALIZE AREA1).

Input:

Field

	

Value


NOPAYIN-ADDRESS-SEG01-FORMAT	'456 ELM AVENUE APT 2B SUITE 100XTRA' (44 chars, no /)
NOPAYIN-STATE	'NY'
NOPAYIN-ZIP-FIRST-FIVE	10001

Expected:

Field

	

Expected Value

	

Rationale


ADDR-LINE1	'456 ELM AVENUE APT 2B SUITE 10' (30 chars — truncated)	UNSTRING puts first 30 chars into HOLD-STREET (PIC X(30)); chars 31–44 are lost
ADDR-LINE2	'NY 10001 ' (30 chars)	HOLD-CITY is all spaces after INITIALIZE AREA1; STRING starts with city delimited by TWO-SPACES (immediate hit — produces nothing), then ONE-SPACE, then state, ONE-SPACE, ZIP, ONE-SPACE. Note: Because HOLD-CITY is all spaces, the first double-space hit is at position 1 — zero city bytes are emitted. Result starts with the first ONE-SPACE, then NY, then space, then 10001, then space

⚠ Edge-case alert: The exact behavior of STRING … HOLD-CITY DELIMITED BY TWO-SPACES when HOLD-CITY is all spaces depends on whether the COBOL runtime finds the delimiter at position 1 (emitting zero bytes) or at position 2 (emitting one space). Verify against actual execution.

TC-04: Address Field Contains Embedded LOW-VALUES (Null Characters)

Objective: Verify the INSPECT … REPLACING ALL LOW-VALUES BY SPACES cleansing step (added July 2009 per source comment).

Input:

Field

	

Value


NOPAYIN-ADDRESS-SEG01-FORMAT	'789 OAK' + X'00' + 'DR/TRENTON' + padding (44 chars total)
NOPAYIN-STATE	'NJ'
NOPAYIN-ZIP-FIRST-FIVE	08608

Expected:

Field

	

Expected Value


ADDR-LINE1	'789 OAK DR ' — null between OAK and DR replaced with space
ADDR-LINE2	'TRENTON NJ 08608 ' — clean (no nulls expected in city/state/ZIP path, but INSPECT covers it if present)
TC-05: Multiple Records — Counter Increment

Objective: Verify RECS-WRITTEN increments by 1 per record (ADD 1 TO RECS-WRITTEN in 1000-MAIN-PROCESSING) and the summary reflects the total.

Input: 3 records in NOPAYIN-FILE, each with a valid STREET/CITY address.

Expected:

NOPAYOUT-FILE contains exactly 3 records
Each record independently formatted (AREA1 and NOPAYOUT-RECORD re-initialized per record via INITIALIZE AREA1, NOPAYOUT-RECORD)
SYSOUT: THE # OF RECORDS PROCESSED WAS 0000003
TC-06: Long Street Fills Entire HOLD-STREET (30 chars) Before /

Objective: Test the boundary where the street portion of the address is exactly 30 characters — the full capacity of HOLD-STREET PIC X(30).

Input:

Field

	

Value


NOPAYIN-ADDRESS-SEG01-FORMAT	'123456789012345678901234567890/CITY' + padding to 44
NOPAYIN-STATE	'PA'
NOPAYIN-ZIP-FIRST-FIVE	19101

Expected:

Field

	

Expected Value


ADDR-LINE1	'123456789012345678901234567890' (exactly 30 chars)
ADDR-LINE2	'CITY PA 19101 '
TC-07: City Name Exactly 15 Characters (Full HOLD-CITY Capacity)

Objective: Test the boundary where HOLD-CITY PIC X(15) is fully used — the double-space trimming delimiter should not be found within the city name if all 15 positions are non-space.

Input:

Field

	

Value


NOPAYIN-ADDRESS-SEG01-FORMAT	'100 BROAD ST/POINT PLEASANT B' + padding (city portion = 'POINT PLEASANT ' → 15 chars exactly)
NOPAYIN-STATE	'NJ'
NOPAYIN-ZIP-FIRST-FIVE	08742

Expected:

Field

	

Expected Value


ADDR-LINE2	'POINT PLEASANT NJ 08742 '
TC-08: All Six RECORD-TYPE Values Pass Through

Objective: NOPAYADD does not filter or branch on NOPAYIN-RECORD-TYPE — all six 88-level values should produce output records identically.

Input: 6 records, one for each NOPAYIN-RECORD-TYPE value:

Record

	

RECORD-TYPE

	

88-level Name


1	'1'	ONE-HUNDRED-PERCENT-OFFSET
2	'2'	PENDED-WEEK
3	'3'	OTHER-PAYMENT
4	'4'	CURRENT-CWE-CHANGE
5	'5'	UI-CLAIM-IS-BYE
6	'6'	WW-CREDIT

Expected:

All 6 produce output records with correctly reformatted addresses
NOPAYOUT-RECORD-TYPE in each output record matches its input value
RECS-WRITTEN = 0000006
TC-09: Street Address with Multiple / Characters

Objective: UNSTRING with a single DELIMITED BY '/' splits at the first / occurrence. The second receiving field (HOLD-CITY) gets everything between the first and second / — characters after the second / are discarded (COBOL UNSTRING behavior with exactly two INTO targets and no POINTER/TALLYING).

Input:

Field

	

Value


NOPAYIN-ADDRESS-SEG01-FORMAT	'100 N/S HIGHWAY/EDISON ' (44 chars)
NOPAYIN-STATE	'NJ'
NOPAYIN-ZIP-FIRST-FIVE	08817

Expected:

Field

	

Expected Value

	

Rationale


ADDR-LINE1	'100 N '	First UNSTRING target gets text before the first /
ADDR-LINE2	'S HIGHWAY NJ 08817 '	Second target gets text between first and second / → 'S HIGHWAY'; city portion trimmed at double-space

⚠ Note: The street name is split incorrectly because the address itself contains /. This is a known data-quality concern, not a program bug — NOPAYADD has no special handling for addresses containing the delimiter character. Flag for upstream data validation.

TC-10: Address Field is All Spaces (No Street or City Data)

Objective: Test behavior when NOPAYIN-ADDRESS-SEG01-FORMAT is entirely spaces (44 spaces, no /).

Input:

Field

	

Value


NOPAYIN-ADDRESS-SEG01-FORMAT	44 spaces
NOPAYIN-STATE	'NJ'
NOPAYIN-ZIP-FIRST-FIVE	07001

Expected:

Field

	

Expected Value

	

Rationale


ADDR-LINE1	30 spaces	UNSTRING puts all spaces into HOLD-STREET (no / found) → ADDR-LINE1 = spaces
ADDR-LINE2	'NJ 07001 ' (or ' NJ 07001...')	HOLD-CITY = spaces from INITIALIZE; STRING emits city trimmed at double-space (zero or one byte), then space, state, space, ZIP, space

⚠ Verify actual byte-level output — the leading content of ADDR-LINE2 depends on how many space-bytes the COBOL STRING emits before the delimiter fires on HOLD-CITY.

TC-11: Non-Address Fields Preservation (Full Record Fidelity)

Objective: Verify that the MOVE NOPAYIN-RECORD TO NOPAYOUT-RECORD in 1100-PROCESS-ADDRESS preserves all non-address fields byte-for-byte.

Input: A single record with distinctive values in every field:

Field

	

Test Value


NOPAYIN-SSN	+123456789 (COMP-3)
NOPAYIN-PC	+001 (COMP-3)
NOPAYIN-WBR	0500.00
NOPAYIN-WBA	0400.00
NOPAYIN-CLAIM-BALANCE	+000012345.67 (COMP-3)
NOPAYIN-EARNINGS-AMOUNT1	0100.50
NOPAYIN-SEX	'M'
NOPAYIN-NAME-SEG01-FORMAT	'DOE JOHN ' (30 chars)
NOPAYIN-SUPPRESSION	'NO'
NOPAYIN-HEALTH	0075.00

Expected: Every output field except ADDR-LINE1 and ADDR-LINE2 must exactly match the corresponding input field values above.

TC-12: AREA1 Re-Initialization Between Records

Objective: Confirm that residual data from Record N's HOLD-STREET / HOLD-CITY does not bleed into Record N+1's output, because INITIALIZE AREA1, NOPAYOUT-RECORD is called at the top of 1100-PROCESS-ADDRESS for every record.

Input (2 records):

Record

	

ADDRESS-SEG01-FORMAT

	

STATE

	

ZIP-FIRST-FIVE


1	'999 VERY LONG STREET NAME HERE/LONGBEACHCITY '	'CA'	90802
2	'1 A ST/NY ' (short)	'NY'	10001

Expected for Record 2:

Field

	

Expected Value


ADDR-LINE1	'1 A ST ' — no remnants of '999 VERY LONG…'
ADDR-LINE2	'NY NY 10001 ' — no remnants of 'LONGBEACHCITY' or 'CA' or 90802
Summary: Test Matrix

TC

	

Scenario

	

Key Verification


01	Happy path / split	Standard address formatting
02	Empty input file	0 records, loop skipped, summary shows 0
03	No / in address	Entire field → street; city empty
04	Embedded LOW-VALUES	INSPECT replaces nulls with spaces
05	Multiple records	Counter increments correctly
06	30-char street before /	HOLD-STREET boundary
07	15-char city	HOLD-CITY boundary
08	All 6 RECORD-TYPE values	No filtering; all pass through
09	Multiple / in address	UNSTRING splits at first / only
10	All-spaces address	Degenerate input handling
11	Non-address field fidelity	Full record preservation
12	AREA1 re-init between records	No cross-record data bleed

This test suite is synthesized from the retrieved NOPAYADD.txt source code and NOPAYADD.md business rules in the Daily CA-7 space.
NOPAYADD.md
NOPAYADD.txt
 Every constant, field size, 88-level value, paragraph name, and DISPLAY string is copied directly from the source. The expected outputs are derived from the 1100-PROCESS-ADDRESS, 1000-MAIN-PROCESSING, and 300-WRAP-UP paragraphs — they should be validated against actual program execution before being used as acceptance criteria.

A few callouts on tricky edge cases:

TC-03 and TC-10 (no delimiter / all-spaces address): The exact byte-level behavior of STRING … HOLD-CITY DELIMITED BY TWO-SPACES when HOLD-CITY is all spaces depends on where the COBOL runtime locates the first double-space. Recommend verifying these against the actual IBM COBOL II runtime.
TC-09 (multiple / characters): This exposes a data-quality vulnerability — the program has no way to distinguish an address containing / from the delimiter. Worth flagging for upstream validation.
TC-04: The INSPECT … REPLACING ALL LOW-VALUES BY SPACES was a 2009 patch (per source comment). This test confirms that fix is operational.
What would you like to do next?

Generate as DOCX

Expand the test suite

Generate sample test data file

_Citations:_
- Citation 1
- Citation 2

## v5-Q7

**Q:** I'm rotating off. Put together a handoff summary of the daily check reprint flow — ZUMDA1R1 and DXCB103U and anything downstream — for the engineer replacing me. They won't have this chat history.

**A** (13:30):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

Here's a standalone handoff summary for the incoming engineer, synthesized from the ZUMDA1R1.md, ZUMDA1R1-jcl.json, DXCB103U-cbl.json, and UIMI0440-cbl.html documents across the Daily CA-7 and DailyUI knowledge spaces.

Handoff Summary — Daily UI Check Reprint Flow (ZUMDA1R1 / DXCB103U)

Handoff Summary — Daily UI Check Reprint Flow

Provenance: This document is synthesized from multiple knowledge-base sources: ZUMDA1R1.md, ZUMDA1R1-jcl.json (Daily CA-7 space), DXCB103U-cbl.json, DXCB103U-cbl.html, UIMI0440-cbl.html (DailyUI space). All program names, dataset names, step names, record sizes, and business rules are cited from those documents. Items marked ⚠ are gaps or areas needing SME verification.

1. What This Flow Does (Business Context)

Job ZUMDA1R1 is a CA-7 daily-scheduled batch job that processes UI (Unemployment Insurance) Non-Direct Deposit check payments. "Non-Direct" means paper checks — not direct deposit / electronic banking. The job:

Validates the input payment file.
Generates formatted 806-byte laser-check print records.
Backs up the output to tape (permanent) and disk (weekly rolling).
Copies today's reprint-eligible records into a 5-day reprint VSAM cluster.

The final output feeds the FINALIST check-printing process (physical laser checks mailed to claimants). The reprint cluster enables reprinting checks for up to 5 days after issuance.

2. Job: ZUMDA1R1 — Step-by-Step

JCL location: JCLIBALL library, CA-7 daily schedule
Job class: 7 | MSGCLASS: J | Account: (Y2K20,P) | LOGONID: PLA2LDX

Step

	

Stepname

	

Program / Utility

	

Purpose

	

Conditional?


1	IEFBR14	IEFBR14	Pre-processing cleanup — deletes stale LAK2LDXP.ZUMDA1R1.UI.CHKS.DTL from any prior run. No error if file doesn't exist.	Unconditional
2	TEST1	IDCAMS REPRO	Data-presence check — extracts exactly 1 record from LAK2LDXP.ZUMDA1R1.NONDD.DTL to a temp file (FB, LRECL=323). Confirms input file is accessible and non-empty.	Skipped if Step 1 RC ≠ 0
3	VERIFYUI	VERFYUI2	Validation — validates all Non-Direct payment records against the DATECARD processing date. Produces a printed verification report.	Skipped if any prior RC ≠ 0
4	UIMI0063	UIMI0440 (via DB2 plan UIMI0440)	Check generation — the main workhorse. Reads Non-Direct payment records, cross-references VSAM code tables and reprint data, and writes formatted 806-byte check records to UI.CHKS.DTL. Also writes reprint records to the UIVSAM VSAM cluster.	Skipped if any prior RC ≠ 0
5	EMPTYIT	IDCAMS REPRO	Fallback — if Step 4 returned RC ≠ 0, creates an empty UI.CHKS.DTL placeholder (FB, LRECL=806, 250 cyl primary) so backup steps don't fail on a missing file.	Runs only if Step 4 RC ≠ 0
6	BACKUP1	SORT (copy)	Permanent tape backup — copies UI.CHKS.DTL as-is (no sort/filter) to GDG LAK2LDXP.ZUMDA1R1.UI.CHKS.BCKUP(+1) on SILO tape. EXPDT=99000 (never expires).	Always runs — unconditional
7	BACKUP2	SORT (copy)	Weekly disk backup — copies UI.CHKS.DTL as-is to GDG LAK2LDXP.ZUMDA1R1.UI.WKLY.BCKUP(+1) on SYSALLDA disk. Rolling GDG retention.	Always runs — unconditional
8	DXCB103U	DXCB103U	Reprint cluster update — reads primary UIVSAM and copies records into the 5-day UIVSAM5 cluster, date-stamping each with today's run date.	Skipped if any prior RC ≠ 0
Key Conditional Logic
Steps 2–4 form a gated pipeline: any failure short-circuits to the backup steps.
Backups (Steps 6–7) always run — even if upstream steps failed — so there's always something on tape/disk (even if it's an empty placeholder).
Step 8 (DXCB103U) only runs if the entire pipeline succeeded (all prior RC = 0). This is a safety mechanism — if checks weren't generated, you don't want to mark records as reprinted.
3. Key Datasets

Dataset Name (HLQ:

	

LAK2LDXP

	

)

	

Type

	

LRECL

	

Purpose


ZUMDA1R1.NONDD.DTL	Sequential (FB)	323	Input — Non-Direct Deposit payment records from upstream		
PROD.CNTLLIB(DATECARD)	PDS member	—	Date control card (processing date in MMDDYYYY + week-ending, month, quarter, annual dates)		
VSAM.CODES.CLUSTER	VSAM (KSDS)	—	Code reference table — payment type codes, benefit program codes, status codes		
VSAM.UIVSAM.CLUSTER	VSAM (KSDS)	—	Primary UI Reprint cluster — keyed by SSN + Sequence		
VSAM.UIVSAM5.CLUSTER	VSAM (KSDS)	—	Secondary 5-day UI Reprint cluster — accumulates 5 days of reprint records		
ZUMDA1R1.UI.CHKS.DTL	Sequential (FB)	806	Output — formatted check print records (deleted/recreated each run)		
ZUMDA1R1.UI.CHKS.BCKUP	GDG (tape)	806	Permanent tape archive — never expires		
ZUMDA1R1.UI.WKLY.BCKUP	GDG (disk)	806	Weekly disk backup — rolling retention		
4. Program: UIMI0440 — Check Generation (Step 4)

This is the heaviest program in the flow.

Type: Batch COBOL, DB2 + VSAM + FILE access, no MQ
DB2 Plan: UIMI0440
Execution: Via TSO batch (IKJEFT01) under step UIMI0063
What it does (60 documented functionalities):
Opens the Non-Direct payment file (CHECKREC DD), date control card (DATEIN), VSAM code table (CODELOOP), and reprint VSAM (REPRINT).
For each eligible payment record (Print Indicator = 1, 0, or blank AND Void Indicator = 0):
Formats claimant name, address, benefit amounts, deductions, tax withholding.
Looks up local office return address from Table 112 (via Table 175 for Regional offices).
Determines office heading: REGIONAL AUTHORIZATION CENTER, INTERSTATE CLAIMS OFFICE (offices 997/999), or default UNEMPLOYMENT CLAIMS OFFICE.
Assigns benefit type codes: EB, EC, TX, TY, TZ, EU, WF, SE — with a priority cascade (SEA overrides WFD overrides primary type).
Handles certification code messaging (Benefits Exhausted for code '1', Benefit Year Ended for code '2', TUC final payment messages).
Assigns check numbers, bank account numbers, ZIP+4 barcodes.
Writes 806-byte records to the primary output (PRNTDATA = UI.CHKS.DTL), a clone output, and a reprint output.
Suppresses secondary output (PRNTDAT2).
On failure:

The UI.CHKS.DTL file is automatically deleted (JCL DISP=DELETE on abnormal) — no partial check data is ever retained.

5. Program: DXCB103U — Reprint Cluster Update (Step 8)
Type: Batch COBOL, VSAM only, no DB2, no MQ
Source member: DXCB103U.cbl (displays as DXCB103R in its own banners — this is the PROGRAM-ID vs. the member name)
Processing Logic:
Housekeeping: Reads the DATECARD from SYSIN. Extracts daily date (B040-DAILY-DATE) in MMDDYYYY format, then reformats it to YYYYMMDD as DATE-RUN.
Open files:
REPRINT-FILE (primary UIVSAM cluster) — opened INPUT mode for sequential read.
REPRINT5-FILE (5-day UIVSAM5 cluster) — opened EXTEND mode (appends after existing records).
Positioning: Sets REPRINT-SSN and REPRINT-SEQUENCE to zero, issues START to position at the first record with a key > 0 (i.e., beginning of file).
If START fails: displays 'INVALID RETURN CODE ON START FOR FILE REPRINT' + status code, closes both files, and terminates immediately.
Record loop: For each record read from REPRINT:
Copies SSN → REPRINT5-SSN (exact)
Copies Sequence → REPRINT5-SEQUENCE (exact)
Stamps DATE-RUN → REPRINT5-DATE (replaces any original date)
Copies 806-char data payload (REPRINT-REST → REPRINT5-REST, exact)
Writes to REPRINT5 (append)
Increments records-read and records-written counters
On write failure: Displays severe error banner: 'PROBLEM EXISTS WITH REPRINT5 FILE', 'WRITE FAILED', 'CORRECT AND RESTART'. Closes both files, terminates immediately.
Wrap-up: Displays completion banner (DXCB103R COMPLETED NORMALLY), total records read, total records written. Closes REPRINT-FILE first, then REPRINT5-FILE (strict order enforced).
The key business rule:

Every record in UIVSAM5 is tagged with today's DATE-RUN. This is how the system knows which records are reprintable for the current 5-day window — older records beyond the window are excluded by date.

6. Failure Scenarios & Recovery

Failure Point

	

What Happens

	

Recovery


Step 1 (cleanup) fails	Steps 2–4 skipped; backups run (will back up stale file if it exists)	Investigate allocation/catalog issue; rerun
Step 2 (TEST1) fails	Means NONDD.DTL is empty or inaccessible; Steps 3–4 skipped	Check upstream job that produces NONDD.DTL
Step 3 (VERFYUI2) fails	Validation failure; Step 4 skipped	Review verification report in SYSOUT
Step 4 (UIMI0440) fails	UI.CHKS.DTL is auto-deleted; EMPTYIT creates empty placeholder; backups run (empty file); Step 8 skipped	Check DB2 availability, VSAM status, SYSOUT messages
Step 4 returns RC=0 but no records	EMPTYIT runs (creates empty file); backups run; Step 8 still executes	Normal — just means no checks this cycle
Step 8 (DXCB103U) — START fails	Immediate termination with status code displayed	Check UIVSAM cluster integrity (VERIFY/REPRO)
Step 8 (DXCB103U) — WRITE fails	Immediate termination, both files closed	Check UIVSAM5 cluster space/integrity; rerun Step 8 only
7. Upstream / Downstream Dependencies
Upstream (what feeds this job):
LAK2LDXP.ZUMDA1R1.NONDD.DTL — produced by the upstream payment processing pipeline (⚠ the specific upstream job is not documented in the held knowledge base; check CA-7 predecessors for ZUMDA1R1)
LAK2LDXP.PROD.CNTLLIB(DATECARD) — shared date control card used across many daily jobs
VSAM.CODES.CLUSTER and VSAM.UIVSAM.CLUSTER — shared VSAM resources
Downstream (what consumes this job's output):
UI.CHKS.DTL → feeds the FINALIST laser check printing process (⚠ the FINALIST job name and details are outside the held knowledge base — it's in the check-print/money-movement domain)
VSAM.UIVSAM5.CLUSTER → consumed by CICS online reprint screens and/or subsequent batch reprint jobs (⚠ specific consumers not documented in the held slice)
ZUMDA1R2 — a related job visible in the DailyUI space that handles Direct Deposit payment processing (separate from this Non-Direct flow), also using LAK2LDXP.ZUMDA1R1.* files
⚠ Coverage Caveat:

The dependency picture above is bounded by the held knowledge base. Dynamically called programs, operator-DEMANDed jobs, and manually triggered streams may not appear. Check CA-7 demand/trigger relationships and the operations runbook for the full picture.

8. Key Things to Watch

The EMPTYIT safety net: If UIMI0440 fails, the job creates an empty placeholder so backups succeed. This means your tape/disk backups for that day contain zero records. If you see a zero-byte backup generation, check whether UIMI0063 actually ran successfully.

Date-stamping in DXCB103U: Every record written to UIVSAM5 gets today's DATE-RUN in YYYYMMDD format. If the DATECARD is wrong (e.g., ops loaded yesterday's card), reprints will have the wrong date window. Always verify the DATECARD matches the processing date.

UIVSAM5 is EXTEND mode: DXCB103U appends to UIVSAM5 — it does not clear it. Older records accumulate over 5 days. ⚠ The purge/cleanup mechanism for records older than 5 days is not documented in the held knowledge base. Ask the operations team or SME about the UIVSAM5 maintenance job.

Program ID mismatch: The source member is DXCB103U but the program's internal PROGRAM-ID (as shown in its completion banner) is DXCB103R. This is normal — they're the same program. Don't be confused by SYSOUT saying DXCB103R COMPLETED NORMALLY.

Record size: NONDD.DTL = 323-byte FB records. UI.CHKS.DTL = 806-byte FB records. If you see IEC messages about record length mismatches, check which file was accidentally wired to the wrong DD.

UIMI0440 is complex: It has 60+ documented functionalities and 300+ business rules (benefit type cascades, certification code messaging, regional/interstate office heading logic). Changes to this program should be treated as high-risk. The arithmetic for earnings/pension offset calculations in UIMI0440 is inferred from source and should be confirmed with an SME before relying on it for test cases.

9. Source Documents for Further Reading

Document

	

Space

	

What It Covers


ZUMDA1R1.md	Daily CA-7	Job-level flow, step rules, mermaid diagrams
ZUMDA1R1-jcl.json	Daily CA-7 / DailyUI	Full 11-rule business rules with Given/When/Then
ZUMDA1R1.txt	Daily CA-7	Raw JCL source
DXCB103U-cbl.json	DailyUI	Full program documentation with 61 business rules
DXCB103U-cbl.html	DailyUI	Flow diagram + summary
UIMI0440-cbl.html	DailyUI	60-functionality summary of check generation program
UIMI0440-cbl.json	DailyUI	300+ business rules for check formatting
VERFYUI2-cbl.json	DailyUI	Verification program documentation

Prepared: September 1, 2026. Contact the LOOPS Engineering Onboarding Specialist for follow-up questions.

This is a self-contained document — your replacement won't need any prior chat context. A few notes on what it covers and what it doesn't:

What's in scope:

The complete 8-step ZUMDA1R1 job flow with all conditional logic and fallback mechanisms
UIMI0440 (check generation) — role, inputs/outputs, benefit type cascade, office heading logic
DXCB103U (reprint cluster update) — full processing logic including date reformatting, VSAM positioning, record mapping, and error handling
All key datasets with their types, record lengths, and purposes
Failure/recovery scenarios and operational watch items

What's explicitly flagged as out-of-scope (knowledge base doesn't cover these):

The specific upstream job that produces NONDD.DTL
The downstream FINALIST check-print job
The UIVSAM5 purge/maintenance mechanism
The UIMI0440 earnings/pension offset arithmetic (inferred, not verified)
What would you like to do next?

Generate a downloadable DOCX

Deep-dive on UIMI0440 check formatting logic

Explore upstream/downstream job dependencies

## v5-Q8

**Q:** What do the ZLPDYOR1 through ZLPDYOR9 jobs do in the daily stream?

**A** (13:31):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

The knowledge base does not have jobs named ZLPDYOR1 through ZLPDYOR9 in either the CA-7 daily schedule table or the job purpose index.
01_schedule_job_t...
05_job_purpose_in...

What Is Documented

The closest match is a single job:

ZLPDYO99 — listed in the CA-7 daily schedule under the LOP subsystem.
01_schedule_job_t...
 However, its JCL header purpose text is not captured in the job purpose index, and no detailed JCL source or program documentation for it appears in the held knowledge base.
Possible Explanations

A few things to check before going further:

Naming typo or convention mismatch: The ZLPD* family in the daily schedule uses a 4-letter function code after ZLPD (e.g., ZLPDWPR*, ZLPDVRU*, ZLPDEUR*). The pattern ZLPDYOR* would imply function code YOR, which doesn't appear. Could the jobs be named something similar? For example:

ZLPDYO99 (the documented one — possibly the "99" consolidation/cleanup job for a ZLPDYO* series?)
Or perhaps they exist under a different prefix entirely?

Multi-database fan-out convention: Many LOOPS daily jobs use a 0–9 suffix to split processing across the 10 IMS databases (DB00–DB09). If ZLPDYO* jobs exist, they would follow this pattern. But without JCL source or purpose text in the knowledge base, I can't describe what they do.

On-demand or recently added: If these jobs were added after the CA-7 schedule snapshot (FSTRUC DOLDAILYD061526, parsed 2026-08-14), they won't appear in the held data.
01_schedule_job_t...

Recommendation

I'd suggest:

Check the CA-7 FSTRUC directly on the mainframe for jobs matching ZLPDYOR* — the schedule listing would show their subsystem, predecessors/successors, and trigger conditions.
Check the JCL library (JCLIBALL) for members named ZLPDYOR1 through ZLPDYOR9 — the JCL header comments will have the purpose line and the programs invoked.
If you can share the JCL or a job name correction, I can search for the programs those steps execute and give you the full breakdown.
How would you like to proceed?

I'll look up the JCL and come back

Tell me more about ZLPDYO99

Let me verify the job names

_Citations:_
- Citation 1
- Citation 2
- Citation 1
- Citation 1
