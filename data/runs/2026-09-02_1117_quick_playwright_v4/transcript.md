# 2026-09-02_1117_quick_playwright_v4

- **Backend:** quick (transport: playwright)
- **Bank:** v4 (`question_sha256` 5da69eeb3130…)
- **Agent:** engineering_onboarding_specialist (`30b0228b-b58a-43ad-818b-2f262f11108f`)
- **Conversation:** `cb197047-bed1-4e80-8e5c-3cb16b7caa77`
- **Model:** Advanced
- **Started:** 2026-09-02 11:04
- **Finished:** 2026-09-02 11:17
- **Status:** complete
- **Questions asked:** 8, answered: 8

## v4-Q1

**Q:** Our new-hire crossmatch spec says the replacement system's SG01 pipeline can only pull data forward based on DB2 RSA_NONMON entries. What do the SG01 and RSA_NONMON DB2 tables contain in LOOPS, and which batch jobs read or write them?

**A** (11:06):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

Here is what the knowledge base documents about these two DB2 tables and the batch jobs that touch them. Important caveats up front:

The knowledge base has no process by the names "SG01 pipeline" or "new-hire crossmatch." Those appear to be names from your replacement-system spec. I've mapped them to the nearest documented DB2 objects below, but please confirm with an SME that the spec is indeed referring to these tables.
The field inventories below are synthesized from SQL in JCL and from CICS program business rules across multiple documents — they represent fields that appear in documented code, not necessarily the full DDL.
OTDUIMP.UIMT_SG01_CLAIMANT — the Claimant Table

This is the master claim-level table for UI benefits. It is keyed on the composite (SG01_IDN_SSN, SG01_CDE_PROGRAM_UIB, SG01_DTE_CLAIM_UIB) — SSN + program code + claim date.
L2PUA003.txt
NAVAWAGE-cbl.json
UMODPMTS-cbl.json

Documented columns (synthesized from L2PUA003.txt, NAVAWAGE-cbl.json, UMODPMTS-cbl.json, UMODWAGE-cbl.json):

UIMT_SG01_CLAIMANT — Documented Columns

Column

	

Description

	

Source


SG01_IDN_SSN	Claimant SSN (PK)	L2PUA003, NAVAWAGE, UMODWAGE
SG01_CDE_PROGRAM_UIB	UI Benefit Program Code (PK)	L2PUA003, NAVAWAGE
SG01_DTE_CLAIM_UIB	UI Benefit Claim Date (PK)	L2PUA003, NAVAWAGE
SG01_DATE_BEGIN_BASE	Base Period Begin Date	NAVAWAGE, UMODWAGE, UMODPMTS
SG01_DATE_END_BASE	Base Period End Date	NAVAWAGE, UMODWAGE, UMODPMTS
SG01_BEN_YEAR_END	Benefit Year End Date	UMODPMTS
SG01_BAL_CLAIM_REM	Remaining Claim Balance	UMODPMTS, L2PUA003
SG01_POT_WEEKS_DUE	Potential Weeks Due	UMODPMTS
SG01_NUM_WKS_PAID	Number of Weeks Paid	UMODPMTS
SG01_MBA	Maximum Benefit Amount	L2PUA003
View more
OTDUIMP.UIMT_RSA_NONMON — the RSA Non-Monetary Table

This table stores non-monetary RSA (Reemployment Services and Eligibility Assessment) records for UI claims — essentially proofing/adjudication tracking for non-monetary eligibility issues.
L2UDB020.md
L2UDB020.md

Documented columns (from L2UDB020.md):

UIMT_RSA_NONMON — Documented Columns

Column

	

Description

	

Source


IDN_SSN	Claimant SSN	L2UDB020
TMS_RECORD_LOAD	Record Load Timestamp	L2UDB020
CDE_PROGRAM_UIB	UI Benefit Program Code	L2UDB020
DTE_CLAIM_UIB	UI Benefit Claim Date	L2UDB020
IDN_HIST	Historical Record Identifier	L2UDB020
DTE_PROOFING	Proofing Date	L2UDB020
IDN_LOGON_ID	Logon ID of processing user	L2UDB020
IDN_USERNAME	Username of processing user	L2UDB020
TMS_RECORD_UPDT	Record Last Update Timestamp	L2UDB020
View more
Batch Jobs that Read or Write These Tables
Batch Jobs Touching UIMT_SG01_CLAIMANT And UIMT_RSA_NONMON

Job

	

Table(s) Accessed

	

R/W

	

...


L2PUA003	UIMT_SG01_CLAIMANT, UIMT_SG11_NONMON, UIMT_SG02_PAYMENT, UIMT_IDENTITY_THEFT_SSN	Read	...
L2UDB020	UIMT_RSA_NONMON	Read	...
L2FTPRS2	(reads the L2UDB020 sorted output file, not the DB2 table directly)	—	...
ZUMDDCU1	(routes journal records to a DD named SG01IBA — IMS journal, not a direct DB2 write)	—	...
View more

CICS online programs that query UIMT_SG01_CLAIMANT (not batch, but relevant for impact):

NAVAWAGE — retrieves claim info (base period, employers, dependants, pension)
UMODPMTS — retrieves active claimant summary (balance, weeks paid, benefit year end)
UMODWAGE — retrieves claim info similarly to NAVAWAGE
What the Knowledge Base Does Not Document
No batch job is documented as writing to either of these DB2 tables. The writes likely happen through CICS online transactions or through a DB2 load process outside the held batch-job slice. This is a coverage gap, not a statement that no writer exists.
The name "SG01 pipeline" does not appear in the knowledge base. The closest match is the batch extract job L2PUA003, which heavily queries UIMT_SG01_CLAIMANT in a complex fraud-detection SQL.
The name "new-hire crossmatch" does not appear in the knowledge base at all. If this is a process that cross-references new-hire wage records against UI claims, it may live outside the LOOPS modules covered here — possibly in the Wage Record or employer-side systems.
Would you like to dig deeper into any of these areas?

L2PUA003 fraud-extract SQL breakdown

L2UDB020 → L2FTPRS2 data flow

CICS online access to SG01

Related DB2 tables (SG02_PAYMENT, SG11_NONMON)

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 5

## v4-Q2

**Q:** How does LOOPS process the daily new hire file today? Walk me through the batch jobs and programs, and what they produce.

**A** (11:08):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

Here is the documented daily New Hire crossmatch pipeline, synthesized from multiple JCL and COBOL source documents across the Daily CA-7 v2 knowledge space. The ordering below is derived from the data-dependency chain visible in the JCL (each job's inputs are the prior job's outputs); it is not read from a single CA-7 schedule-dependency document, so treat the exact sequencing as the most-likely flow, subject to SME confirmation.

Phase 1 — Ingest & Dedup (upstream)

An upstream companion job L2NHD011 produces the New Hire Output Detail file (320-byte records, SSN in positions 1–9). The knowledge base references this job as the source of L2NHD001's SORTHIRE input, but L2NHD011 itself is not fully documented in the held slice.
L2NHD001.md

Program DXNHCM29 reads the raw New Hire input and deduplicates by SSN. It produces three output streams :
DXNHCM29.md

Clean file — unique SSN records (or acceptable duplicates where SSN + last name match)
Duplicate file — true duplicates written aside
Duplicate SSN Report — printed report of flagged duplicates
Phase 2 — DB2 Load (ZUMDNHU1 → UIMI0134)

Job ZUMDNHU1 invokes program UIMI0134 ("Database Load for New Hire"), which runs daily to load the DB2 table UIMT_NEWHire.
ZUMDNHU1.md
UIMI0134.md
 For each New Hire detail record it:

Validates Date of Birth, Date of Hire, SSN, Employer FEIN, ZIP codes, and State code (6 checks total)
Defaults all-zero DOB to 00010101; rejects future hire dates; applies leap-year rules
Inserts validated records into UIMT_NEWHire with a load timestamp
Counts and reports rejected records

After the DB2 load, job ZUMDNHU1 also runs a purge step (DXNHCM02) to delete aged New Hire records from UIMT_NEWHire and produce a New Hire Refund Output Report.
ZUMDNHU1.md
DXNHCM02.md

Phase 3 — Account Refresh, Merge & Split (L2NHD001)

Job L2NHD001 is the central consolidation and distribution job. It has roughly 10 internal steps :
L2NHD001.md

L2NHD001 Internal Steps

Step

	

Program

	

What it does


DXNHCM05	DXNHCM05	Refreshes Pay Account Detail from VSAM Loop-Payment backup → new GDG generation
DXNHCM07	DXNHCM07	Refreshes TRA Account Detail from Check-Laser + No-Pay backups → new GDG generation
DXNHCM09	DXNHCM09	Refreshes No-Pay Account Detail from No-Pay backup → new GDG generation
SORT4F	SORT	Copies DDU Checks backup into a fresh DDU New Detail work file
DXNHCM06	DXNHCM06	Refreshes T4F Account Detail merging with DDU New Detail → new GDG generation
DXNHCM04	DXNHCM04	Consolidates all four account types (Pay + NoPay + TRA + T4F) into a single 80-byte PAYNOPAY file
SORTPNP	SORT	Sorts PAYNOPAY by SSN ascending, date descending
SORTHIRE	SORT	Sorts New Hire Output Detail (from L2NHD011) by SSN ascending
SPLITNH	SORT	Splits sorted New Hire into 10 partitions by SSN range
SPLITPNP	SORT	Splits sorted PAYNOPAY into the same 10 SSN-range partitions
View more

The 10-way SSN range split uses fixed boundaries (e.g., 000000000–115502000, 115502001–137444750, etc.) to enable parallel downstream processing.
L2NHD001.md

Phase 4 — Parallel SSN Crossmatch (ZULDNHR0–ZULDNHR9)

Ten parallel jobs — ZULDNHR0 through ZULDNHR9 — each run IMS batch program DSNMTV01 using PSB LOPGMPnn, executing the COBOL matching logic of UIMI0158.
ZULDNHR1.md
UIMI0158.md
 Each job:

Reads one NEWHIRE split file + the corresponding PAYNOPAY split file
Walks both sorted files in an SSN merge-match loop:
SSN match → builds a 479-byte cross-match record combining New Hire detail with claim data (Program Code, Date of Claim, CWE date, source type P1/N2/N3/T3/F4)
No match on PAYNOPAY → falls back to IMS DB01 lookup by SSN; if a claim < 35 days old is found, creates a cross-match record with source = DB
Calculates 8 weekly date-range buckets around the hire date; zeroes out buckets outside the claim window; sets LETTER = N if all 8 are empty
Retrieves Void Code and Backup Flag from IMS DB02 payment segment
Validates DOB, hire date, SSN, FEIN, ZIP, state on each output record
Writes valid records to CMATCH.SPLITnn.DTL (479-byte FB)
Phase 5 — New Hire LLR / IMS Update (ZULDNHU0–ZULDNHU9)

Ten parallel jobs — ZULDNHU0 through ZULDNHU9 — each run DSNMTV01 as an IMS batch update using PSB LOPUnn.
05_job_purpose_in...
ZULDNHU6.md
 Each job:

Reads the corresponding CMATCH file from Phase 4
Looks up VSAM code tables and employee address reference data
Updates IMS databases (LOPDnnnn / LOPXnnnn) with crossmatch results
Produces multiple outputs:
BPC174–BPC179 — Benefit Plan Carrier transaction files (six separate files)
BTCHJRL4 — Batch journal
Primary output and report files

Each ZULDNHU* job has a CA-7 recovery trailer that DEMANDs a backout job (ZUL06BUn) on any abend.
ZULDNHU6.md
ZULDNHU0.md

Phase 6 — TRA Remarks Generation (UIMI0147)

Program UIMI0147 (run from a ZULDNHU* job context) generates IMS remark records in LOOPDB16 for TRA crossmatch conflicts, populating "DATE OF HIRE:", employer name/FEIN, and hire-related fields for investigator review.
UIMI0147.md

Summary Pipeline Diagram
L2NHD011 (upstream)  →  DXNHCM29 (dedup)
                              │
                    ZUMDNHU1 (DB2 load + purge)
                              │
                    L2NHD001 (refresh → merge → sort → 10-way split)
                         ╱         ╲
              NEWHIRE.SPLIT*    PAYNOPAY.SPLIT*
                         ╲         ╱
              ZULDNHR0–9 (parallel SSN crossmatch → CMATCH files)
                              │
              ZULDNHU0–9 (parallel IMS update → BPC files + journals)

Key Data Stores Touched
New Hire Pipeline — Data Stores

Store

	

Type

	

Read/Write

	

...


UIMT_NEWHire	DB2	Write (INSERT)	...
UIMT_NH_CROSSMATCH	DB2	Read (online inquiry)	...
LOOPDB01 (DB01)	IMS	Read	...
LOOPDB02 (DB02)	IMS	Read	...
LOOPDB16	IMS	Write	...
LOPDnnnn / LOPXnnnn	IMS	Read+Write	...
Pay/NoPay/TRA/T4F GDG files	Sequential	Read+Write	...
NEWHIRE/PAYNOPAY split files	Sequential	Write then Read	...
CMATCH split files	Sequential	Write then Read	...
BPC174–BPC179	Sequential	Write	...
View more
What the Knowledge Base Does Not Document
How the raw new hire file arrives — the ingest from the National Directory of New Hires or state W-4 feed is outside the held code slice
Job L2NHD011 — referenced as the New Hire Output Detail source but not fully documented
The batch job that populates UIMT_NH_CROSSMATCH — the CICS programs (TAG001, LOBCN100, LOBDN150) read and update it, but the batch job that initially inserts crossmatch records into this DB2 table is not explicitly documented in the held slice
Downstream consumers of the BPC files — these Benefit Plan Carrier transaction files feed further processing outside the LOP batch boundary
What would you like to explore next?

Cross-match business rules detail

New Hire record layout

Online inquiry flow

Create a Word document of this walkthrough

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 3
- Citation 5
- Citation 1
- Citation 1
- Citation 6
- Citation 7
- Citation 8
- Citation 9
- Citation 9
- Citation 10
- Citation 11

## v4-Q3

**Q:** When a new-hire crossmatch hit comes in, under what conditions does LOOPS update the claimant's return-to-work date, and where is that date stored?

**A** (11:09):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

This is well-documented across multiple programs. The answer spans the batch crossmatch pipeline (program UIMI0147), the IVR system (LOI6FUN6), and several CICS online screens. Here's the full picture, synthesized from multiple source documents — all citations below are from retrieved knowledge-base content.

Where the Return-to-Work Date Lives

The RTW date is stored in two places depending on claim type:

Table

Store

	

Field

	

Format

	

...


IMS LOOPDB01 — DB01 (Claim Basic) segment	DB01-DATE-RETURN-WORK	Internal packed F6 (YYYYMMDD); zero = no date	...
DB2 TNPV_CLAIM	DTE_RETURN_WORK	YYYY-MM-DD; 0001-01-01 = null sentinel	...
View more

On CICS screens (e.g., LOH3C015), the date is displayed by converting DB01-DATE-RETURN-WORK from F6 to display format when it's > 0; if zero, the field displays as zero.
LOH3C015-cbl.json

Batch Crossmatch RTW Update — UIMI0147 (paragraph 2300-UPDTE-RTW-DB01)

This is the core batch logic, run inside the ZULDNHU0–9 parallel jobs. The update only fires for non-TRA claims (source ≠ T3) and only when the existing DB01-DATE-RETURN-WORK is zero (no RTW date currently on file).
UIMI0147.md

Precondition: Read Additional Claim Segments (DB10)

Before making the RTW decision, the program reads all DB10 (Additional Claim) segments under the claimant's DB01 parent using GNP (Get Next in Parent) calls. For each DB10 found, it captures DB10-DATE-ADD-CLAIM and DB10-SEP-CODE-ADD. Two switches track the results:

FOUND-10-SW — Y if any DB10 segment exists, N if none
DOA-FOUND-SW — Y if a valid date of additional claim was found (non-blank filler), N if not
Decision Tree

The decision logic in 2300-UPDTE-RTW-DB01 evaluates the following conditions in order :
UIMI0147.md

RTW Update Decision Rules — UIMI0147 Paragraph 2300-UPDTE-RTW-DB01

\#

	

Condition

	

Action

	

...


1	FOUND-10-SW = 'N' (no DB10 segment exists)	Re-establish parent; convert hire date to F6; set DB01-DATE-RETURN-WORK = hire date; REPL DB01	...
2	DOA-FOUND-SW = 'N' (DB10 exists but no valid additional claim date)	Same as #1 — set RTW to hire date	...
3	HM-DATE-HIRE-SAVE = 0 (hire date is zero/missing)	Re-establish parent; skip update	...
4	WS-DATE-ADD-CLAIM > DATE-SAVE (additional claim date is after hire date)	Set RPT-RTW-SW = 'Y', ZERO-SW = 'Y'; write RTW exception report entry (3060-RTW-RPT-NH); re-establish parent; skip update	...
5	Otherwise (hire date ≥ additional claim date)	Convert hire date to F6; set DB01-DATE-RETURN-WORK = hire date; re-establish parent; REPL DB01	...
View more

In plain language: the batch job sets the RTW date to the New Hire hire date, unless:

The hire date itself is zero/missing
The claimant filed an additional claim after the hire date (meaning they may have become unemployed again — updating RTW would be incorrect)
The claim already has an RTW date on file (the entire 2300-UPDTE-RTW-DB01 path is only reached when DB01-DATE-RETURN-WORK = 0)
When RTW Is Not Updated: Exception Report + Special Remark

When condition #4 fires (additional claim date > hire date), two things happen :
UIMI0147.md

RTW Exception Report — a line is written to RTW-RPT-FILE containing SSN, Program Code, Date of Claim, FEIN, hire date, reported date, employer name, additional claim date, and separation code
Special IMS Remark — paragraph 3067-CREATE-REM-SEG inserts a DB16 remarks segment titled NH RTW NOT UPDATED with text like:

NEW HIRE DATE OF HIRE: MM-DD-YYYY WITH [FEIN] [EMPLOYER NAME] NOT UPDATED TO CLAIM BASIC SINCE ADDITIONAL DATED MM-DD-YYYY

TRA Claims (Source = T3) — Different Path

For TRA claims, UIMI0147 does not use the IMS DB01 DATE-RETURN-WORK directly. Instead, it queries DB2 TNPV_CLAIM.DTE_RETURN_WORK for the active claim. If the result is 0001-01-01 (null sentinel), the internal field is set to zero; otherwise the DB2 date is converted to F6 format. This value then drives the letter-generation decisions, but the batch program does not execute the 2300-UPDTE-RTW-DB01 paragraph for T3 sources — it skips the IMS RTW update entirely.
UIMI0147.md

Other Entry Points That Can Set the RTW Date

Beyond the batch crossmatch, the RTW date can also be written by:

IVR system (LOI6FUN6): When a claimant calls the IVR and reports a return-to-work date > 0, the value from IVR-IN-RETURN-TO-WORK is copied directly into DB01-DATE-RETURN-WORK and a REPL is issued against LOOPDB01. If the REPL fails, problem code F6RP is returned to the IVR.
LOI6FUN6-cbl.json
CICS screen DXCC121S (basic claim entry): Converts the entered RTW date from display format (F1/MMDDYY) to internal F6 and stores it in DB01-DATE-RETURN-WORK.
CICS screen LOAK025S: Converts RTW from F2 format to F6 and stores on the basic claim segment.
LOAK025S-cbl.json
CICS screen LOH3C015 (conversation C015/C016): Maps the computed RTW date (WS-COMP-DATE-RTWI) to the DB01 segment during claimant updates.
LOH3C015-cbl.json
Summary

The batch new-hire crossmatch (in UIMI0147) is the only path that automatically stamps the hire date as the RTW date. Its guard conditions are:

Source is not T3 (non-TRA)
Existing DB01-DATE-RETURN-WORK is zero (no RTW already on file)
Hire date is not zero
Hire date is on or after the most recent additional claim date (or no additional claims exist)

If all four hold, DB01-DATE-RETURN-WORK in IMS LOOPDB01 is set to the hire date via an IMS REPL call. Otherwise, the RTW is left alone and the conflict is documented via the RTW exception report and the NH RTW NOT UPDATED remark.

Would you like to dive deeper into a related area?

Letter generation logic in UIMI0147

Crossmatch remark details

CICS screens (LOBDN150 / LOB8N250)

_Citations:_
- Citation 1
- Citation 2
- Citation 2
- Citation 2
- Citation 2
- Citation 3
- Citation 5
- Citation 1

## v4-Q4

**Q:** The pension spec replaces the manual process where staff compute pension reductions in Excel and key them into LOOPS. How does LOOPS apply a pension reduction when paying a weekly benefit, and does LOOPS itself compute the weekly reduction amount from the pension details (for example, prorating a lump sum)?

**A** (11:10):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

This is an excellent architecture question with a clear two-part answer from the documented source code. Here's what the knowledge base shows, synthesized across multiple programs.

Part 1: How LOOPS Applies the Pension Reduction at Payment Time

LOOPS applies pension as a simple dollar-for-dollar subtraction from the Weekly Benefit Amount (WBA), applied after earnings reductions but before garnishment and tax withholding. The pattern is consistent across every documented payment path:

The core formula (per certification week):

Adjusted WBA (AWBA) = WBA − Pension Amount

If Pension ≥ WBA → AWBA is set to zero; no benefit is payable for that week. Garnishment, tax withholding, and further deductions are all skipped.
LO9JC23R-cbl.json
If Pension < WBA → AWBA = WBA − Pension. Processing continues to garnishment deduction, then tax withholding.
LO9JC23R-cbl.json

Where this logic runs (in the documented programs):

Table

Context

	

Program

	

Notes


Weekly Certification (CICS)	LOAI021S	Applies per-week: TWA-AWBA1 = TWA-WBA1 − TWA-PEN1, then TWA-AWBA2 = TWA-WBA2 − TWA-PEN2; totals both weeks
Payment Processing (CICS)	DXCP020S, DXCP021S	Same per-week subtraction using TWA-PEN1/TWA-PEN2
EUB Batch Projection	LO9JC23R	Uses WRK-PENS against WS-WBA1 each week
Payment Recalculation	DXCBD53S, DXCD072S	AWBA = WBA Pay − Pension Deduction
Payment Inquiry (display-only)	DXCA204S	AWBA-AMT = DB02-WBA-PAY − DB02-PENSION-AMT; if negative, displays zero
Void/Reissue	WWCP042S	Same subtraction on recalculated payments
View more

For two-week certifications, pension is applied independently to each week, and the totals are summed afterward: Total AWBA = Week 1 AWBA + Week 2 AWBA.
LOAI021S-cbl.json
LOAK025S-cbl.json

Part 2: Does LOOPS Compute the Weekly Amount from Pension Details?

No — in the documented programs, LOOPS does not prorate or compute a weekly pension reduction amount from raw pension details (monthly amount, lump sum, etc.). LOOPS consumes a pre-determined weekly dollar amount that is already stored on the claim.

Here's how the pension amount gets onto the claim:

Non-Monetary Determination (Issue Code 15): A staff member enters a pension amount on the non-monetary determination screen (PENSION-AMTI). Program DXCD061S (paragraph 7120-NON-PRIM-ISS-15) stores that screen value directly into the basic claim segment field DB01-PENSION-AMT and sets the Pension Indicator (DB01-PENSION-IND).
DXCD061S-cbl.json
WWCD061S-cbl.json

Pension Indicator values (from DXCP151S):

0 = No pension
1 = Fixed amount (pension start date equals claim date)
2 = Table-based / fixed amount on basic record (pension start date ≠ claim date)
3 = Table or zero

At payment time, the system looks up the pension amount based on the indicator:

If indicator = 1 → uses DB01-PENSION-AMT directly from the basic segment
If indicator = 2 → first checks a temporary pension table for the claim week; if no entry found, defaults to DB01-PENSION-AMT from the basic segment
If indicator = 3 → checks the pension table; if no entry found, uses zero (not the basic segment amount)

Critically: in none of these paths does LOOPS perform arithmetic on a monthly pension, an annual pension, or a lump sum to derive the weekly offset. The field DB01-PENSION-AMT is whatever dollar amount was entered on the non-monetary determination screen. Any proration or conversion from raw pension source data to a weekly offset amount happens outside LOOPS — historically in the Excel-based manual process you described, and in the future via the replacement pension spec's SG01 pipeline.

Summary

LOOPS is a pension-amount consumer, not a pension-amount calculator. It stores a pre-computed weekly offset on DB01-PENSION-AMT, subtracts it dollar-for-dollar from the WBA each week, and floors the result at zero. The intelligence about how to derive that weekly figure from raw pension data (monthly amounts, lump sums, employer contribution percentages, start/end dates) lives entirely outside the payment engine — today in the staff's manual Excel process, and in the future in whatever the replacement spec implements.

This is important for the new spec's design: the replacement system must deliver a ready-to-subtract weekly dollar amount into the PENSION-AMT field (or its DB2 equivalent SG01_PENSION_AMT), because LOOPS payment programs will not interpret or transform it further.

Would you like to explore any related area?

Pension table lookup logic

Pension-garnishment interaction

UIMI0440 offset arithmetic

_Citations:_
- Citation 1
- Citation 1
- Citation 2
- Citation 9
- Citation 10
- Citation 11

## v4-Q5

**Q:** Our SSN validation spec routes the new check through ICON's UIQ, with deceased checks out of scope for now. What does LOOPS use for SSN and deceased verification, and where do the results land?

**A** (11:12):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

This is a rich question that touches two separate VERIS-mediated services and several storage endpoints. Here's what the documented programs show, synthesized across the CICS and Daily CA-7 knowledge spaces.

The External Service: VERIS

LOOPS does not implement its own SSN validation or deceased-detection logic. Both functions are delegated to an external service called VERIS (the SSA — Social Security Administration — verification system). VERIS is called with the claimant's SSN and Date of Birth and returns a rich response including validation details and a key return code.
SARN114S-cbl.json

VERIS is accessed through two different interface modules depending on context:

Table

Context

	

Module

	

Transport

	

...


CICS (online)	VERISO (dynamically called)	MQ queue LAK2LDXP.VERIS.REQUEST	...
Batch	VERISB (statically called)	MQ request/reply queues	...
View more
Part 1: SSN Validation
Online — Claim Registration

When a new UI claim is being filed, programs DXCC111S and DXCC122S invoke VERISO after all screen-level edits have passed. The SSN (SSNI) and Date of Birth (DATE-BIRTHI) are sent to VERIS, and the response returns :
DXCC111S-cbl.json

VERIS-COMPCODE — completion code (0 = success)
VERIS-REASON — reason code
VERIS-SSN-RETCDE — the SSN-specific return code (the critical field)
DOB code, DOB string, age range, SSN assignment range, and state of issuance
Online — Standalone SSN Verification Screen

Program LO8JSSNV (transaction LO8J) provides a dedicated CICS screen for SSN verification. It validates that the SSN is numeric, validates DOB is numeric, then submits both to VERIS via the MQ queue LAK2LDXP.VERIS.REQUEST with EBCDIC-to-ASCII conversion.
LO8JSSNV-cbl.json

Batch — SSN Validity Re-Verification

Program UIMI0072 performs daily batch re-verification of SSN validity records that previously failed VERIS or whose dependents have pending re-checks. It selects active records from the UIMV_SSN_VALIDITY DB2 table (Table-22) where History_Indicator = '0' and either the MQ Completion Code ≠ 0 or any dependent's SSN Validation Code = '4'. It calls VERISB for each, updates the validity record, and writes results to a Validity output file.
UIMI0072.md

Interstate SSN Inquiry (Separate System)

Program INPOIQ00 handles interstate SSN inquiries within the NJ ICON system — this is a different function. It sends SSN inquiries to a Florida hub for cross-state data retrieval and stores results in the SSN Holding File (INFLIQ00 VSAM). This is not the VERIS-based SSN validation; it's a separate inter-state information exchange.
INPOIQ00-cbl.json

Note on "ICON's UIQ": The knowledge base documents INPOIQ00 (transaction IBIQ) as ICON's SSN inquiry program. The literal name "UIQ" does not appear in retrieved sources. INPOIQ00 may be what your spec references, but I cannot confirm the name "UIQ" from the knowledge base — please verify with the ICON team.

Part 2: Deceased Verification

Deceased detection in LOOPS is a by-product of the VERIS SSN call, not a separate service. The magic return code is:

VERIS-SSN-RETCDE = '00000110'  →  SSN belongs to a retired or deceased individual

Three Sources of Deceased Determination

Program UIMI0726 (Accelerated Refunds Daily Extract) illustrates the full three-layer deceased check, applied per-claimant :
UIMI0726.md

Input record's existing deceased indicator — if already non-zero, claimant is flagged deceased immediately
SSN Retired table lookup — if the claimant's SSN is found in UIMV_SSN_RETIRED (Table-23), claimant is flagged deceased with the stored date of death
VERIS death verification call — calls VERISB with SSN + DOB; if VERIS-SSN-RETCDE = '00000110', the claimant is confirmed deceased

If any of these three sources confirms deceased status, the Deceased Flag is set to 'Y'.
UIMI0726.md

VERIS Deceased Response Fields

When VERIS confirms deceased :
DXCC111S-cbl.json
UIMI0726.md
DXCC122S-cbl.json

VERIS-RIDDOD — Date of Death (extracted into MM, DD, CCYY components)
VERIS-RIDDOB — Date of Birth
Part 3: Where Do the Results Land?
DB2 Tables
Table

Table

	

Key Fields

	

What It Stores

	

...


UIMV_SSN_VALIDITY (Table-22)	SSN, Program Code, Date of Claim	SSN verification results: MQ completion/reason codes, SSN return code, DOB code, dependent SSN validation codes	...
UIMV_SSN_RETIRED (Table-23)	SSN, Program Code, Date of Claim	Retired/deceased SSN records: first name, last name, DOB, Date of Death, benefit payment zip, lump sum zip	...
View more
Output Records and Indicators

In batch extract programs like UIMI0726, the results are written to the output master record :
UIMI0726.md

AR-DECEASED-IND — set to 1 if deceased, 0 if not
AR-DECEASED-DATE — populated from WS-DATE-DEATH-VERIS if deceased, zeroed if not
Audit Files
VERIS Copy File (VERISCPY) — the full VERIS response record is written here for every claimant confirmed deceased, creating an audit trail
Validity File — UIMI0072 writes a comprehensive output record per re-verified SSN including all return codes, dependent validation codes, and claimant name
Batch Error Resilience

The batch VERIS interface (UIMI0726, UIMI0072) includes auto-disable logic :
UIMI0726.md

20 consecutive MQ connection errors (code 2033) → VERIS disabled for remainder of run
75 total VERIS errors of any type → VERIS disabled for remainder of run
Summary for Your Spec

SSN validation and deceased detection in LOOPS are both mediated by a single external service: VERIS (SSA verification), accessed via MQ queues. LOOPS sends SSN + DOB; VERIS returns a return code that covers both validity and deceased status ('00000110' = retired/deceased). Results land in two DB2 tables (UIMV_SSN_VALIDITY for validation details, UIMV_SSN_RETIRED for deceased/retired records), on output master record indicators (AR-DECEASED-IND, AR-DECEASED-DATE), and in a VERIS copy audit file. LOOPS does not perform SSN validation or deceased detection internally — if your replacement spec is routing the SSN check through a different upstream system and leaving deceased checks out of scope for now, be aware that in the current system the same VERIS call handles both, and downstream programs like UIMI0726 expect the UIMV_SSN_RETIRED table to be populated for their three-layer deceased check.

Would you like to dig deeper into any of these areas?

Online claim registration VERIS flow

Batch SSN re-verification (UIMI0072)

Deceased detection in Accelerated Refunds extract

Interstate SSN inquiry (INPOIQ00)

_Citations:_
- Citation 1
- Citation 2
- Citation 5
- Citation 6
- Citation 7
- Citation 4
- Citation 4
- Citation 2
- Citation 4
- Citation 8
- Citation 4
- Citation 4

## v4-Q6 (asked immediately after v4-Q5)

**Q:** When our identity-verification writeback hits a cancelled claim, LOOPS rejects it with response code 7 and a message starting "ERROR: CANCELLED CLAIM". Which LOOPS program produces that response, and is there a list of the writeback response codes?

**A** (11:13):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

Good question — and an important one to get right before your integration spec solidifies. I can identify the program, but I need to flag two discrepancies between what you described and what the source code documents.

The Program: UMOD077S

The CICS program UMOD077S handles the NIME (Non-Monetary Identity) reversal transaction — this is the MQ-based "writeback" interface that external systems use to reverse an identity block (Issue 18) on a LOOPS claim. It receives requests via MQ, processes them against the IMS claim database and the DB2 UIMT_RSA_NONMON table, and sends a reply message back via MQ.
UMOD077S-cbl.json

The cancelled-claim check is in paragraph 2211-CHECK-CLAIM: it reads the Cancellation Indicator (DB01-CANC-CLAIM) from the retrieved IMS basic claim record. If the value is '1', processing is immediately rejected with status CHECK-CLAIM-ERROR, the return message is set to 'CANCELLED CLAIM', all pending database changes are rolled back via SYNCPOINT ROLLBACK, and the error is sent back on the MQ reply queue.
UMOD077S-cbl.json

There is also a CICS screen equivalent: DXCD077S, which does the same cancelled-claim check for Identity Non-Monetary Reversal requests entered interactively. It displays error message 0201 ("Claim Has Been Cancelled") on the screen.
DXCD077S-cbl.json

Two Discrepancies to Verify

Message text: Your spec says the message starts with "ERROR: CANCELLED CLAIM". The documented return message in UMOD077S is 'CANCELLED CLAIM' — without the ERROR: prefix. Other UMOD077S error messages do use the ERROR: prefix (e.g., 'ERROR: SSN PASSED IN IS ZEROS', 'ERROR: DO NOT SEND PAYMENT ON THIS CLAIM'), but the cancelled-claim message specifically does not, per the retrieved source.
UMOD077S-cbl.json
 Either the production code adds the prefix in a layer not covered by the knowledge base, or your spec may have the prefix wrong — worth checking directly.

Response code 7: The knowledge base does not document a numeric "response code 7" for UMOD077S. The program uses text-based return messages in W03-RETURN-MESSAGE, not numeric response codes. It does set internal error classifications (DATA-ERROR, CHECK-CLAIM-ERROR, DATE-ERROR, IMS-ERROR), but these are not numeric codes exposed to the caller. If your interface documentation shows a numeric code 7, it may originate from a wrapper, middleware, or MQ message header — but that mapping is not in the held UMOD077S source.

Documented NIME Error/Return Messages

Here is the full set of return messages documented in UMOD077S, synthesized from multiple rules across the program. This is what the MQ reply carries back to the caller :
UMOD077S-cbl.json

UMOD077S NIME Return Messages

\#

	

Return Message Text

	

Condition

	

...


1	ERROR: SSN PASSED IN IS ZEROS	SSN input equals zero	...
2	CLAIM IN USE, TRY AGAIN LATER	IMS lock conflict (error code 9999) — another user/process holds the record	...
3	ERROR: PROGRAM CODES 45, 50, & 51 ARE NOT ALLOWED	Program Code is '045', '050', or '051'	...
4	CLAIM NOT FOUND ON RSA_NONMON	No active record in UIMT_RSA_NONMON for SSN + Program Code + Date of Claim (status = 0, informational — not treated as error)	...
5	ERROR: P1-STATUS-CODE=[code]:2210-GET-CLAIMANT	IMS retrieval of basic claim record failed	...
6	CANCELLED CLAIM	Cancellation Indicator (DB01-CANC-CLAIM) = '1'	...
7	ERROR: DO NOT SEND PAYMENT ON THIS CLAIM	Both LA Indicator = '1' AND Payment Trigger = 'Y' on the claim	...
8	ERROR: CURR CWE DATE < DOC	Current Week Ending date ≤ Date of Claim + 5 days	...
9	ERROR: CWE IS NOT A SATURDAY	CWE date does not fall on a Saturday	...
10	(IMS error format)	Various IMS update failures during non-monetary segment update, remarks insert, claimant update, or RSA_NONMON table update	...
View more

All error conditions (except the informational #4) trigger a SYNCPOINT ROLLBACK before the MQ reply is sent, ensuring no partial updates persist.
UMOD077S-cbl.json

What Is Not in the Knowledge Base
A numeric response code table mapping text messages to integer codes. If your upstream system is receiving code 7, that mapping lives outside the UMOD077S source — possibly in middleware, an MQ message header convention, or the calling system's translation layer.
The MQ reply queue name is environment-specific (the program selects it dynamically).
Any additional error conditions that might be produced by programs or layers outside the held code slice.

I'd recommend verifying the "response code 7" / "ERROR:" prefix directly against the MQ message layout your integration partner is using — the LOOPS side returns free-text in W03-RETURN-MESSAGE, so any numeric code would be a wrapper convention.

Want me to dig deeper into any of these?

DXCD077S screen-based reversal flow

Complete NIME validation sequence

Successful NIME reversal writeback details

_Citations:_
- Citation 1
- Citation 1
- Citation 2
- Citation 1
- Citation 1
- Citation 1

## v4-Q7

**Q:** For the Connect migration: when a weekly certification comes in through the IVR today, how does LOOPS mark the submission channel on the certification record, and how would I tell an IVR cert from a web cert in the data?

**A** (11:15):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

Great question for the Connect migration — channel identification in LOOPS is a bit more nuanced than it looks at first glance, because the channel is encoded differently depending on which layer of the system you're reading. The knowledge base documents two distinct mechanisms, plus a composite encoding on the payment record. Here's the full picture, synthesized from multiple source programs.

How LOOPS Stamps the Channel at Certification Time

When a weekly certification flows through the CICS certification processing path, the program DXCP021S receives a processing mode indicator (SPAD-Z-MODE-WS) that identifies the inbound channel :
DXCP021S-cbl.json

'W' = Web
'I' = IVR
'F' = Fax

This mode drives different initialization logic (e.g., the IVR application LOI5FUN5 restores its own screen data and skips certain defaults). However, this mode indicator is not what gets written to the certification record as a persistent channel marker.

What does get persisted are two fields on the BP88 payment certification record :
DXCP026S-cbl.json

BP88-TERMINAL-ID-CERT — set to '7777' for all automated channels (Web, IVR, and Voice)
BP88-OPERATOR-ID-CERT — set to 9000 specifically for Web certifications; IVR/Voice uses its own operator ID (not 9000)

This is set in DXCP026S (the payment-processing CICS program), which explicitly assigns Terminal ID '7777' when the channel is Voice (APL-LOGICAL-CONV-ID = 'VP1A', 'VP1B', or 'IVR '), Web (SPAD-Z-MODE-WS = 'W'), or IVR (SPAD-Z-MODE-WS = 'I').

How to Tell IVR from Web from Manual in the Data

Every downstream program in the knowledge base uses the same two-field decision tree on the certification record. Here it is, documented consistently across DXCBDA2R, DXCBD12R, DXCBD12T, UIMI0440, and UIMI0443 :
DXCBDA2R.md
DXCBDA2R.cbl.md
DXCBD12T.md
DXCBD12R.md
UIMI0443.md
UIMI0440.md

Weekly Certification Channel Classification Rules

Channel

	

Terminal ID (

	

BP88-TERMINAL-ID-CERT

	

...


WEB (online self-service)	'7777'	= 9000	...
PHONE / IVR (telephone)	'7777'	≠ 9000	...
Manual / P100 (staff-assisted)	≠ '7777'	(any)	...
View more

The key takeaway: Terminal ID '7777' is shared by both Web and IVR — it just means "not a physical terminal." The Operator ID is the differentiator: 9000 = Web, anything else with '7777' = IVR/Phone.

UIMI0440 encodes this into a single phone-indicator field (F70-PHONE-IND) :
UIMI0440.md

'2' = Operator ID 9000 + Terminal ID 7777 (Web / SIM 926 automated)
'1' = Terminal ID 7777, Operator ID ≠ 9000 (Phone / IVR)
'0' = Terminal ID ≠ 7777 (In-person / manual)
The Badge Indicator — A Second Encoding on Payment Records

After payment processing, the Badge Indicator (SG02-BADGE-IND) on the IMS payment segment encodes both the certification method and the payment delivery method in a single composite digit, documented in NAVAPMTS :
NAVAPMTS-cbl.json

Badge Indicator Encoding (Dual-Purpose)

Badge Indicator

	

Certification Method

	

Payment Method


0	MANUAL	CHECK
1	IVR	CHECK
2	WEB	CHECK
3	MANUAL	DIRECT DEPOSIT
4	IVR	DIRECT DEPOSIT
5	WEB	DIRECT DEPOSIT
6	MANUAL	DEBIT CARD
7	IVR	DEBIT CARD
View more

So if you're querying payment history (e.g., through the NAVAPMTS inquiry program), the Badge Indicator is the field to use. If you're reading raw certification records from the PAYVSAM or NOPAY files (as DXCBDA2R does), it's the Terminal ID + Operator ID pair.

What This Means for the Connect Migration

For your Connect integration, the critical implication is:

IVR certifications today are distinguished from Web solely by Operator ID — the IVR system does not use Operator ID 9000. If Connect replaces the IVR and your new channel also stamps 9000, every downstream reporting program (DXCBDA2R, DXCBD12R, DXCBD12T, UIMI0440, UIMI0443) will classify those certs as Web, not Phone. You'll need to either assign a distinct Operator ID to Connect-originated certs, or update the downstream classification logic.

Check series is also channel-dependent — DXCP026S assigns check series 10 for IVR/Voice and 11 for Web.
DXCP026S-cbl.json
 If Connect enters through the Web path, it gets series 11 instead of 10.

The Badge Indicator combines certification channel with payment delivery method. If Connect certifications flow through the Web processing mode, they'll get badge values 2/5 (WEB + CHECK/DIRECT DEPOSIT) rather than 1/4/7 (IVR). This affects any system reading payment history.

What Is Not in the Knowledge Base
The specific Operator ID that the current IVR system assigns — the docs say "not 9000" but don't name the value. This would be in the IVR middleware configuration or the LOI5FUN5 / LOI7FUN7 transaction setup.
Whether there are additional downstream consumers of Terminal ID / Operator ID / Badge Indicator outside the held code slice.
What would you like to explore next?

Map the IVR certification processing flow end-to-end

Search for the IVR-specific Operator ID value

Assess downstream impact if Connect uses Operator ID 9000

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 5
- Citation 6
- Citation 7
- Citation 8
- Citation 8
- Citation 9
- Citation 2

## v4-Q8

**Q:** The MUNC replication spec shows each municipality row carries a local_office_id. On the LOOPS side, how are local offices represented and used in claims processing, and is the municipality-to-local-office assignment documented there?

**A** (11:17):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

This is a rich topic — the knowledge base documents local offices from multiple angles: the claim record, CICS authorization, batch classification, and the municipality relationship tables. Let me synthesize everything.

Local Office on the Claim Record

The primary representation is the field DB01-LOCAL-OFF on the IMS basic claim segment (DB01 / LOOPLE01). This is the local unemployment office that "owns" the claim. It is set at claim registration time and persists on the record. A large number of programs read it :
LO99SBLD-cbl.json
DXCC072S-cbl.json
MACROLST-cbl.json
DXCR032S-cbl.json
LOAASBLD-cbl.json
LOH3C015-cbl.json
LOFQSBLD-cbl.json
SARN114S-cbl.json
LOV1C326-cbl.json
UIMI0031.md

LO99SBLD — extracts it into T176-LOCAL-OFFICE and SPLIT-LO for numeric/range validation during certification eligibility
LOAASBLD — copies it into APL-LOCAL-OFFICE and TXT-LOCAL-OFFICE-NUMBER for routing, remarks, and adjudication
LOFQSBLD — passes it through to the web inquiry response buffer (W03-LOCAL-OFFICE-CODE)
MACROLST, LOH3C015 — writes it to the DB2 UIMV_CLAIMANT table's CDE_LOCAL_OFFICE field, so the office that originally filed the claim is permanently recorded
UIMI0031 — stamps it onto payment records as both PR02-LOCAL-OFF-CUR and PR02-RESP-LOCAL-OFF-CUR
DXCR032S — carries it forward onto refund segments (SF08-REFUND-SCRN-LOCAL-OFF) and CAPS records (CAPS-LOCAL-OFFICE)

There is also a second local-office field on journal/segment records: Responsible Local Office (RESP-LOCAL-OFF-CUR / RESPLO). At claim registration (SARN114S), the segment prefix gets both :
SARN114S-cbl.json

Local Office ← from DB01-LOCAL-OFF (the originating office on the claim)
Responsible Local Office ← from APL-LOCAL-OFFICE (the processing terminal's office)

These can differ when a centralized unit or special office processes a claim belonging to another office.

How Local Office Is Used in Claims Processing
1. CICS Terminal Authorization (Access Control)

Multiple CICS programs enforce the rule that a terminal can only process claims from its own local office — unless it's an authorized special unit :
DXCC072S-cbl.json
LOV1C326-cbl.json

DXCC072S, LOV1C326: Compare APL-LOCAL-OFFICE (terminal) against DB01-LOCAL-OFF (claimant). Match → access granted. Mismatch → check special unit authorization table (via LOCAL-OFFICE-CHECK). If not authorized → access denied with error.
2. Batch Claim Type Classification

The Responsible Local Office (RESPLO) — not the local office per se — drives claim type classification in the batch journal extract programs (DXCBW30E, DXCBW39E, DXCBW39U, DXCBW30U). The hierarchy is :
DXCBW30E.md
DXCBW39E.md
DXCBW39U.md
DXCBW38R.md
DXCBW30U.md

Claim Type Classification By RESPLO And Municipality

Priority

	

Condition

	

Claim Type (STTYPE)

	

...


1	Program Code = 11 or 12	4	...
2	RESPLO = 999 or 997	3	...
3	Municipality 05500–07599	1	...
4	All other	2	...
View more

For Type 3 claims (RESPLO 999/997), the municipality code is range-validated: if between 01001–76999 it's used as-is; otherwise it defaults to 77777.
DXCBW30E.md
DXCBW39E.md

3. Local Office Validation Against Reference Tables

DXCC121S (Claimant Maintenance) validates the Employment Service Office code against Table 112 (Local Offices) in the CODELOOP VSAM file. If the office code is not found, error 474 is raised.
DXCC121S-cbl.json
 Special rules apply for certain program codes (e.g., Program Code 84 must use ESO = 998).
DXCC121S-cbl.json

The Municipality-to-Local-Office Assignment

This is directly documented — and it's the heart of what your MUNC replication spec is reflecting. The knowledge base shows two data stores that carry the municipality→local-office mapping, plus a maintenance application:

Primary: WDPV_E_FIPS_DESCRP (DB2 Table)

DXCC121S and LOH3C015 document how NJ address processing works :
LOH3C015-cbl.json
DXCC121S-cbl.json

For NJ addresses, the system queries WDPV_E_FIPS_DESCRP by city name (DES_FIPS_REGION) AND local office (CDE_LOCAL_OFFICE)
A matching row returns: CDE_MUNICIPAL (municipality code), IDN_FIPS_CITY, IDN_FIPS_COUNTY, IDN_FIPS_STATE
If exactly one match → municipality and FIPS codes are auto-assigned
If multiple matches for the same city + local office → the system refines by adding CDE_MUNICIPAL to the query
If the city is found but the local office doesn't match → a city/local-office mismatch error is displayed, and the user is directed to screen C015 to manually enter the municipality code
If duplicate city + local office → error 1505 (ambiguity)
Secondary: MUNICIPA VSAM File

When the DB2 FIPS search fails, DXCC121S falls back to a browse of the MUNICIPA VSAM file by city name, then compares local office. Each record in this file also carries a local office field.
DXCC121S-cbl.json

Maintenance Application: DXAMUNCP / DXAMUNC2 (MUNC Transaction)

The CICS municipality maintenance screens (MSTMUNC1 through MSTMUNC4) are documented in DXAMUNCP and DXAMUNC2. The detail screen (MSTMUNC4) shows the full municipality record layout :
DXAMUNC2-cbl.html
DXAMUNCP-cbl.json

CITY, MUNICIPAL CODE, STATE, TAX MUNICIPAL, COUNTY, LOCAL OFFICE, LOCAL NAME, HEALTH MUNICIPAL, CORPORATE, WIB, COUNTY

So each municipality row does carry a local office, exactly as your MUNC replication spec shows. The CDE_LOCAL_OFFICE in the DB2 table (WDPV_E_FIPS_DESCRP) and the local-office field in the MUNICIPA VSAM file are the authoritative sources for this assignment.

Out-of-State / Out-of-Region Handling

For addresses outside NJ :
DXCC121S-cbl.json

DE, NY, PA → searched in WDPV_E_FIPS_DESCRP by city + state FIPS code (no local office in the key)
All other states → assigned default municipality code 09400, all FIPS codes zeroed
What's Not in the Knowledge Base
Who maintains the WDPV_E_FIPS_DESCRP rows and the MUNICIPA VSAM file — the maintenance screens are documented, but the operational process for when/why rows are added or local-office assignments change is not in the held code slice.
The complete list of valid local office codes — Table 112 defines the valid set, but it lives in the CODELOOP VSAM dataset, whose populated values are operations-maintained and outside the knowledge base.
Whether RESPLO and DB01-LOCAL-OFF can diverge on an existing claim over its lifetime (e.g., through office reassignment) — the registration logic sets them independently, but whether any downstream transaction can update DB01-LOCAL-OFF post-creation would require checking additional CICS update programs beyond the held set.
Would you like to go deeper on any of these areas?

Municipality FIPS lookup details

Claim type classification deep dive

MUNC transaction / maintenance screens

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
- Citation 8
- Citation 2
- Citation 9
- Citation 11
- Citation 12
- Citation 13
- Citation 14
- Citation 15
- Citation 11
- Citation 12
- Citation 16
- Citation 16
- Citation 6
- Citation 16
- Citation 16
- Citation 17
- Citation 18
- Citation 16
