# 2026-09-01_1321_quick_playwright_v4

- **Backend:** quick (transport: playwright)
- **Bank:** v4 (`question_sha256` 5da69eeb3130…)
- **Agent:** engineering_onboarding_specialist (`093ac4e3-0712-481e-af95-9ddc5e4fc734`)
- **Conversation:** `62e1b60f-ab00-488d-8718-15cb96de88eb`
- **Model:** Advanced
- **Started:** 2026-09-01 13:10
- **Finished:** 2026-09-01 13:21
- **Status:** complete
- **Questions asked:** 8, answered: 8

## v4-Q1

**Q:** Our new-hire crossmatch spec says the replacement system's SG01 pipeline can only pull data forward based on DB2 RSA_NONMON entries. What do the SG01 and RSA_NONMON DB2 tables contain in LOOPS, and which batch jobs read or write them?

**A** (13:11):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

Good question — these are two distinct DB2 tables in LOOPS, and it's important to clarify that the knowledge base does not document a process named "new-hire crossmatch" that ties them together. Your replacement-system spec may be referencing a design that sits outside the documented LOOPS batch flows. Here's what the knowledge base does document about each table and the jobs that touch them.

OTDUIMP.UIMT_RSA_NONMON — RSA Non-Monetary Transactions

This table stores Reemployment Services and Eligibility Assessment (RSA) non-monetary UI claim records. The documented columns (nine fields extracted by L2UDB020) are :
L2UDB020.md
L2UDB020.md

IDN_SSN — Claimant Social Security Number
TMS_RECORD_LOAD — Record Load Timestamp
CDE_PROGRAM_UIB — UI Benefit Program Code
DTE_CLAIM_UIB — UI Benefit Claim Date
IDN_HIST — Historical Record Identifier
DTE_PROOFING — Proofing Date
IDN_LOGON_ID — Processing user's Logon ID
IDN_USERNAME — Processing user's Username
TMS_RECORD_UPDT — Record Last Update Timestamp

Batch jobs documented against this table:

L2UDB020 (READ) — Extracts the entire table (no filters, WITH UR) into a tilde-delimited CSV (LAK2LDXP.L2UDB020.NONMON.CSV), then sorts by SSN into LAK2LDXP.L2UDB020.NONMON.SORTED.CSV (122-byte fixed records).
L2UDB020.md
L2UDB020.txt
L2FTPRS2 (downstream) — FTPs the sorted CSV file to a Labor server. The JCL explicitly notes the CSV "IS FLAT FILE COPY OF DB2 TABLE UIMT_RSA_NONMON".
L2FTPRS2.txt
L2FTPRS2.txt

Note — write side: The knowledge base does not document which job or program writes to UIMT_RSA_NONMON. There is a separate but similarly named table, OTDUIMP.UIMT_NONMON_DATA, which is populated by CICS subprogram UIMI0466 (and its batch counterpart UIMB0466) with nonmonetary determination details (examiner number, issue code, determination date, redetermination, etc.).
UIMI0466.md
UIMB0466.md
 These are two different tables — confirm with an SME which one your spec intends as the source-of-truth for the replacement pipeline.

OTDUIMP.UIMT_SG01_CLAIMANT — Core Claimant and Claim Data

This table holds core claimant identity and claim-level data. The documented columns (from COBOL source and JCL) include :
src_cob_ABENDBP-W...
bre_cob_2_UIMB014...

SG01_IDN_SSN — Claimant SSN
SG01_CDE_PROGRAM_UIB — UI Benefit Program Code
SG01_DTE_CLAIM_UIB — UI Benefit Claim Date
SG01_INVALID_CLAIM — Invalid Claim indicator

The flow diagram in L2PUA003.md labels it "Core Claimant and Claim Data" and shows it alongside three other DB2 tables (UIMT_SG11_NONMON, UIMT_SG02_PAYMENT, UIMT_IDENTITY_THEFT_SSN).
L2PUA003.md

Batch jobs documented against this table:

L2PUA003 (READ) — PUA (Pandemic Unemployment Assistance) Fraud Data Extract. Reads UIMT_SG01_CLAIMANT (plus UIMT_SG11_NONMON, UIMT_SG02_PAYMENT, and UIMT_IDENTITY_THEFT_SSN), unloads fraud candidate records, reformats them, and FTPs them to the claims server.
L2PUA003.md
L2PUA003.txt
L2PUA003.txt
COBOL program in ABENDBP-WS1750R.txt (READ) — Opens a cursor (TABLE_007) against UIMT_SG01_CLAIMANT and fetches SSN, program code, claim date, and invalid-claim flag.
src_cob_ABENDBP-W...
bre_cob_2_UIMB014...

Note — write side: The knowledge base does not document which batch job or online program inserts/updates rows in UIMT_SG01_CLAIMANT.

Important Distinction: DB2 Table vs. File-Based SG01 Pipeline

The knowledge base also documents an extensive file-based "SG01" processing pipeline inside the Payroll Reissuance job D2PAD168 (and its counterpart D2PAD139). That pipeline works with 659-byte flat-file SG01 segment records derived from document conversion — involving steps like SG01FLDS, TDCBD17L, SORT22, and dozens of SG01 offset split/merge passes.
D2PAD168.md
 This is not the same as the DB2 table UIMT_SG01_CLAIMANT. The file-based pipeline processes payment reissuance offsets; the DB2 table stores claimant claim-level identity data. Your spec's "SG01 pipeline" should be verified against the replacement-system design docs to determine which one it means.

Summary
DB2 Tables And Batch Job Summary

DB2 Table

	

Purpose

	

Documented Read Jobs

	

...


OTDUIMP.UIMT_RSA_NONMON	RSA non-monetary UI claim transactions	L2UDB020 (extract→CSV); L2FTPRS2 (FTP downstream)	...
OTDUIMP.UIMT_SG01_CLAIMANT	Core claimant identity and claim data	L2PUA003 (PUA fraud extract); COBOL ABENDBP/WS1750R cursor read	...
View more

Bottom line: In the documented LOOPS batch flows, these two tables are not connected by any single crossmatch job. The New Hire crossmatch jobs (ZLPDN1R0–ZLPDN1R9) read IMS databases (LOPD/LOPX), not these DB2 tables. If your replacement-system spec links UIMT_RSA_NONMON entries to an "SG01 pipeline," that linkage is either in an undocumented upstream process or is a new design in the replacement system — I'd recommend confirming with the crossmatch SME which LOOPS process currently provides the join between these datasets.

Would you like to explore further?

RSA_NONMON extract pipeline details

SG01_CLAIMANT fraud extract details

D2PAD168 SG01 reissuance pipeline

New Hire crossmatch IMS-based jobs

_Citations:_
- Citation 1
- Citation 2
- Citation 1
- Citation 3
- Citation 4
- Citation 5
- Citation 6
- Citation 7
- Citation 8
- Citation 9
- Citation 10
- Citation 10
- Citation 11
- Citation 12
- Citation 8
- Citation 9
- Citation 13

## v4-Q2

**Q:** How does LOOPS process the daily new hire file today? Walk me through the batch jobs and programs, and what they produce.

**A** (13:13):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

This is a great question for onboarding — the daily new-hire pipeline is one of the larger documented batch flows in LOOPS, spanning multiple jobs across file acquisition, deduplication, DB2 load, parallel splitting, crossmatching, IMS updates, and refund reporting. Here's the end-to-end walkthrough, synthesized from multiple source documents across the Daily CA-7 and NewHire knowledge spaces.

The New Hire Input Record

Before diving into the jobs, the input file uses the NEWHIRE copybook layout — 320-byte fixed-length records containing :
NEWHIRE.txt
NEWHIRE.txt

NH-SSN (9 digits) — Claimant/Employee Social Security Number
NH-LAST-NAME, NH-FIRST-NAME, NH-MIDDLE-INIT — Name fields
Employee address (line 1, line 2, city, state, ZIP, ZIP+4, foreign country code/ZIP)
NH-DATE-HIRE (8 digits), NH-DATE-BIRTH (8 digits), NH-GENDER
Employer name, address, state, ZIP, NH-EMPLR-FEIN (9 digits)
44 bytes of filler
Phase 1 — File Acquisition & Deduplication: L2NHD011

This is the entry point. The file SENDTOUIB.TXT arrives daily from DOL on the MoveIt server.
L2NHD011.md
L2NHD011.md

L2NHD011 — File Acquisition And Deduplication Steps

Step

	

Utility / Program

	

What It Does


PREPARE1	IEFBR14	Deletes leftover sort work file and MoveIt control file from prior run
TRANS01	EZACFSM1	Downloads SENDTOUIB.TXT from /HOME/DOL/LOOPS/INBOUND via MoveIt; archives a timestamped copy to /HOME/DOL/LOOPS/ARCHIVE; deletes the source file from inbound
TRANS02	FTP	Executes the MoveIt secure-transfer commands using stored credentials
SORTCOPY	SORT (FIELDS=COPY)	Archives the raw downloaded file into a new GDG generation KIPPS001.ZUMDNHU1.DTL(+1) — 320-byte FB records, no transformation
PREPARE2	IEFBR14	Deletes the temporary KIPS1 working copy
SORTCPY2	SORT (FIELDS=COPY)	Refreshes KIPS1 working area from KIPS2 staging source
SORTHIRE	SORT	Sorts the new GDG generation by SSN (positions 1–9, ascending, zoned decimal) → NEWHIRE.SORT.DTL
DXNHCM29	DXNHCM29	Reads the sorted file; detects duplicate SSNs using date-sensitive rules from DATECARD; produces two GDG outputs: unique records (NEWHIRE.OUT.DTL(+1)) and duplicates (NEWHIRE.DUP.DTL(+1)) plus an error report
View more

Key output: LAK2LDXP.L2NHD011.NEWHIRE.OUT.DTL(+1) — the deduplicated new-hire file that feeds all downstream jobs.
L2NHD011.md
L2NHD011.md

Phase 2 — DB2 Load: ZUMDNHU1

This job loads the deduplicated records into the DB2 table UIMT_NEWHire.
ZUMDNHU1.md
ZUMDNHU1.md

ZUMDNHU1 — DB2 Load Steps

Step

	

Program

	

What It Does


DBLOAD	UIMI0134 (DB2 plan UIMI0134)	Reads the current generation of NEWHIRE.OUT.DTL; validates each record (DOB, hire date, SSN, FEIN, ZIP, state code — including leap-year and future-date checks); inserts valid records into UIMT_NEWHire with a current timestamp (TMS_RECORD_LOAD); logs errors
PURGEDSN	IDCAMS	Conditionally purges the KIPPS FTP interface detail file after a successful load
View more

Program UIMI0134 validates six fields per record: Date of Birth, Date of Hire, SSN (numeric), Employer FEIN (numeric), Employee ZIP (numeric), and Employee State (against a predefined list including territories). A foreign country code overrides an invalid state. Only records passing all six checks are inserted.
UIMI0134.md

Phase 3 — Parallel Split Preparation: L2NHD001

This job prepares both the New Hire records and a consolidated Pay/No-Pay file, then splits each into 10 SSN-range partitions for parallel downstream processing.
L2NHD001.md

L2NHD001 — Parallel Split Steps

Step

	

Utility / Program

	

What It Does


PREPARE1	IEFBR14	Deletes 23 prior-run work files (sorted NH, sorted PNP, 10 NH splits, 10 PNP splits, combined PNP)
DXNHCM04	DXNHCM04	Merges four account-type files (Pay, No-Pay, T4F, TRA) into one unified PAYNOPAY.DTL (80-byte records)
SORTPNP	SORT	Sorts the merged Pay/No-Pay file by account ID (pos 1–9 ascending), then date/sequence (pos 32–39 descending)
SORTHIRE	SORT	Sorts the L2NHD011 output (NEWHIRE.OUT.DTL) by account ID (pos 1–9 ascending) → SORT.NEWHIRE.DTL
SPLITNH	SORT	Splits the sorted New Hire file into 10 partitions (NEWHIRE.SPLIT01.DTL – SPLIT10.DTL) by SSN ranges
SPLITPNP	SORT	Splits the sorted Pay/No-Pay file into the same 10 SSN-range partitions (PAYNOPAY.SPLIT01.DTL – SPLIT10.DTL)
View more

The 10 SSN ranges used for splitting are consistent across all split/match jobs :
L2NHD001.md
L2NHD001.md

SSN Range Partition Boundaries

Split

	

SSN Range


01	000000000 – 115502000
02	115502001 – 137444750
03	137444751 – 141302200
04	141302201 – 144540100
05	144540101 – 148361300
06	148361301 – 152052200
07	152052201 – 155405800
08	155405801 – 163187500
09	163187501 – 249743000
10	249743001 and above
View more
Phase 4 — Parallel Pay/No-Pay Crossmatch: ZULDNHR0–ZULDNHR9

These 10 jobs run in parallel — one per SSN split. Each matches Pay/No-Pay records against New Hire records using IMS.
05_job_purpose_in...
ZULDNHR1.md
ZULDNHR1.md
ZULDNHR7.md

Each job (ZULDNHRn) does:

PREPARE — Deletes the prior CMATCH.SPLITnn.DTL output file
Matching — Runs DSNMTV01 with PSB LOPGMPnn, reading PAYNOPAY.SPLITnn.DTL + NEWHIRE.SPLITnn.DTL, accessing IMS databases LOPDnnnn and LOPXnnnn
Output — Produces a combined match file CMATCH.SPLITnn.DTL (479-byte FB records)
Phase 5 — Parallel IMS Update: ZULDNHU0–ZULDNHU9

These 10 jobs consume the match output from Phase 4. Each runs DSNMTV01 to process matched new-hire records against IMS databases and VSAM reference files (code tables, employee address).
05_job_purpose_in...

Each job produces:

BPC output files (BPC174 – BPC179) — Benefit Plan Carrier transaction files
Batch journal (BTCHJRL4)
Output records and reports for downstream processing
Phase 6 — IMS New Hire Refund Crossmatch: ZLPDN1R0–ZLPDN1R9

These 10 jobs run a separate crossmatch path directly from the deduplicated New Hire file against IMS claim data. Each is described in JCL as "NEW HIRE CROSS REF MATCH WITH CURRENT FILE AND OFFSET > ZERO".
05_job_purpose_in...
05_job_purpose_in...
ZLPDN1R1.txt
ZLPDN1R0.txt
ZLPDN1R0.md
ZLPDN1R0.md
ZLPDN1R1.md

Each job (ZLPDN1Rn) does:

SCRATCH — Deletes prior-run sort and refund work files
SRTHIRE — Sorts the current generation of NEWHIRE.OUT.DTL, filtering to the job's SSN range, ascending by SSN
DXNHCM02 — IMS DL/I batch program that reads sorted new-hire records, looks up claimant data in IMS databases (LOPDnnnn / LOPXnnnn) using DATECARD, and produces a New Hire Refund Detail file (NHREFUND.DTL, 170-byte FB records) for qualifying participants
Phase 7 — Refund Reporting: DXCBNHR1 (downstream)

Program DXCBNHR1 reads the refund detail output and produces two printed reports split by refund balance threshold :
DXCBNHR1.md

Over $2,000 Report — Refund balance ≥ $2,000.00
Under $2,000 Report — Refund balance > $0 and < $2,000.00

Each report includes: SSN, employee name, address, employer FEIN, hire date, claim date, bad-address indicator, and refund balance.

End-to-End Flow Summary
DOL MoveIt Server
        │
        ▼
  ┌─ L2NHD011 ─────────────────────────┐
  │  FTP download → Archive → GDG      │
  │  Sort by SSN → DXNHCM29 dedup      │
  │  Output: NEWHIRE.OUT.DTL(+1)        │
  └───────┬────────────────┬────────────┘
          │                │
          ▼                ▼
    ZUMDNHU1            L2NHD001
    UIMI0134 →          Merge Pay/NoPay/T4F/TRA
    DB2 UIMT_NEWHire    Sort both → Split both ×10
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
           ZULDNHR0–9            ZLPDN1R0–9
           Match PNP vs NH       Sort NH per range
           → CMATCH files        DXNHCM02 vs IMS
                    │                   │
                    ▼                   ▼
           ZULDNHU0–9            DXCBNHR1
           IMS update            Refund reports
           BPC174–179            (≥$2K / <$2K)

Important Caveats
This is a synthesis built from the documented jobs listed above. The CA-7 schedule may include additional predecessor/successor jobs not detailed in the knowledge base (e.g., the upstream source of the KIPS2 file, or downstream consumers of the BPC files).
The write side of the UIMT_NEWHire DB2 table is now clear: it's program UIMI0134 in job ZUMDNHU1.
ZUMDNHU1.md
UIMI0134.md
The knowledge base does not document which job concatenates or merges the 10 ZLPDN1Rn refund files before feeding them to DXCBNHR1, or whether DXCBNHR1 reads them individually.
What would you like to explore next?

New Hire crossmatch program internals

Pay/No-Pay consolidation details

DB2 load validation rules

Job scheduling and dependencies

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 3
- Citation 4
- Citation 5
- Citation 6
- Citation 7
- Citation 8
- Citation 8
- Citation 9
- Citation 10
- Citation 11
- Citation 12
- Citation 13
- Citation 10
- Citation 10
- Citation 14
- Citation 15
- Citation 16
- Citation 17
- Citation 18
- Citation 19
- Citation 21
- Citation 6
- Citation 7

## v4-Q3

**Q:** When a new-hire crossmatch hit comes in, under what conditions does LOOPS update the claimant's return-to-work date, and where is that date stored?

**A** (13:14):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

This is a very detailed question, and the documented source code provides a thorough answer. The RTW update logic lives in program UIMB0147 (referenced in the knowledge base as both UIMB0147.cbl.md and UIMI0147.cbl.md), specifically in procedure 2300-UPDTE-RTW-DB01, which runs within the ZULDNHU0–ZULDNHU9 IMS update jobs. Here's the full decision tree, synthesized from both source documents.

Where the Return-to-Work Date Is Stored

The return-to-work date is stored in field DB01-DATE-RETURN-WORK on the Claim Basic segment (DB01) of the IMS LOOPDB01 database. The hire date is converted from its input YYYYMMDD format to the internal "F6" packed date format before being written there.
UIMI0147.md
UIMB0147.md

Important Scope Note — Non-TRA Claims Only

The RTW date update logic in 2300-UPDTE-RTW-DB01 applies only to non-TRA (non-T3) source records. For TRA claimants (source code T3), the entire RTW date update path is skipped; the program routes directly to the DB2 remarks insertion (3100-INSERT-T3-REMARK) into TNPV_CLAIM_REMARKS without touching DB01-DATE-RETURN-WORK.

The Decision Tree (Procedure 2300-UPDTE-RTW-DB01)

The following decision flow is documented in UIMB0147 / UIMI0147 and governs whether the hire date gets written as the RTW date :
UIMI0147.md
UIMB0147.md

Step 1 — Does an RTW date already exist?
Check: Is DB01-DATE-RETURN-WORK non-zero?
If YES → Skip entirely. No update, no remark. The existing RTW date is preserved.
UIMI0147.md
Step 2 — Read Additional Claim (DB10) segments

If no RTW date exists, the program reads all Segment 10 (Additional Claim) child segments under the claimant's claim in IMS using a GNP (Get-Next-within-Parent) loop. For each segment it captures:

Whether any DB10 segment was found (FOUND-10-SW)
Whether a valid Date of Additional Claim exists — determined by checking whether DB10-FILLER-CHK-10 is spaces (DOA-FOUND-SW)
The actual date (WS-DATE-ADD-CLAIM) and separation code (WS-DB10-SEP-CODE-ADD)
Step 3 — Evaluate what was found
RTW Update Decision Logic For Non-TRA Claims

Condition

	

Action

	

Report/Remark


RTW already non-zero (DB01-DATE-RETURN-WORK > 0)	Skip — no change to claim	None
No DB10 segments found (FOUND-10-SW = 'N')	Set DB01-DATE-RETURN-WORK = Hire Date	No exception report
DB10 found, but no valid Date of Additional Claim (DOA-FOUND-SW = 'N')	Set DB01-DATE-RETURN-WORK = Hire Date	No exception report
Valid Additional Claim Date found, but saved Hire Date = 0	Re-establish parent; do NOT set RTW	None
Additional Claim Date ≤ Hire Date (hire is on or after the additional claim)	Set DB01-DATE-RETURN-WORK = Hire Date	No exception report
Additional Claim Date > Hire Date (additional claim is more recent than hire)	Do NOT update RTW date	Write RTW-Not-Updated report entry + insert 'NH RTW NOT UPDATED' remark on claim (IMS DB16 segment)
View more
When the RTW Date IS Updated

The hire date is written as the RTW date when all of these are true:

No RTW date already exists on the claim (DB01-DATE-RETURN-WORK = 0)
Source is not T3 (TRA claims are excluded)
One of the "safe" additional-claim conditions holds:
No Additional Claim segment (DB10) exists at all, OR
DB10 segments exist but none contain a valid Date of Additional Claim, OR
A valid Additional Claim Date exists but it is on or before the Date of Hire
The saved Hire Date is non-zero (a valid date was received from the new-hire file)

When these conditions are met, the program converts HM-DATE-HIRE from YYYYMMDD to internal F6 format and stores it in DB01-DATE-RETURN-WORK, then issues a REPL call to persist the updated claim basic segment in IMS.
UIMI0147.md

When the RTW Date Is NOT Updated (and What Happens Instead)

The RTW date is suppressed when the Date of Additional Claim is strictly later than the Date of Hire (WS-DATE-ADD-CLAIM > DATE-SAVE). In this case:

The RPT-RTW-SW flag is set to 'Y'
The ZERO-SW is set to 'Y' to prevent any downstream zeroing of the RTW field
An RTW-Not-Updated report entry is written (paragraph 3060-RTW-RPT-NH) containing: SSN, program code, DOC, employer FEIN, hire date, first benefit week begin date, employer name, additional claim date, and separation code
A special IMS remark (DB16 segment) is inserted on the claim with title 'NH RTW NOT UPDATED' and text:

NEW HIRE DATE OF HIRE: [MM/DD/YYYY] WITH [FEIN] [EMPLOYER NAME] NOT UPDATED TO CLAIM BASIC SINCE ADDITIONAL DATED [MM/DD/YYYY]

The business rationale is to prevent recording a return-to-work date that predates a subsequent claim filing, which would be contradictory.
UIMI0147.md
UIMB0147.md

Summary Flow
Crossmatch hit arrives (from ZULDNHU0–9 jobs, program UIMB0147)
                │
         Source = T3?
        ┌───YES──┐
        │        ▼
        │   Skip RTW update entirely
        │   → Route to DB2 TRA remarks
        │
        └───NO───┐
                 ▼
    DB01-DATE-RETURN-WORK > 0?
        ┌───YES──→ Skip (RTW already set)
        └───NO───┐
                 ▼
    Read all DB10 (Additional Claim) segments
                 │
    ┌── No DB10 found ──────────→ Set RTW = Hire Date ✓
    │
    ├── DB10 found, no valid DOA → Set RTW = Hire Date ✓
    │
    ├── Valid DOA found, Hire=0 ─→ Skip (no valid date)
    │
    ├── DOA ≤ Hire Date ─────────→ Set RTW = Hire Date ✓
    │
    └── DOA > Hire Date ─────────→ SUPPRESS RTW update
                                   Write report + insert
                                   'NH RTW NOT UPDATED' remark

Important Caveats
This describes the documented logic in UIMB0147/UIMI0147 from the held knowledge base. Other programs or CICS screens may also read or write DB01-DATE-RETURN-WORK, but those are outside the scope of the new-hire crossmatch flow documented here.
The "F6 format" conversion for the hire date into DB01-DATE-RETURN-WORK is documented but the exact byte layout of F6 is not detailed in the retrieved source — it is described as an "internal date format" conversion. An SME or the date-conversion subroutine source would confirm the packed representation.
What would you like to explore next?

When do the claimant/employer letters get generated?

Walk me through the standard crossmatch remark insertion

How does the TRA/T3 path differ?

_Citations:_
- Citation 1
- Citation 2
- Citation 1
- Citation 2
- Citation 1
- Citation 1
- Citation 1
- Citation 2

## v4-Q4

**Q:** The pension spec replaces the manual process where staff compute pension reductions in Excel and key them into LOOPS. How does LOOPS apply a pension reduction when paying a weekly benefit, and does LOOPS itself compute the weekly reduction amount from the pension details (for example, prorating a lump sum)?

**A** (13:16):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

This is an excellent question that gets at a fundamental architecture boundary in LOOPS. The retrieved source code tells a clear story, and the answer to your second question — does LOOPS compute the weekly pension reduction? — is particularly important for any replacement spec.

How LOOPS Applies a Pension Reduction at Payment Time

At the point a weekly benefit is being paid, the pension reduction is applied through a single, universal formula called the AWBA (Adjusted Weekly Benefit Amount) calculation. This formula appears identically across every payment-processing and reporting program in the held knowledge base:

AWBA = WBA-PAY  minus  PENSION-AMT


This is documented consistently in UIMB0440.md, UIMB0443.md, BALANCE.md, DXCBD10R.md, DXCBD06E.md, and DXCBD83R.md
DXCBD10R.md
BALANCE.md
DXCBD06E.md
DXCBD83R.md
.

Where the Pension Amount Lives on a Payment Record

Each payment record (the BP88-format VSAM record for pay transactions, or the NOPAYIN-format record for no-pay transactions) carries two pre-populated per-week pension fields:

BP88-PENSION-AMOUNT1 — pension deduction for Certification Week Ending period 1
BP88-PENSION-AMOUNT2 — pension deduction for Certification Week Ending period 2

These fields are already filled in when the payment record reaches the check-printing and reporting programs. Every downstream program simply reads them.
UIMB0443.md
UIMB0440.md
DXCBD30R.txt

The AWBA Zero-Floor Rule

After computing AWBA = WBA minus PENSION-AMT, a validation rule applies:

If AWBA < 0 and Program Code ≠ 45 → AWBA is floored at zero (no negative benefit is allowed)
If AWBA < 0 and Program Code = 45 (CWC — Combined Wage Claim Transfer) → the negative value is retained as-is. This is a documented policy exception
Check Stub and Report Display

At check-printing time (programs UIMB0440, UIMB0441, UIMB0442, UIMB0443), the total pension deduction shown on the check stub is simply:

Total Pension Deduction = BP88-PENSION-AMOUNT1 + BP88-PENSION-AMOUNT2


This summed value is placed in fields F24-PENSION and F59-PENSION on the check stub.
UIMB0443.md
UIMB0440.md
UIMB0441.md

Special Case: Pension Offset Segments

Program DXCBD40E documents a special "pension offset segment" identified by CHECK-PART2 = 0099999999. If such a segment has a zero benefit amount (AMT-BEN-PAID = 0), it is completely excluded from all downstream processing — no sort key, no check register, no bank record, no reports.
DXCBD40E.md

The Critical Answer: LOOPS Does NOT Compute the Weekly Reduction

In the documented programs, LOOPS never computes a weekly pension reduction from raw pension details. There is:

❌ No lump-sum proration logic
❌ No conversion from gross monthly/annual pension to a weekly offset
❌ No employer-contribution-percentage calculation
❌ No pension-type routing (periodic vs. lump sum vs. rollover)

Every program that touches pension at payment time — UIMB0440, UIMB0443, BALANCE, DXCBD10R, DXCBD06E, DXCBD83R — receives PENSION-AMT (or BP88-PENSION-AMOUNT1/2) as a pre-computed dollar amount and simply subtracts it from WBA-PAY.
DXCBD10R.md
BALANCE.md
DXCBD06E.md
DXCBD83R.md
UIMB0443.md

Where the Weekly Amount Originates

The pension amount enters the claim through the Non-Monetary Determination (DB11) segment. Program DXCBW30E documents capturing a PENSION-AMT from Segment 11 loop data (LOOPSP11) and storing it in the non-monetary output field NPENAMT.
DXCBW30E.md
 This is the result of the determination process — but the computation of that dollar figure (from the raw pension details a claimant reports or that a pension source provides) is not performed by any program in the held knowledge base.

This confirms the manual process you described: staff determine the weekly pension reduction amount outside LOOPS (historically in Excel), then key that computed dollar amount into LOOPS via a CICS screen as a non-monetary determination. From that point forward, LOOPS carries the pre-computed PENSION-AMT on every payment segment and simply applies the AWBA = WBA − PENSION formula.

Summary Flow (Synthesized)
┌──────────────────────────────────────────────────────┐
│  OUTSIDE LOOPS (today: manual / Excel)               │
│  Staff computes weekly pension reduction from:        │
│  - pension type, lump sum, employer %, etc.          │
│  Result: a dollar amount (e.g., $47.00/week)         │
└───────────────────┬──────────────────────────────────┘
                    │ keyed via CICS screen
                    ▼
┌──────────────────────────────────────────────────────┐
│  LOOPS: Non-Monetary Determination (DB11)            │
│  PENSION-AMT stored on the determination segment     │
│  (DXCBW30E captures it from LOOPSP11)               │
└───────────────────┬──────────────────────────────────┘
                    │ flows to payment segment (DB02)
                    ▼
┌──────────────────────────────────────────────────────┐
│  LOOPS: Payment Record (BP88 VSAM / DB02 IMS)       │
│  BP88-PENSION-AMOUNT1, BP88-PENSION-AMOUNT2          │
│  (pre-populated per certification week)              │
└───────────────────┬──────────────────────────────────┘
                    │ read at check-print / reporting
                    ▼
┌──────────────────────────────────────────────────────┐
│  LOOPS: AWBA = WBA-PAY − PENSION-AMT                │
│  Floor at zero (unless PC=45 CWC)                    │
│  (UIMB0440, BALANCE, DXCBD10R, DXCBD06E, etc.)     │
└──────────────────────────────────────────────────────┘

Implication for the Replacement Spec

The pension spec that replaces the manual Excel process is introducing computation logic that does not exist anywhere in the current LOOPS codebase (in the documented programs). The replacement system would be the first place that logic is codified in software — there is no legacy code to reverse-engineer for the proration formulas. The business rules for prorating lump sums, applying employer contribution percentages, or handling different pension types would need to come from NJ DOL policy documents and SMEs, not from existing COBOL source.

Would you like to explore any of these areas further?

Pension flow from DB11 to DB02

Pension offset segment handling

CWC negative AWBA exception

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 5
- Citation 6
- Citation 7
- Citation 5
- Citation 6
- Citation 9
- Citation 10
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 5
- Citation 11

## v4-Q5

**Q:** Our SSN validation spec routes the new check through ICON's UIQ, with deceased checks out of scope for now. What does LOOPS use for SSN and deceased verification, and where do the results land?

**A** (13:17):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

The knowledge base has rich documentation on this. LOOPS uses a layered approach: basic format checks happen at multiple ingest points, but the real SSN verification (against SSA) and deceased detection both flow through a single external service called VERIS. Here's the full picture.

SSN Format Validation (Local, Within LOOPS)

Before any external check, multiple LOOPS programs perform basic SSN format and numeric validation at their respective entry points:

DXCB147U — Validates SSN against the NNN-NN-NNNN pattern, checking all 11 character positions individually (3 digits, dash, 2 digits, dash, 4 digits)
DXCBD42C — Validates SSN is all-numeric for payment/redet records from the WRREDET file; writes 'SSN MUST BE NUMERIC' to an error report if it fails
UIMB0134 — Validates Employee SSN is all-numeric for New Hire crossmatch records
UIMI0158 — Validates SSN is numeric on crossmatch output records, setting an SSN-Passed flag ('Y'/'N') that gates whether the record is written

These are all local format checks — they reject garbage data but do not confirm the SSN is real or alive.

SSN Verification Against SSA (External — VERIS)

The actual identity-level SSN verification is performed by calling the VERISB (batch) or VERISBN (new variant) external subroutine, which communicates with the Social Security Administration.
VERISB.md
VERISBN.md

Inputs to VERIS:

Claimant's SSN (VERIS-SSN)
Date of Birth, reformatted to CCYY-MM-DD (VERIS-DOB)

Trigger point documented: Program UIMI0025 (CWC initial claim processing, Program Code 45) fires the VERIS call after successfully inserting the new basic claim segment into the IMS database. The trigger flag LETS-DO-VERIS is set to 'Y', and DB01-DATE-BIRTH is saved for the call.
UIMI0025.md
 [108]

VERIS Response Fields:

VERIS-COMPCODE — MQ completion code (00 = successful communication)
VERIS-SSN-RETCDE — the SSN-level return code from SSA
Plus: VERIS-DOBCODE, VERIS-LOWASSIGN, VERIS-HIGHASSIGN, VERIS-AGENOW, VERIS-LOWAGE, VERIS-HIGHAGE, VERIS-DOBSTRING, VERIS-STATESTRING, VERIS-FIRSTNAME, VERIS-LASTNAME, VERIS-RIDDOB, VERIS-RIDDOD (date of death), VERIS-ZIP1, VERIS-ZIP2
Where SSN Verification Results Land

1. UIMV_SSN_VALIDITY DB2 table — Every VERIS call result (success or failure) is recorded here. Key fields include [108]:
UIMI0025.md

IDN-SSN, Program Code, Date of Claim
MQ-COMPCODE, MQ-REASON
SSN-RETCDE, SSN-RETCDE-LIT
DOBCODE, LOWASSIGN/HIGHASSIGN, AGENOW, LOWAGE/HIGHAGE
STATE-CDE, DOBSTRING
HISTORY-IND (set to '0' for current)

2. Claim pended in IMS — When VERIS-COMPCODE = 00 AND VERIS-SSN-RETCDE ≠ 00 (SSN problem confirmed), the program [108]:
UIMI0025.md

Retrieves the basic segment with GHU
Sets DB01-POT-PAY-PEND = 1 (potential payment pending)
Increments DB01-REMARKS-COUNTER
Creates a Remarks segment (DB16) with the message 'PROBLEM WITH SSN - CLAIM PENDED'
Deceased Detection — Three Sources

Program UIMB0726 / UIMI0726 documents a three-source deceased check that sets the Deceased Flag ('Y'/'N'). A claimant is marked deceased if any of the following is true [101]:
UIMB0726.md
UIMI0726.md

Table

Source

	

Check

	

How Death Date Is Captured


Input master record	Deceased Indicator ≠ 0 on the existing master input record	Date carried from the input record
UIMV_SSN_RETIRED DB2 table	SSN found in the SSN Retired table	DATE-OF-DEATH from the table record
VERIS death verification	VERIS-SSN-RETCDE = '00000110'	VERIS-RIDDOD (date of death from SSA)
View more

Eligibility threshold for VERIS death check: The claimant's AR-TOTAL-REFUND must be greater than $24.99 — only claimants with a meaningful outstanding balance get the VERIS deceased check.
UIMB0726.md

Where Deceased Results Land

1. UIMV_SSN_RETIRED DB2 table — When VERIS returns SSN-RETCDE = '00000110', a record is inserted with [108]:
UIMI0025.md

IDN-SSN, Program Code, Date of Claim
FIRSTNAME, LASTNAME (from SSA)
DATE-OF-BIRTH, DATE-OF-DEATH
ZIP-BENEFIT-SENT, ZIP-LUMP-SUM-SENT

2. Output Master Record (ACP) — Programs UIMB0726/UIMI0726 set [101]:
UIMB0726.md
UIMI0726.md

AR-DECEASED-IND = 1 and AR-DECEASED-DATE = WS-DATE-DEATH-VERIS (if deceased)
AR-DECEASED-IND = 0 and AR-DECEASED-DATE = zeroes (if not deceased)

3. Downstream cleanup — Program DXCBACP1 applies deceased date placeholder correction: if the Deceased Date is '????????' and the indicator is 1, it replaces it with the current system date; if the indicator is 0, it clears to zeros.
DXCBACP1.md

VERIS Resilience Rules
If a VERIS call fails and the error reason is not 2033 (non-connection error), the total error counter increments.
UIMB0726.md
If total VERIS errors exceed 75, all further VERIS calls are disabled for the remainder of the run (VERIS-SW = 'N'), and the message '*** MORE THAN 75 VERIS ERRORS ***' is logged.
UIMB0726.md
ICON ↔ LOOPS Interface

The knowledge base documents ICON as an upstream system that feeds data into LOOPS. Source code comments in UIMB0003.txt / UIMI0003.txt reference formatting alien registration numbers "FROM ICON TO LOOPS" and ensuring data acceptance for the S.A.V.E. program.
UIMI0003.txt
 [102] Job TNPYD006 also generates HCTC payment files formatted for ICON transmission.
TNPYD006.md
 [106] However, the knowledge base does not contain a process or interface named "UIQ" — the term does not appear in any retrieved document. If your spec references ICON's UIQ as the channel for the new SSN check, that may be an ICON-side component documented outside the LOOPS knowledge base, or it may be worth confirming the exact name with the ICON team.

Summary Flow (Synthesized from Multiple Sources)
┌─────────────────────────────────────────────────────────┐
│  LOCAL FORMAT CHECKS (multiple programs)                │
│  DXCB147U: NNN-NN-NNNN format                          │
│  DXCBD42C, UIMB0134, UIMI0158: numeric-only            │
│  → Rejects garbage; does NOT confirm SSN is real        │
└──────────────────────┬──────────────────────────────────┘
                       │ passes format check
                       ▼
┌─────────────────────────────────────────────────────────┐
│  VERIS CALL (VERISB / VERISBN subroutine)              │
│  Input: SSN + DOB                                       │
│  External: Social Security Administration               │
│  Triggered in UIMI0025 (CWC claim filing, PC=45)       │
└──────────────────────┬──────────────────────────────────┘
                       │ response received
            ┌──────────┼──────────┐
            ▼          ▼          ▼
      SSN OK      SSN Problem   Deceased/Retired
    (RETCDE=00)  (RETCDE≠00,   (RETCDE=00000110)
                  ≠00000110)
            │          │          │
            ▼          ▼          ▼
     ┌──────────┐ ┌──────────┐ ┌──────────────────┐
     │ Record   │ │ Pend     │ │ Insert into      │
     │ in       │ │ claim:   │ │ UIMV_SSN_RETIRED │
     │ UIMV_SSN │ │ POT-PAY  │ │ (name, DOB, DOD, │
     │_VALIDITY │ │ PEND=1   │ │  ZIP codes)      │
     │          │ │ + Remark │ │                  │
     │          │ │ DB16     │ │ + Record in      │
     │          │ │          │ │ UIMV_SSN_VALIDITY│
     └──────────┘ └──────────┘ └──────────────────┘
                                        │
                  ┌─────────────────────┘
                  ▼
     ┌───────────────────────────────────┐
     │  ACP Master Record Output         │
     │  (UIMB0726 / UIMI0726)           │
     │  AR-DECEASED-IND = 1             │
     │  AR-DECEASED-DATE = death date   │
     │  (three-source check: input rec, │
     │   SSN Retired table, VERIS)      │
     └───────────────────────────────────┘

Implication for Your SSN Validation Spec

Your replacement spec routing through ICON's UIQ is introducing a different verification path than what LOOPS uses today. In the current system, VERIS is the sole SSN verification channel, and it doubles as the deceased detection mechanism (return code '00000110'). If the new UIQ-based check only validates SSN existence and leaves deceased checks out of scope, be aware that today's VERIS call serves both purposes simultaneously — the replacement will eventually need a deceased-detection equivalent to cover the UIMV_SSN_RETIRED insert and the downstream AR-DECEASED-IND/AR-DECEASED-DATE population that currently depend on VERIS return code '00000110'.

Would you like to explore any of these areas further?

VERIS MQ messaging details

DB2 table deep dive

Deceased detection logic in detail

_Citations:_
- Citation 5
- Citation 6
- Citation 7
- Citation 7
- Citation 7
- Citation 8
- Citation 9
- Citation 8
- Citation 7
- Citation 8
- Citation 9
- Citation 10
- Citation 8
- Citation 8
- Citation 11
- Citation 12

## v4-Q6 (asked immediately after v4-Q5)

**Q:** When our identity-verification writeback hits a cancelled claim, LOOPS rejects it with response code 7 and a message starting "ERROR: CANCELLED CLAIM". Which LOOPS program produces that response, and is there a list of the writeback response codes?

**A** (13:19):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

I need to be straightforward here: the knowledge base does not contain a process or interface named "identity-verification writeback" that produces a "response code 7" or a message starting with "ERROR: CANCELLED CLAIM". Neither that response-code numbering scheme nor that exact message text appears in any retrieved document.

What the Knowledge Base Does Document for Cancelled-Claim Rejection

The closest documented match is program DXCBDI5U (the IB5 LOOPS Interface), which rejects inbound IB5 interstate monetary determination records when the target claim is cancelled. However, this is not an identity-verification writeback — it's the interstate claims monetary processing interface. Here's what it actually does:

Trigger: When DB01-CANC-CLAIM NOT = '0' on the retrieved basic claim record (Segment 01), the IB5 record is rejected.
DXCBDI5U.md

Exact message literal (from source code, DXCBDI5U.txt):
DXCBDI5U.txt

cobol

02 MSG-CANCELED-CLAIM    PIC X(35)
        VALUE 'CLAIM IS CANCELED'.

The message is 'CLAIM IS CANCELED' — not 'ERROR: CANCELLED CLAIM'.

Mechanism: The program moves MSG-CANCELED-CLAIM to WS-MESSAGE, calls 40000-FORMAT-ERROR-RECORD, which writes a record (SSN + effective date + message) to the MESSAGES output file and increments WS-NUMBER-REJECTED-IB5S. Control then goes to 31000-EDIT-IB5-EXIT, halting all further processing for that IB5.
DXCBDI5U.md
DXCBDI5U.txt

No numbered response codes: DXCBDI5U does not produce a numeric response code (like "7") — it writes rejection messages to a flat MESSAGES file. There is no response-code field in the WS-MESSAGE-RECORD layout. The layout is:

cobol

01 WS-MESSAGE-RECORD.
   02 WS-MSG-SSN                PIC 9(9).
   02 WS-MSG-EFFECTIVE-DATE     PIC 9(6).
   02 WS-MESSAGE                PIC X(50).
Full List of DXCBDI5U Rejection Messages (Synthesized)

The source code defines these rejection message literals — they are text messages, not numbered codes :
DXCBDI5U.md
DXCBDI5U.txt

DXCBDI5U IB5 Rejection Messages

Message Literal

	

Variable Name

	

Condition


INVALID IB5 DATA - + field name + data	MSG-INVALID-IB5-DATA	IB5 field-level validation failure (transaction type, claim type)
IB5 MARKED RETURNED WAGES AND EB	MSG-RETURN-AND-EB	Returning Wages combined with EB claim type
EFFECTIVE DATE BEFORE 7/1/86	MSG-PRIOR-TO-7-1-86	Effective date prior to 07/01/1986
DEPENDANCY AMOUNT REPORTED INVALID	MSG-INVALID-DEP-AMT	Dependency amount invalid for paying state
STATE NOT PROCESSABLE	MSG-STATE-NOT-PROCESSABLE	Paying state not in processable table
ST. NOT PROCESSABLE ON EFFECT. DATE	MSG-EFF-DATE-NOT-PROCESSABLE	State not yet processable on the IB5 effective date
CLAIMANT BASIC NOT FOUND	MSG-NO-BASIC / MSG-BASIC-NOTFND	No basic claim record for SSN + PC 45 + effective date
IB5 IS NOT FOR CURRENT CLAIM	MSG-NONCURRENT-CLAIM	LA Current Claim Indicator ≠ '1'
CLAIM IS CANCELED	MSG-CANCELED-CLAIM	Cancel Indicator (DB01-CANC-CLAIM) ≠ '0'
CLAIM STATUS IS ALREADY INVALID	MSG-ALREADY-INVALID	Returning Wages on an already-invalid claim
View more

Additionally, two informational (non-rejection) messages are documented :
DXCBDI5U.md

'UI REDETERMINED, EB HAS BEEN FILED' (MSG-UI-REDET-EB-FILED) — warns that a UI redet may affect an existing EB filing
'EB LIABILITY > 50% UI-PROCESSED 50%' (MSG-EB-MORE-THAN-HALF) — EB chargeable amount exceeds 50% of UI max liability
What's Missing

The knowledge base does not document:

An identity-verification writeback interface — VERIS (VERISB/VERISBN) is documented as a read-only verification request (sends SSN+DOB to SSA, gets back response codes), not a writeback that receives external results.
VERISB.md
VERISBN.md
A numbered response-code scheme (1, 2, 3 … 7) for any writeback — DXCBDI5U uses text messages, not numeric codes
The exact message prefix "ERROR: CANCELLED CLAIM" — DXCBDI5U uses 'CLAIM IS CANCELED'
Recommendations

The interface you're describing — an identity-verification writeback with numbered response codes — may be:

A newer interface not in the held LOOPS code slice — the knowledge base covers selected modules, not the whole system
A component on the ICON/replacement side that maps LOOPS rejection text into numbered codes before returning them to the caller
A different LOOPS program outside the knowledge base coverage (naming conventions to check: DXCB* for batch, DXCD*S for CICS, UIM* for subprograms)

I'd suggest confirming with the interface team which program actually produces the numbered response codes and whether "response code 7" is a LOOPS-side construct or something the calling system derives from LOOPS' text rejection messages.

Would you like to explore further?

Search for writeback interface programs

Detailed DXCBDI5U rejection walkthrough

Cancelled-claim handling across LOOPS programs

_Citations:_
- Citation 1
- Citation 2
- Citation 1
- Citation 2
- Citation 1
- Citation 2
- Citation 1
- Citation 3
- Citation 4

## v4-Q7

**Q:** For the Connect migration: when a weekly certification comes in through the IVR today, how does LOOPS mark the submission channel on the certification record, and how would I tell an IVR cert from a web cert in the data?

**A** (13:19):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

Great question for the Connect migration — LOOPS uses a two-field convention on the certification record itself (not a single "channel" flag) to identify where a weekly certification was submitted. The channel is determined by the combination of Operator ID and Terminal ID stamped on the record at the time of entry. Here's exactly how it works:

How LOOPS Marks the Submission Channel

LOOPS does not store a literal "IVR" or "WEB" label on the certification record. Instead, it stamps two metadata fields at submission time, and downstream programs derive the channel from those values :
DXCBDA2R.md
DXCBDA2R.cbl.md

Table

Field (PAYVSAM)

	

Field (NOPAY)

	

Description


BP88-OPERATOR-ID-CERT	NOPAY-OPERATOR-ID-ENTRY	Operator ID at time of certification entry
BP88-TERMINAL-ID-CERT	NOPAY-TERMINAL-ID-ENTRY	Terminal ID at time of certification entry
View more

The channel classification logic (documented in program DXCBDA2R.cbl, paragraph 2600-CHECK-ENTRY-SOURCE) then applies these rules :
DXCBDA2R.md
DXCBDA2R.cbl.md

Channel Classification Rules
LOOPS Weekly Certification Channel Classification Rules

Channel

	

Terminal ID

	

Operator ID

	

...


WEB (online self-service)	'7777'	9000	...
PHONE / IVR (telephone self-service)	'7777'	Not 9000	...
Manual P100 (staff-assisted)	Not '7777'	Not 9000	...
View more
How to Tell an IVR Cert from a Web Cert in the Data

The key distinguisher is the Operator ID — both IVR and Web share Terminal ID '7777', but only Web uses Operator ID 9000 :
DXCBDA2R.md
DXCBDA2R.md

IVR cert: Terminal ID = '7777' AND Operator ID ≠ 9000
Web cert: Terminal ID = '7777' AND Operator ID = 9000
Manual/staff cert: Terminal ID ≠ '7777' (Operator ID is irrelevant for this classification)

So if you're querying the PAYVSAM or NOPAY data, a filter like:

sql

-- IVR certifications
WHERE TERMINAL_ID = '7777' AND OPERATOR_ID <> 9000

-- Web certifications
WHERE TERMINAL_ID = '7777' AND OPERATOR_ID = 9000

-- Manual / staff-entered
WHERE TERMINAL_ID <> '7777'

will separate the three channels.

Where This Logic Is Used
DXCBDA2R.cbl — the batch Daily/Weekly Certification Extract Report program — is the primary documented consumer of this logic. It reads both the PAYVSAM (payment) and NOPAY (no-payment) input files, classifies each cert by channel, and produces three separate summary reports: Combined, Web-only, and Phone-only.
DXCBDA2R.cbl.md
NOPAYRFM — the NOPAY-to-PAYVSAM reformatter — preserves these fields when it maps NOPAY-TERMINAL-ID-ENTRY → BP88-TERMINAL-ID-CERT and NOPAY-OPERATOR-ID-ENTRY → BP88-OPERATOR-ID-CERT.
NOPAYRFM.md
Important Caveats for the Connect Migration

No dedicated "channel" column exists — the channel is derived from the Operator ID / Terminal ID combination, not stored as a discrete code. If Connect introduces a new submission path, it would need to either reuse one of the existing ID conventions or add a new indicator field.

IVR Operator IDs are variable — the IVR is identified by Terminal ID '7777' with any Operator ID other than 9000. The knowledge base does not document what specific Operator ID values the IVR system stamps (it could be a fixed IVR system ID or vary). This would be worth confirming with the IVR/telephony team.

Coverage caveat — this logic is documented in DXCBDA2R and NOPAYRFM within the held code slice. Other LOOPS programs or CICS screens that consume these fields may apply the same convention, but that cannot be confirmed from the knowledge base alone.

What would you like to explore next?

DXCBDA2R batch flow details

BP88 certification record layout

NOPAYRFM field mapping

_Citations:_
- Citation 1
- Citation 2
- Citation 1
- Citation 2
- Citation 1
- Citation 3
- Citation 2
- Citation 4

## v4-Q8

**Q:** The MUNC replication spec shows each municipality row carries a local_office_id. On the LOOPS side, how are local offices represented and used in claims processing, and is the municipality-to-local-office assignment documented there?

**A** (13:21):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

This is a great question that touches several LOOPS layers. Let me walk through what the knowledge base documents about local offices, how they're used throughout claims processing, and what it says (and doesn't say) about the municipality-to-local-office linkage.

Local Office Representation in LOOPS

In LOOPS, the local office is stored as a numeric code on the Claim Basic Segment (DB01), in the field DB01-LOCAL-OFF. Every claim record carries this code from the point of initial filing, and it propagates to virtually every downstream segment and transaction. There are actually two local-office fields that travel together on most segment prefixes:

Table

Field

	

Description

	

Source


DB01-LOCAL-OFF (or LOCAL-OFF-CUR, LO)	The local office of record for the claim — the office that "owns" it	Set at claim filing, stored on DB01
RESP-LOCAL-OFF-CUR / RESPLO	The responsible local office — the office accountable for a particular action	Often set equal to DB01-LOCAL-OFF, but can differ in some contexts
View more

Special local office codes documented in the held code :
DXCBW30E.md
DXCBW39E.md

999 and 997 — designate out-of-state or special processing offices
Codes < 999 — regular in-state local offices
How Local Offices Are Used in Claims Processing

The local office code is a workhorse field that drives logic in nearly every batch program in the knowledge base. Here are the major documented uses:

1. Claim Type Classification

The local office is one of the two primary inputs (along with program code) to the Claim Type Classification routine (X200-DO-TYPECLM) used in programs DXCBW30E and DXCBW39E :
DXCBW30E.md
DXCBW39E.md
DXCBW39E.md

Local Office = 999 or 997 → Claim Type 3 (Out-of-State / Special), with subsequent municipality range validation
Local Office ≠ 999/997, Program Code ≠ 11/12 → municipality range determines Type 1 vs. Type 2
Program Code = 11 or 12 → Type 4 (Interstate), regardless of local office
2. Table 003 Lookup (New Claims)

When a new claim is inserted (UIMI0003), the local office code is validated against Table 003, which maps each local office to its :
UIMI0003.md

Adjudication Center (T003-ADJUD-CTR-LO)
RCC Center (T003-RCC-CTR-LO)

If the local office is not found in Table 003, the claim gets an error status and the error message 'LO NOT FOUND ON TABLE' is logged.

3. Payment Segment Propagation

When payment segments are created (programs UIMI0031, UIMB0031), the local office from DB01 is copied to both PR02-LOCAL-OFF-CUR and PR02-RESP-LOCAL-OFF-CUR in the payment prefix, establishing the claim's office as also responsible for the payment.
UIMI0031.md
UIMB0031-cbl.json

4. Non-Monetary Determination Segments

Program DXCBD23U copies the local office from DB01 into both the Local Office and Responsible Local Office fields of the Segment 11 prefix.
DXCBD23U.md

5. Occupational Transfer Exclusion

Program DXCBD53E skips any claim record where Local Office = 997 or 999, excluding out-of-state claims from the ES occupational transfer output.
DXCBD53E.md

6. ERI Scheduling Eligibility

Program DXCBD07E compares the local office on the DB01 claim record against the local office on the ERI Master File record — a mismatch disqualifies the claim from ERI scheduling.
DXCBD07E.md

7. Claimant Demographics / DB2 Records

When populating the UIMV_CLAIMANT table (UIMI0004, UIMB0025), the local office is copied to CDE_LOCAL_OFFICE.
UIMB0025.md
UIMI0004.md

8. Badge Generation

Badges are only generated when Local Office < 999 and no badges are already on file. Office 999+ suppresses badge generation.
UIMB0031-cbl.json

Municipality-to-Local-Office Assignment

This is where I need to be very direct: the knowledge base does not document a municipality-to-local-office mapping table or lookup mechanism.

Here's what is documented:

The municipality code (DB01-MUNIC-CODE / MUNCI-CUR) and the local office code (DB01-LOCAL-OFF) are both stored on the Claim Basic Segment (DB01), but they are treated as independent fields in every documented program.
The claim type classification logic uses them in sequence (check local office first, then municipality range), but never derives one from the other.
Table 003 maps local offices to adjudication/RCC centers — but there is no documented "Table XXX" that maps municipalities to local offices in the held code.

Your MUNC replication spec showing a local_office_id on each municipality row suggests there is a reference table somewhere that maps municipalities to their responsible local office — but that table's contents and the process that populates or consumes it live outside the knowledge base's coverage. Likely candidates for where it would reside:

The CODELOOP VSAM dataset (which holds the populated code-table values, including T120 and potentially other reference tables — the knowledge base has the T120TABL.cpy layout but not the loaded values)
A DB2 reference table used by the CICS online claim-filing screens (the C030 conversation) to default or validate the local office based on the claimant's municipality at filing time
An operations-maintained reference dataset that is outside the batch program slice documented here
Summary (Synthesized)
Local Office Usage Summary In LOOPS

Aspect

	

What's Documented

	

Source


Storage location	DB01-LOCAL-OFF on Claim Basic Segment	Multiple programs
Special codes	999, 997 = out-of-state/special	DXCBW30E, DXCBW39E
Table 003 validation	Maps LO → Adjudication Center + RCC Center	UIMI0003
Payment propagation	LO copied to both Local Office and Responsible LO on payment prefix	UIMI0031, UIMB0031
Claim type classification	LO = 999/997 → Type 3; used with municipality and program code	DXCBW30E, DXCBW39E
ERI scheduling	LO on claim must match LO on ERI Master File	DXCBD07E
Occupational transfer	LO = 997 or 999 → claim excluded from output	DXCBD53E
Municipality → LO mapping	Not documented in held code; likely in CODELOOP VSAM or a DB2 reference table	Outside KB coverage
View more

The bottom line for the Connect migration: LOOPS uses the local office extensively once it's on the claim, but the mechanism that assigns a local office based on municipality at claim-filing time is not in the batch program slice covered by the knowledge base. That assignment logic would be in the CICS online claim-filing conversation (C030) or a supporting reference table — worth checking with the team that owns the online claim intake screens or the CODELOOP VSAM dataset.

Would you like to explore further?

How local office gets assigned during claim filing

More detail on Table 003 and office hierarchies

End-to-end municipality code flow in LOOPS

_Citations:_
- Citation 1
- Citation 2
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
- Citation 6
