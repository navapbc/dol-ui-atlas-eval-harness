# 2026-09-01_1310_quick_playwright_v3

- **Backend:** quick (transport: playwright)
- **Bank:** v3 (`question_sha256` 414d3168fc4e…)
- **Agent:** engineering_onboarding_specialist (`093ac4e3-0712-481e-af95-9ddc5e4fc734`)
- **Conversation:** `68696dd1-f720-474e-870e-a7301153f306`
- **Model:** Advanced
- **Started:** 2026-09-01 13:03
- **Finished:** 2026-09-01 13:10
- **Status:** complete
- **Questions asked:** 8, answered: 8

## v3-Q1

**Q:** Describe the Automated Collection Process.

**A** (13:04):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

The knowledge base has no process by the exact name "Automated Collection Process." However, there are several closely related documented collection processes that may be what you're looking for. Here are the closest matches:

1. Accelerated Collection Process (ACP)

This is the closest documented match. It is implemented by program UIMI0730, titled "ACCELERATED COLLECTION PROCESS" in its source header (authored by P. Haughton, August 2010). It is part of the CA-7 daily LOP batch schedule.
UIMI0730.txt

The ACP's population-selection logic is documented in the companion subprogram UIMI0725 (UIMI0725.md). A base claim record is selected for ACP population processing when it has at least one active outstanding balance across any of these debt types :
UIMI0725.md

Federal 100% or 50% Refund Offset
Non-Federal 100% or 50% Refund Offset
Extended Benefits 100% or 50% Refund Offset
FSC, DI, EUB, or WFD 100% or 50% Refund Offset
Fines Amount Balance
Interest Amount Balance

The selection criteria require that the record be a base claim (Program Code = 0 and Claim Date = 0) and that at least one of those balances is greater than zero. Once selected, the full claim validation and output record creation process is initiated.
UIMI0725.md

Note: The retrieved source covers the selection/population step (UIMI0725) and identifies UIMI0730 as the main ACP program. The full end-to-end ACP flow (upstream extraction, downstream actions) may involve additional programs not fully documented in these passages.

2. DABS — Debt Collection Document Generation

Job D2FND222 invokes the DABS (Debt Automated Build System) Document Builder program JECBD53P. This step processes a Driver File (DRIV1F1.DTL) and generates debt collection correspondence and forms across 10 distinct output streams, applying date-sensitive business rules and code lookups from the VSAM.CODEDABS.CLUSTER table.
D2FND222.md

The job also includes a Driver File backup step with automatic discard of incomplete backup generations on failure.
D2FND222.md

3. Auto Garnishment Batch Processing

Job L2AGW2 handles Auto Garnishment batch processing. It distributes garnishment records across 10 parallel processing units using program DXCBW18S, reading from a consolidated input file (AUTOGARN) and a merged detail file, then partitioning them into FILE01 through FILE10.
L2AGW2.md

4. Collection of Debt (COD) Continuity

Program UIMB0025 documents how Collection of Debt (COD) fields are carried forward when a claim is transferred. The transferred fields include COD Amount, COD Potential Amount, COD Minimum Exceeded Date, and the Dunning Letter Level (current level of collection correspondence sent to the claimant).
UIMB0025.md

Could you clarify which of these you're interested in? If you meant the Accelerated Collection Process (ACP), I can dig deeper into UIMI0730 and its full batch context.

Which collection process would you like to explore further?

Accelerated Collection Process (ACP)

DABS Debt Collection Document Generation

Auto Garnishment Batch Processing

Collection of Debt (COD) Continuity

_Citations:_
- Citation 1
- Citation 2
- Citation 2
- Citation 3
- Citation 3
- Citation 4
- Citation 5

## v3-Q2 (asked immediately after v3-Q1)

**Q:** What does the acronym ACP stand for?

**A** (13:04):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

In the LOOPS knowledge base, ACP stands for Accelerated Collection Process, as documented in the LOOPS terminology glossary (06_terminology_glossary.md), sourced from the LOOPS Daily Flowchart.
06_terminology_gl...

This is further corroborated by the copybook ACPVALID.txt, which defines the record layout for ACP-DOR-VALID-PAYMENT — the layout for valid payments from the Department of Revenue — and by programs like UIMI0732 (ACP Population table management) and DXCBACP4 (ACP payment detail reporting).
ACPVALID.txt
UIMI0732.md
DXCBACP4.md

Would you like me to go deeper into how the Accelerated Collection Process works end-to-end?

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4

## v3-Q3

**Q:** When LOOPS issues a weekly benefit payment, how is the charge allocated across the claimant's base-period employers?

**A** (13:05):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

This is a rich topic that spans multiple programs in the LOOPS system. Here's a synthesized answer drawn from the documented source code — the explanation covers both how the charge percentage is established and how each weekly payment is distributed.

Step 1: Establishing the Charge Percentage (at Claim Setup Time)

When a claim is monetarily determined, the system calculates each base-period employer's charge percentage — the fraction of every future weekly payment that employer will bear. The programs involved are DXCD037S (CICS monetary determination) and UIMI0004 / UIMB0004 (IMS subprograms).

The standard formula is :
UIMB0004.md
DXCD037S-cbl.json

Employer Charge % = Employer's Total Wages ÷ Total Claim Base Wages

Special cases:

Overlap wages — If an employer's wages overlap with a prior claim's base period, the overlapping wages are subtracted from the numerator before dividing (different quarters are excluded depending on whether the base year is Normal, Lag, or Current).
UIMB0004.md
UCX (Military) claims — Under Period 1 or Period 3, the military employer (Form 214) gets 0% and only NJ-state employers share liability. Under Period 2, all employer types (NJ, military, UCFE) share proportionally.
DXCD037S-cbl.json
Held / invalid employers — Employers with hold indicators G, H, or D (or on an invalid claim) are assigned 0%.
DXCD037S-cbl.json
General Fund — Any remaining unallocated MBA after all employers are charged goes to a General Fund employer entry.
DXCD037S-cbl.json

Each employer's Maximum UI Charge Amount is then: Charge % × Maximum Benefit Amount (MBA), and the employer's Balance Remaining starts at that maximum minus any prior charges. A rounding-remainder process ensures all employer percentages sum to exactly 100% and all max charges sum to exactly the MBA.
UIMB0004.md
UIMI0004.md

Step 2: Weekly Payment Charge Distribution (Each Payment Cycle)

When a weekly benefit payment is issued, the charge is distributed by batch program DXCBP500 (and online counterpart UIMR0030). The process works as follows :
DXCBP500.md
UIMR0030-cbl.json

2a. Initialization
The WBA (Weekly Benefit Amount) is read from the payment record.
A Remaining WBA tracker (WS-REMAIN-AWBA) is set to the full WBA.
The employer table is loaded with all base-period employers and positioned at the first entry.
2b. Payment Type Routing
If the payment transaction code is < 100 → Regular UI payment (full-rate charging).
If ≥ 100 → Extended Benefits (EB) payment (half-rate charging: each employer's charge = 0.5 × Charge % × WBA).
DXCBP500.md
DXCBP500.md
2c. Employer-by-Employer Loop (Positive Payments)

For each employer in the table (processed in order; UIMR0030 sorts them ascending by charge percentage first ):
UIMR0030-cbl.json

Calculate proportional charge: Charge = WBA × Employer Charge % (or 0.5 × Charge % × WBA for EB), rounded to the nearest cent.
UIMR0030-cbl.json
DXCBP500-cbl.json
Cap at remaining WBA: If the calculated charge exceeds the remaining unallocated WBA, it is reduced to equal the remaining WBA.
DXCBP500.md
Cap at employer's remaining balance: If the (possibly WBA-capped) charge exceeds the employer's remaining chargeable balance (TAB1-BAL-EMP-REM), it is further reduced to that balance, and the employer's balance goes to zero.
DXCBP500.md
DXCBP500.md
Deduct from trackers: The charge amount is subtracted from both the employer's remaining balance and the remaining WBA.
Rounding overage correction (UIMR0030 path): If deducting the charge drives the remaining WBA negative, the employer's charge is reduced by the overage and the remaining WBA is set to zero.
UIMR0030-cbl.json
Create charge record: A DB04 charge record is inserted for each employer with a non-zero charge.
DXCBP500.md
UIMB0030.md
2d. Residual Handling (Last Employer / Rounding Adjustment)
Table

Program

	

Residual Strategy


DXCBP500	Any remaining WBA left after all proportional charges is assigned entirely to the last employer in the table.
UIMR0030	After all employers are charged proportionally, if WBA remains, an overflow distribution process works backwards through the table, absorbing the remainder into employers that still have available balance.
View more

In both cases, the system guarantees that 100% of the WBA is distributed — the remaining WBA reaches zero before processing ends.
DXCBP500.md
UIMR0030-cbl.json

2e. Negative Payments (Credits/Reversals)

When a payment has a negative WBA (a reversal), the system iterates in reverse (from the last employer to the first), restoring employer balances rather than charging them. The same proportional and capping logic applies in mirror.
DXCBP500.md
DXCBP500.md

Key Programs Involved
Table

Program

	

Role

	

Space


DXCD037S	CICS monetary determination; calculates charge percentages and max charges	CWC
UIMI0004 / UIMB0004	IMS subprograms for charge percentage calculation and rounding	Daily CA-7
DXCBP500	Batch employer charge distribution for each weekly payment	Daily CA-7
UIMR0030	Online/CICS employer charge distribution (with sort and rounding adjustment)	Daily CA-7
UIMB0030	Populates the DB04 charge segment record	Daily CA-7
View more

Note: This summary is synthesized from the business rules extracted from the programs above. The charge percentage formula and weekly distribution algorithm are well-documented in source. The arithmetic for the weekly charging loop (particularly the rounding residual strategy difference between DXCBP500 and UIMR0030) is derived from source and should be confirmed with a subject-matter expert if precision matters for your use case.

Would you like to explore a specific aspect further?

Charge percentage calculation details

DXCBP500 batch charging walkthrough

UIMR0030 online charging differences

Negative payment / credit processing

_Citations:_
- Citation 1
- Citation 2
- Citation 1
- Citation 2
- Citation 2
- Citation 2
- Citation 1
- Citation 3
- Citation 4
- Citation 5
- Citation 4
- Citation 6
- Citation 5
- Citation 5
- Citation 7
- Citation 6
- Citation 4
- Citation 6
- Citation 5
- Citation 4
- Citation 8
- Citation 4
- Citation 5
- Citation 4
- Citation 6

## v3-Q4

**Q:** Which LOOPS batch processes validate SSNs and check whether a claimant is deceased, and how do they work?

**A** (13:06):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

The knowledge base documents several batch processes that handle SSN validation and deceased detection. This is a synthesized summary drawn from multiple program documents across the Daily CA-7 space.

SSN Verification via the VERIS Service

At the heart of SSN validation is a two-tier architecture: a reusable called module (VERISBN) and calling programs that invoke it and act on the results.

VERISBN — The SSN Verification Engine

VERISBN is a called batch COBOL module that interfaces with IBM MQSeries to verify an SSN against the Social Security Administration (SSA). It does not run standalone — it is called by other programs.
VERISBN.md
VERISBN.md

How it works:

Accepts input — The calling program passes a claimant's SSN and Date of Birth (in MMDDCCYY format) via a COBOL linkage area.
Reads configuration — Opens the VERSTIME control file for timestamp management and VERSQUEU for the MQ queue manager name (defaults to QRT1 if empty).
Connects to MQ — Establishes a connection to IBM MQSeries using the resolved queue manager name. If already connected (reason code 2002), it reuses the session.
Sends request — Puts a non-persistent message containing the SSN + DOB onto queue LAK2LDXP.VERIS.REQUEST with a 5-minute expiry.
Waits for response — Opens LAK2LDXP.VERIS.REPLY and waits up to 5 minutes (3000 tenths of a second) for a correlated response matched by message ID.
Standardizes response — Converts all text fields (name, state, SSN return code literal, DOB string) to uppercase.
Returns results — Returns the full verification response to the caller, including return codes, name, DOB details, age ranges, state, and ZIP codes.
VERISBN.md
Programs That Call VERISBN and Act on Results
1. UIMI0004 — SSN Verification at Monetary Determination

During claim monetary determination, UIMI0004 verifies the claimant's SSN with the SSA :
UIMI0004.md

Retrieves the basic claim record (SSN + Program Code 10 + Date of Claim).
Reformats the DOB from internal CCYYMMDD to MMDDCCYY for VERIS.
Calls VERISB (the VERIS interface) with the SSN and DOB.
Stores results in the UIMV_SSN_VALIDITY DB2 table (Table-22) — including all return codes, age range, state code, and DOB details. Even failed VERIS calls get recorded (with blanks/zeros for the verification fields).
UIMI0004.md

Deceased / Retired detection:

If the SSN return code is '00000110', the claimant is identified as deceased or retired. A record is inserted into the UIMV_SSN_RETIRED DB2 table (Table-23) with the claimant's name, DOB, date of death, and ZIP codes for benefit/lump-sum payments.
UIMI0004.md

SSN Problem flagging:

If the SSN return code is any non-zero value (not just '00000110'), the claim is flagged for manual review: the remarks counter is incremented, the potential-payment-pending indicator is set to 1, and a remarks segment (DB16) is inserted into IMS documenting the SSN issue.
UIMI0004.md
2. UIMI0072 / UIMB0072 — SSN Re-Verification Batch

These are batch re-verification programs that retry previously failed VERIS checks :
UIMB0072.md
UIMI0072.md

Queries the UIMV_SSN_VALIDITY table for records where the prior VERIS call returned a non-zero completion code or where dependent SSNs have a validation code of '4'.
Re-submits those SSNs through VERISBN.
Marks the original record's history indicator from '0' → '1' (historical).
Inserts a new active record with the updated VERIS results.
Writes an output file for downstream reporting.
If the re-verified SSN returns code '00000110' (retired/deceased), an additional record is inserted into the UIMV_SSN_RETIRED table (Table-23).
UIMB0072.md
UIMI0072.md
3. UIMI0726 / UIMB0726 — Accelerated Refunds Daily Extract (Multi-Layered Deceased Detection)

These programs combine three independent deceased-detection methods during the daily accelerated refunds extract :
UIMI0726.md
UIMB0726.md

Table

Layer

	

Method

	

Source


1	Input record check	If the master record's deceased indicator is already set, flag deceased and capture the date of death
2	Retired SSN table lookup	Query UIMV_SSN_RETIRED (Table-23) by SSN; if found, set deceased flag (date of death = zeros, since the table doesn't always carry one)
3	Live VERIS call	For claimants with total refund balance > $24.99 who are not already deceased and VERIS is available, call VERISB with SSN + DOB. If return code = '00000110', set deceased, capture date of death from VERIS, write response to VERIS copy file
View more

Circuit breaker: VERIS calls are automatically disabled for the remainder of the run if 20+ consecutive MQ connection errors (reason code 2033) occur, or total VERIS errors exceed 75.
UIMI0726.md
UIMB0726.md

The output master record's deceased indicator and date are set based on whichever layer triggered the flag.
UIMB0726.md

Death Trigger Processing
ZDLDTHU0 (JCL Job) → TDCBD16P (IMS DL/I Program)

This is a separate, daily death trigger batch job that processes external death notification records :
ZDLDTHU0.md

VERIFY step — Verifies integrity of 6 VSAM cluster files (LOP data/index, DAB data/index, Coded Abstracts, Employee VSAM). All 6 must pass (RC ≤ 4) before processing proceeds.
TDCBD16P — The main IMS DL/I program reads death trigger records from the DEATHTRG input file, retrieves policy/owner info from the LOP database (read-only), and updates the DAB database (exclusive).
Outputs 4 files:
FORMGEN — Form generation records (correspondence)
CONFLICT — Records requiring manual review
WORKLOAD — Task assignment records
BTCHJRNL — Audit trail
IMS log is backed up unconditionally (even on abend) to a GDG.
On success — The DEATHTRG file is deleted.
On abend — Recovery job ZDL08BU0 is triggered via CA-7, and all 4 output files are deleted and recreated empty for clean restart.
Other SSN Validation Programs
DXCB147U — SSN Format Validation

Validates that an input SSN conforms to the NNN-NN-NNNN format by checking all 11 character positions (3 digits, dash, 2 digits, dash, 4 digits) simultaneously.
DXCB147U.md

DXCBD29S — SSN Range Splitter

A batch file splitter that reads a sequential input file of SSNs and distributes records into 10 output files based on predefined SSN numeric range boundaries, with a control report of record counts per file.
DXCBD29S.md
DXCBD29S.md

L213DA (JCL Job) — Blank SSN Filter

Filters batch journal transaction records, excluding any record where the SSN field (positions 31–41, 11 characters) is all blank spaces, ensuring only records with populated SSNs proceed to the BAL0209 balancing program.
L213DA.md

Key Data Stores
SSN Validation And Deceased Check Data Stores

Data Store

	

Type

	

Purpose


UIMV_SSN_VALIDITY (Table-22)	DB2	Stores all VERIS SSN verification results — both successful and failed — for audit and compliance
UIMV_SSN_RETIRED (Table-23)	DB2	Records SSNs confirmed as deceased/retired by VERIS (return code '00000110'), with name, DOB, date of death, and payment ZIP codes
LAK2LDXP.VERIS.REQUEST	MQ Queue	Outbound SSN verification request queue
LAK2LDXP.VERIS.REPLY	MQ Queue	Inbound SSN verification response queue
VERSTIME	Sequential	Stores last VERIS processing timestamp
VERSQUEU	Sequential	Stores MQ queue manager name configuration
VERISCPY	Sequential	Audit file of VERIS responses for deceased claimants (written by UIMI0726/UIMB0726)
DEATHTRG	Sequential	External death trigger input records (consumed by ZDLDTHU0/TDCBD16P)
View more

Coverage caveat: This answer is bounded by the programs documented in the knowledge base. Additional SSN validation or deceased-detection logic may exist in programs, jobs, or streams outside the held slice (e.g., real-time CICS flows, IVR processes). The TDCBD16P program itself is referenced only via its JCL wrapper (ZDLDTHU0); its internal COBOL logic is not separately documented in the knowledge base.

What would you like to explore next?

VERIS return code meanings and handling

Batch schedule dependencies for SSN/deceased processing

Impact of deceased flag on benefit payments

_Citations:_
- Citation 1
- Citation 2
- Citation 1
- Citation 3
- Citation 3
- Citation 3
- Citation 3
- Citation 4
- Citation 5
- Citation 4
- Citation 5
- Citation 6
- Citation 7
- Citation 6
- Citation 7
- Citation 7
- Citation 8
- Citation 9
- Citation 10
- Citation 11
- Citation 12

## v3-Q5 (asked immediately after v3-Q4)

**Q:** What are the 16/16 and 16/17 screens in LOOPS used for?

**A** (13:07):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

The knowledge base does not contain any CICS screens identified as "16/16" or "16/17". LOOPS screens in the documented programs are typically referenced by transaction codes (e.g., D020) or BMS map names, not by a "nn/nn" numbering convention, and no document in the held knowledge spaces uses those identifiers for a screen.

Closest Documented Match: IMS Segments 16 and 17

The notation "16" and "17" does map directly to two well-documented LOOPS IMS database segments that are surfaced through CICS screens via the SPAD communication area. These are the closest documented candidates — but I cannot confirm they are what your "16/16" and "16/17" labels refer to. Here's what the knowledge base says about each:

Segment 16 — Remarks Information (LOOPLE16 / DB16)

This segment stores structured operator remarks attached to a claim. Its layout is defined in copybook LOOPLX16.cpy
LOOPLX16.cpy.csv
 :

DB16-REMARKS-SEQUENCE-NUMBER — Unique sequential ID for the remark within the claim
DB16-REMARKS-TITLE — 25-character title/heading
DB16-REMARKS-TEXT — 250-character free-text body
DB16-ORIG-REMARKS-ENTRY-OP-ID / DB16-ORIG-REMARKS-ENTRY-LOCOFF / DB16-ORIG-REMARKS-ENTRY-DATE — Who/where/when the remark was created
DB16-LAST-MODIFY-OPERATOR-ID / DB16-LAST-MODIFY-LOCAL-OFFICE / DB16-LAST-DATE-MODIFIED — Last-edit audit trail
30 × 1-byte filler positions

When a CICS program reads the claim from IMS, the Segment 16 data is copied into SPAD communication area slot 16 (SPADDX2K-LOOPLE16) so downstream CICS screens can display it.
DXCD035S-cbl.json
 Multiple programs insert DB16 segments — for example, UIMI0025 / UIMB0025 create SSN-validity remarks , DXCBDUDC creates "CANCELLED DEBIT CARD" remarks , and DXCBDVP1/DXCBDVP2 insert remarks via DL/I ISRT calls.
UIMI0025.md
UIMB0025.md
DXCBDUDC.md
DXCBDVP1.txt
DXCBDVP2.txt

Segment 17 — Free-Form Text (LOOPLE17 / DB17)

This segment stores longer free-form narrative text associated with nonmonetary determinations and other claim issues. Its layout is defined in copybook LOOPLX17.cpy
LOOPLX17.cpy.csv
 :

DB17-PHRASE-NUM — 5-digit phrase number (links to a standard determination phrase)
DB17-26B-HIST-IND — Historical indicator flag for 26B processing (values 0–9)
DB17-FF-TEXT — 576-character free-form text field (much longer than DB16's 250 characters)
DB17-PRIME-DATE — Primary date associated with the text entry
15 × 1-byte filler positions

Similarly, Segment 17 data is copied into SPAD slot 17 (SPADDX2K-LOOPLE17) for CICS screen access.
DXCD035S-cbl.json
 Programs like UIMI0003 / UIMB0003 transfer DB17 segments when migrating fraud nonmonetary issues from an old claim to a new claim.
UIMI0003.md
UIMB0003.md
 Audit program DXCBD09R detects and reports changes to DB17-FF-TEXT between before/after images.
DXCBD09R.md

Key Differences at a Glance
Segment 16 Vs Segment 17 Comparison

Attribute

	

Segment 16 (Remarks)

	

Segment 17 (Free-Form Text)


IMS segment name	LOOPLE16	LOOPLE17
Copybook	LOOPLX16.cpy	LOOPLX17.cpy
Journal copybook	LOOPCD16	LOOPCD17
Primary text field	DB16-REMARKS-TEXT (250 chars)	DB17-FF-TEXT (576 chars)
Title / Phrase	DB16-REMARKS-TITLE (25 chars)	DB17-PHRASE-NUM (5-digit phrase #)
Sequence numbering	DB16-REMARKS-SEQUENCE-NUMBER	N/A (keyed under parent nonmonetary)
Audit tracking	Full: operator, office, date (orig + last-mod)	Minimal: DB17-PRIME-DATE only
SPAD slot	Slot 16	Slot 17
Typical use	Operator notes, system-generated alerts (SSN issues, debit card cancellation)	Nonmonetary determination narratives, 26B processing text
View more
What to Check

The "16/16" / "16/17" naming convention may come from an operator manual, training guide, or screen-navigation reference that is not in the knowledge base. If you can share where you encountered these identifiers (e.g., a training document, a screen print, or a menu path), I can try to match them more precisely. The screen programs that present claim data via SPAD (such as DXCD035S) do load both segments for display, so they may be the programs behind whatever screen you're looking at.
DXCD035S-cbl.json

Would you like to explore further?

Find the CICS screen program

Deep-dive on DB16 remarks processing

Deep-dive on DB17 free-form text

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 5
- Citation 6
- Citation 7
- Citation 8
- Citation 2
- Citation 9
- Citation 10
- Citation 11
- Citation 2

## v3-Q6

**Q:** How does LOOPS determine whether a weekly certification was submitted by phone (IVR), on the web, or entered by staff?

**A** (13:08):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

LOOPS determines the submission channel of a weekly certification by examining two fields on the certification record: the Operator ID and the Terminal ID. The same logic is applied consistently across multiple programs in the documented codebase. Here's how it works:

The Core Decision Rule

The classification is a simple two-field test applied to every certification record, whether it comes from the PAYVSAM (payment) file or the NOPAY (no-payment) file :
DXCBDA2R.md
DXCBDA2R.md

Web (Online): Operator ID = 9000 AND Terminal ID = '7777'
Phone / IVR (Telephone): Terminal ID = '7777' BUT Operator ID ≠ 9000
Manual / Staff (P100): Terminal ID ≠ '7777' (any other terminal)

The key insight is that both Web and IVR share the same Terminal ID '7777' — it is the Operator ID 9000 that distinguishes Web from Phone. All other terminal IDs default to staff entry.

Which Fields Are Checked

The specific field names depend on the source file :
DXCBDA2R.md
DXCBDA2R.md

Certification Channel Fields By Source File

Source File

	

Operator ID Field

	

Terminal ID Field


PAYVSAM (payment records)	BP88-OPERATOR-ID-CERT	BP88-TERMINAL-ID-CERT
NOPAY (no-payment records)	NOPAY-OPERATOR-ID-ENTRY	NOPAY-TERMINAL-ID-ENTRY
View more
How the Indicator Is Stored Downstream

Different programs encode the result in different ways:

DXCBDA2R (Daily Audit Report) sets one of three Boolean working-storage flags — WEB, PHONE, or MANUAL-P100 — and uses them for channel-level sub-counters throughout its audit categorization.
DXCBDA2R.md
DXCBDA2R.md
UIMI0440 / UIMB0440 / UIMI0443 (check-print programs) set a single numeric indicator field F70-PHONE-IND on the check output record :
UIMI0443.md
UIMI0440.md
UIMB0440.md
'2' = Automated / IVR (Web: Operator 9000 + Terminal 7777)
'1' = Phone-assisted (Terminal 7777, non-9000 operator)
'0' = In-person / staff entry (any other terminal)
DXCBD12T (Regional Payment Activity Report) classifies into three counters: WEB-CERTS, TELEPHONE-CERTS, and NON-TELEPHONE-CERTS using the same Terminal ID / Operator ID logic.
DXCBD12T.md
Important Context
The upstream systems (IVR telephony and the web front-end) are what stamp these Operator ID / Terminal ID values onto the certification record before LOOPS batch processing sees them. The IVR system and the web portal both use Terminal ID '7777' as a convention; the web portal additionally stamps Operator ID 9000. Staff entering certifications via CICS screens use their own operator IDs and real terminal IDs, which will never be '7777'.
This classification is derived by construction — the documented programs compute the channel from these two fields but, in the documented programs, do not validate or reject records if the combination is unexpected. The pattern holds in all documented programs, but programs or streams outside the knowledge base may handle it differently.
Want to explore further?

How does DXCBDA2R use the channel classification in its reports?

How does UIMI0440 use the phone indicator on checks?

What do we know about how IVR and web certifications enter LOOPS?

_Citations:_
- Citation 1
- Citation 2
- Citation 1
- Citation 2
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 5
- Citation 6

## v3-Q7 (asked immediately after v3-Q6)

**Q:** What is JPAY and how does it connect to LOOPS?

**A** (13:09):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

The knowledge base does not contain any system, process, program, job, or interface named "JPAY." I searched across the payment-related documentation in the connected spaces and found no match for that term.

What the Knowledge Base Does Document for Payments

The documented payment infrastructure in LOOPS uses these names and concepts:

LoopPay — the batch payment processing pipeline that reads from the LOOPPAY VSAM cluster, splits transactions via DXCBP10S into 10 parallel streams, and processes them through IMS database updates (jobs like L2BPD12, ZLPDBPU0–ZLPDBPU9)
PAYVSAM — the payment VSAM file that holds certified payment records and feeds downstream processing (check print, direct deposit, debit card, electronic banking)
Payment output streams documented in UIMI0143 and ZUMDA1R2: Non-Dollar/Non-File, Electronic Banking (EBPAY), Direct Deposit Bank UI (DDBNKUI), and others
Debit Card payments — tracked via a Processed Indicator value of '3' and reported through dedicated report streams
Check Register and Payment Activity Reports — produced by programs like DXCBD49S, FLEBD81R, TNCBD15E, etc.
Possible Explanations

"JPAY" may be:

A colloquial or informal name used by staff for one of the documented payment processes above
A reference to an external vendor or system (e.g., a debit card provider or banking partner) whose interface is outside the LOOPS knowledge base
A different NJ DOL system that sits outside the LOOPS mainframe scope documented here

Could you clarify where you encountered the term "JPAY"? For example, was it in a job name, a conversation with operations staff, or a process document? That would help me narrow down what documented LOOPS component it might correspond to.

## v3-Q8

**Q:** How are municipality (MUNC) codes validated in LOOPS?

**A** (13:10):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

The knowledge base documents municipality (MUNC) code handling across several programs and contexts. This is a synthesized summary drawn from multiple source documents.

Where MUNC Codes Originate

The municipality code is stored in the IMS database on the Basic Claim segment (Segment 01), in the field MUNIC-CODE of copybook LOOPDB01. When batch programs process journal records, the municipality is captured the first time a Segment 01 (Basic Claim) record appears for a given SSN :
DXCBW30E.md

A Municipality Switch (MUNCI-SW) is set to 'Y' when a Basic Claim is processed, and the code is stored in MUNCI-CUR
When a new SSN is detected, the switch resets to 'N' and the municipality defaults to zero until a Basic Claim is encountered for the new claimant
All subsequent records for the same SSN carry forward the municipality established from that Basic Claim
Range Validation in Claim Type Classification

Multiple programs — including DXCBW30E, DXCBW39E, and DXCBW39U — apply the same tiered validation logic in their Claim Type Classification routine (X200-DO-TYPECLM). The validation depends on the claim type :
DXCBW30E.md
DXCBW39E.md
DXCBW39E.md

MUNC Code Validation By Claim Type

Claim Type

	

Condition

	

MUNC Validation

	

...


Type 4 — Interstate	Program Code = 11 or 12	No range check — MUNC passed through as-is	...
Type 3 — Out-of-State / Special Office	Local Office = 999 or 997	MUNC must be > 01000 AND < 77000 (i.e., 01001–76999)	...
Type 1 — In-State Local Municipality	MUNC between 05500 and 07599	Used as-is (already within valid range by definition)	...
Type 2 — All Other In-State	Default / catch-all	Used as-is	...
View more

The decision flow in the documented programs is :
DXCBW30E.md
DXCBW39E.md

Is Program Code 11 or 12? → Type 4 (Interstate). Use MUNC as-is. Exit.
Is Local Office 999 or 997? → Type 3 (Out-of-State). Validate MUNC in range 01001–76999; if out of range, override to 77777. Exit.
Is MUNC between 05500 and 07599? → Type 1 (In-State Local). Use MUNC as-is. Exit.
Otherwise → Type 2 (All Other). Use MUNC as-is. Exit.
Numeric Validation for Internet Certification

Program DXCBD50E applies a separate, stricter check when building Internet certification records: the municipality code (MUNIC from Segment 02) must be numeric. If it is not numeric, the program displays a warning message with the claimant's SSN, zeros out the SSN, and skips the record entirely — no Internet certification record is written. The rationale documented in the source is that a non-numeric MUNC "indicates a data quality issue that also signals a potentially invalid SSN".
DXCBD50E.md

Municipality Reference Table Lookup

Program DXCBW40R (Municipality Claims Report) goes a step further by searching a municipality reference table to resolve MUNC codes to named municipalities for reporting. It uses an optimization: if the current record's MUNC code (MUNS-CODE-IN) matches the previous record's (PREV-CNTY-MUNS-NO), it skips the table search and reuses the previously matched position (HOLD-INDEX-2).
DXCBW40R.md
DXCBW40R.md

What Is Not in the Knowledge Base
The actual populated values of any municipality reference table (e.g., the mapping of code 05501 to a specific town name). The table layouts are documented, but the values are operations-maintained data.
Whether any CICS online program validates MUNC codes at the point of data entry — the documented validation is all in batch programs.
Whether there is a master municipality code table that defines the universe of valid NJ municipality codes beyond the range checks described above.
Would you like to explore further?

How does the municipality reference table lookup work in DXCBW40R?

How are MUNC codes used in the weekly extract and reporting programs?

Tell me more about DXCBD50E's municipality and SSN validation

_Citations:_
- Citation 1
- Citation 1
- Citation 2
- Citation 3
- Citation 1
- Citation 2
- Citation 4
- Citation 5
- Citation 6
