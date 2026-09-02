# 2026-09-02_1142_quick_playwright_v6

- **Backend:** quick (transport: playwright)
- **Bank:** v6 (`question_sha256` bc49a835de4a…)
- **Agent:** engineering_onboarding_specialist (`30b0228b-b58a-43ad-818b-2f262f11108f`)
- **Conversation:** `c1881dbd-3d4d-46b1-9093-13843871b436`
- **Model:** Advanced
- **Started:** 2026-09-02 11:30
- **Finished:** 2026-09-02 11:42
- **Status:** complete
- **Questions asked:** 8, answered: 8

## v6-Q1

**Q:** Walk me through the daily bank reconciliation job L204DF2: what does it produce, and how do check records get from the daily register to the bank files?

**A** (11:31):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

Here's a comprehensive walkthrough of job L204DF2, drawn from the JCL documentation (L204DF2.md) and the raw JCL source (L204DF2.txt).

The JCL header describes this job's purpose as: "THIS DAILY JOB PRINTS THE DAILY BATCH REGISTER AND BANK FILES."
L204DF2.txt
 It carries a restart criticality of 9 (high priority).
L204DF2.txt

What L204DF2 Produces

The job has three main output tracks, all sourced from a single input file — LAK2LDXP.L204DF.BIGREC.DTL (the "Big Record Detail" file, which is the daily batch register) :
L204DF2.md

1. Four Bank Account Reconciliation Files — sorted by account key (first 20 bytes, ascending):

RECON.ACC2528.DTL — O-Category records
RECON.ACC2536.DTL — B-Category records
RECON.ACC0987.DTL — T-Category records
RECON.ACC0499.DTL — E-Category records

2. Checks Issued Detail File — LAK2LDXP.L2BPBNK1.CHECKS.ISSUED.DTL (GDG) — a deduplicated, sorted file of standardized 39-byte check records.
L204DF2.md

3. Error/Exception Outputs:

ERROR.DISK.DTL — reconciliation records that failed bank matching (for accounts 0001273518 / 0001273507)
ERROR.FICHE.DTL — microfiche-ready tape archive of those errors (30-day retention)

4. Backups produced each run :
L204DF2.md

RECNBKP2.DTL — consolidated 4-account reconciliation backup on tape (120-day retention)
Individual GDG backups of each of the four account files
BANKMTCH.BCKUP — Bank Match VSAM snapshot on tape (30-day retention)
PAYREC.BCKUP — Payment Record backup on disk
RECNBKP2.DLY.BCKUP — permanent daily backup tape (EXPDT=99000)
BNKFLDTE.DTL — date-enriched (88-byte) bank record archive on tape
How Check Records Flow from the Daily Register to the Bank Files

Here is the step-by-step pipeline, in execution order :
L204DF2.md

Phase 1 — Cleanup
PREPARE (IEFBR14): Unconditionally deletes six prior-run files (the four account recon files, the intermediate recon file, and the error file) to ensure a clean slate.
Phase 2 — Build the Reconciliation Work File
SORTA (SORT): Copies every 80-byte record from BIGREC.DTL into a temp work file &&RECONCIL. No filtering — this is a straight copy.
Phase 3 — Filter, Date-Enrich, and Categorize
BNKFLMOD (program): Reads &&RECONCIL and extracts only "Old Account" bank records → writes OLDACCT.BNKREC.DTL (80-byte).
BNKFLDTE (program): Reads OLDACCT.BNKREC.DTL + a DATECARD control card, appends 8 bytes of date data → writes 88-byte records to BNKFLDTE.DTL (GDG tape archive).
UIBNKDAT (program): Reads OLDACCT.BNKREC.DTL + DATECARD and routes each record to exactly one of four category streams: &&BANKO, &&BANKB, &&BANKT, &&BANKE. No record is duplicated or dropped.
Phase 4 — Sort into Per-Account Bank Files

Each temp category file is sorted on positions 1–20 (account key, ascending) and written to its permanent reconciliation file:

Table

Sort Step

	

Input Category

	

Output Account File


SORTO	&&BANKO (O-Category)	RECON.ACC2528.DTL
SORTB	&&BANKB (B-Category)	RECON.ACC2536.DTL
SORTT	&&BANKT (T-Category)	RECON.ACC0987.DTL
SORTE	&&BANKE (E-Category)	RECON.ACC0499.DTL
View more
Phase 5 — Consolidation and Individual Backups
REPRO4 (IDCAMS): Concatenates all four account files (in order: 2528 → 2536 → 0987 → 0499) into RECNBKP2.DTL (tape GDG, 120-day retention).
BACKUP1–4 (IDCAMS): Each creates a GDG backup of its respective account file. These execute unconditionally.
Phase 6 — Bank Matching (Separate Track)
SORT1 (SORT): Filters &&RECONCIL to only records where positions 71–80 = 0001273518 or 0001273507.
BNKFLBLD (program): Matches those filtered records against the BANKMTCH VSAM cluster; unmatched/failed records go to ERROR.DISK.DTL (133-byte print-line format).
REPRO5 (IDCAMS): Backs up the BANKMTCH VSAM to tape (30-day retention).
Phase 7 — Build the Checks Issued File (the Register-to-Bank path)

This is the specific path that transforms daily register records into the bank's checks-issued file:

BUILDOUT (program): Reads the full BIGREC.DTL again and transforms each record into a standardized 39-byte output record → writes to temp file &&OUTSTD.
SORTD (SORT): Sorts all 39-byte records in ascending order across the full record (positions 1–39), and eliminates exact duplicates (SUM FIELDS=NONE).
Output: a new GDG generation of LAK2LDXP.L2BPBNK1.CHECKS.ISSUED.DTL — the deduplicated checks-issued file ready for the bank.
Phase 8 — Final Housekeeping
REPRO6: Backs up PAYREC.DTL to disk GDG.
IEFBR14A: Deletes SPOILCHK.DTL (only if all prior steps succeeded; otherwise preserved for investigation).
REPRO8: Copies ERROR.DISK.DTL to microfiche tape (30-day retention) — only if REPRO6 succeeded.
REPRO9: Copies RECNBKP2.DTL to a permanently retained daily backup tape (EXPDT=99000) — only if all prior return codes ≤ 4.
Key Design Notes
BIGREC.DTL is the hub: It feeds both the reconciliation path (via &&RECONCIL) and the checks-issued path (directly via BUILDOUT). The knowledge base does not document what upstream job produces BIGREC.DTL, so that upstream dependency lives outside this job's documentation.
Error handling is defensive: Every output file with DISP=(NEW,CATLG,DELETE) is automatically removed on step failure, and most steps are gated on COND=(0,NE) (all prior RC = 0).
Programs BNKFLMOD, BNKFLDTE, UIBNKDAT, BNKFLBLD, and BUILDOUT are externally linked programs — their internal logic (the actual filtering/categorization/transformation rules) is not documented in the JCL-level knowledge base. The categorization rules in UIBNKDAT in particular (what makes a record O vs. B vs. T vs. E) would require reviewing that program's source code.
Would you like to explore further?

What feeds BIGREC.DTL into this job?

Dive into the categorization or transformation programs

Show the CA-7 scheduling for this job

_Citations:_
- Citation 1
- Citation 1
- Citation 2
- Citation 2
- Citation 2
- Citation 2

## v6-Q2

**Q:** How are the daily BC3E claimant forms prepared for laser printing in job L207DCL, and what does each program in the chain do to the record?

**A** (11:33):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

Here is a comprehensive walkthrough of job L207DCL, synthesized from the JCL source (L207DCL.txt), the JCL documentation (L207DCL.md), and the COBOL program analyses (DXCB165U.md, DXCB166U.md, DXCBD24E.md, DXCBBC3E.md, UIMI0754.md, DXCBD54R.md).

The JCL narrative states: "PRINTS NEW BC3E FORMS FOR THE CLAIMANT ON LASER." It has a restart criticality of 1 (force complete, especially when STEP04 returns RC=04 meaning no data).
L207DCL.txt
L207DCL.md

What the Job Produces

The ultimate output is a merged AFP print stream of domestic and foreign BC3E Unemployment Benefit Determination forms, routed to the USPS Daily AFP printer (AFPOUT1) with form definition GEN14, page definition DOLB3E, directed to the ADF_ND-USPS:DAILY print room.
L207DCL.txt
L207DCL.md

It also produces GDG backups of every intermediate product and a +10 day date-adjusted archive for potential reprints.
L207DCL.md

The Upstream Input

The source file is LAK2LDXP.MAIL.L207DC2.DATA.DTL — 778-byte fixed-length laser output records. These are produced upstream by program DXCBD54R, which reads raw BC3 input records and formats them into printable form layout. DXCBD54R handles:

Unpacking SSN into XXX-XX-XXXX display format
Converting all dates (Date of Claim, Base Period Begin/End, Benefit Year Begin/End, First Report Date) from ISO YYYYMMDD to American MM/DD/YYYY via the F6CONF2X date conversion routine
Formatting dollar amounts (WBR, MBA, Max Charge Amount) from packed to display format
Calculating Weekly Dependent Allowance = Before-Dependency Amount − WBR
Computing quarterly wages, weeks, and totals for all four base period quarters
Setting wage source checkboxes (Employer vs. Claimant affidavit) and the Monetary Redetermination indicator
Classifying each record's form type: B3W → BC3E (regular), B3R → BC3ER (redetermination)
Validating the Local Office number against Table 112 — invalid = hard ABEND (code 227)

The L207DCL job does not format the BC3E form content itself. It receives already-formatted 778-byte laser records and prepares them for physical laser mailing.

The Full Program Chain — What Each Step Does to the Record
Phase 1 — Validation & Housekeeping
Table

Step

	

Program

	

What It Does


VERIFY	IDCAMS	Verifies VSAM Codes Cluster integrity; if RC≠0, all downstream steps are bypassed
BACKUP1	IDCAMS REPRO	Creates GDG backup of source file (778-byte records)
PREPARE1	IEFBR14	Deletes all 9 intermediate files from prior run
STEP04	IEBPTPCH	Prints first record to job log for operator visual verification
View more
Phase 2 — Domestic / Foreign Split
Table

Step

	

Program

	

What It Does

	

...


SORT1	SORT	Extracts Foreign records where positions 342–346 = '00000' (zero ZIP) → FRGN.DTL	...
SORT2	SORT	Extracts Domestic records where positions 342–346 ≠ '00000' → DATA.DTL	...
View more
Phase 3 — Domestic Record Transformation Chain

Each program hands its output to the next. Here is what happens to each domestic record as it passes through the chain:

Step DXCB165U — ZIP Code Extraction & Append (source: DXCB165U.md)
DXCB165U.md

Input: 778-byte laser output record
Does: Copies the full 778-byte record to output, then extracts the 5-digit ZIP (BC3L-ZIP-END1) and the 4-digit ZIP+4 extension (BC3L-ZIP-END4) from within the record and appends them to the end
Output: 787 bytes (778 original + 5 ZIP + 4 ZIP+4) → DC3.DATA.DTL
Also: Reads a DATECARD control card and converts daily/week-ending dates to YYYYMMDD, but the date values are only displayed for audit — the record transformation is purely ZIP appending

Step DXCB166U — Tray Assignment & Classification (source: JCL-level documentation)

Input: 787-byte date-enriched records
Does: Applies tray assignment and classification logic using the DATECARD reference date — this is where records get organized into mail trays for postal sorting
Output: 778 bytes (compressed back) → TRAY.DTL
Note: DXCB166U's internal COBOL source is not in the knowledge base at program-rule level; the tray-assignment business rules are documented only at JCL-step level

Step DXCBD24E — ZIP Code Formatting onto Address Line (source: DXCBD24E.md)
DXCBD24E.md

Input: 778-byte tray detail record
Does: Reads the 5-digit ZIP and 4-digit extension, formats them as NNNNN-NNNN, then scans the 40-character city/state address field (address line 6) character by character looking for three consecutive spaces. When found, it inserts the formatted 9-digit ZIP code at that position — ensuring the ZIP appears on the same line as city/state without overwriting existing text
Output: 778 bytes → EMAIL.ZUMDAHR1.TRA10.DTL

Step DXCBBC3E (step name DXCBBC3E) — Name Reformat + Sort Key Construction (source: DXCBBC3E.md)
DXCBBC3E.md

Input: 778-byte email/AFP record
Does three things to each record:
Parses and reformats the claimant name: The name arrives as LASTNAME/FIRSTNAME MIDDLEINIT. The program UNSTRINGs it on / (last name), double-space (first name), and single-space (middle initial), then reconstructs it in natural reading order: "First Middle Last" or "First Last" if no middle initial. The result is written back into BC3L-CLAIM-NAME within the record
Constructs a 4-digit SSN sort key: Takes SSN-2 (Group Number, 2 digits) + first 2 digits of SSN-3 (Serial Number) → composite sort key SP-SSN-END
Constructs an 8-character date sort key: Assembles MAIL-YY + MAIL-MM + MAIL-DD → YYYYMMDD format
Appends both keys: The 778-byte record becomes the data section, plus the 4-digit SSN key and 8-character date key appended
Output: 790 bytes (778 data + 4 SSN key + 8 date key) → TRAF.DTL

Step UIMB0754 (program UIMI0754) — DB2 Employer Synonym Enrichment (source: UIMI0754.md)
UIMI0754.md

Input: 790-byte traffic detail record
Does: Extracts the SSN and FEIN from each record, queries DB2 table UIMT_SG03_EMPLOYER to retrieve a FEIN Synonym Code (SYNCODE), and appends it to the record. SQL errors are captured in the SQLERRLG error log
Output: 797 bytes → SYNC.DTL
Phase 4 — Foreign Record Transformation Chain (Parallel Path)

Foreign records (ZIP = '00000') go through a shorter but identical tail-end pipeline:

Table

Step

	

Program

	

Input

	

...


DXCBBC3X	DXCBBC3E (same program)	778 bytes from FRGN.DTL	...
UIMB754B	UIMI0754 (same program)	790 bytes	...
View more

Foreign records skip DXCB165U, DXCB166U, and DXCBD24E — those steps handle ZIP-based postal tray sorting that doesn't apply to foreign addresses.

Phase 5 — Merge & Print

Step LASRPRNT (IEBGENER) — Concatenates FRG3 (foreign) first, then SYNC (domestic) appended after, and routes the merged stream to the AFP printer output queue. No transformation is applied — records are passed through as-is at 797 bytes.
L207DCL.md

The AFP printer is configured as:

FORMDEF=GEN14, PAGEDEF=DOLB3E
DEST=LOCAL, CLASS=S
ROOM='ADF_ND-USPS:DAILY'
Phase 6 — Backups & Date Adjustment
Table

Step

	

What It Does


BACKUP2	GDG backup of SYNC.DTL (domestic, 797 bytes)
BACKUP3	GDG backup of FRG3.DTL (foreign, 797 bytes)
DATEPG7	Reads SYNC records, applies +10 day date adjustment to date fields, expands from 778→807 bytes → PLUS10.DTL
GDGBUILD	GDG backup of PLUS10.DTL
View more
Phase 7 — Conditional Reprint
Table

Step

	

Condition

	

What It Does


DXCBR400	Always runs	Evaluates whether reprint is needed; RC=400 triggers reprint branch
DXCBR7A	RC=400 only	Reads PLUS10 backup, generates new detail records using run date 05/16/2012
DXCBR7B	RC=400 only	Selects specific record ranges (1, 3–5, 7) from new detail → REPRINT.DTL
REPRINT	RC=400 only	Routes selected reprint records to AFP printer (same AFPOUT1 definition)
NULLSTEP	RC≠400	Cleanup placeholder; job ends normally
View more
Record Size Summary Through the Chain
L207DCL Record Size Transformation

Step

	

Program

	

Record Size In

	

...


(upstream)	DXCBD54R	BC3 raw	...
SORT1/SORT2	SORT	778	...
DXCB165U	DXCB165U	778	...
DXCB166U	DXCB166U	787	...
DXCBD24E	DXCBD24E	778	...
DXCBBC3E	DXCBBC3E	778	...
UIMI0754	UIMI0754	790	...
LASRPRNT	IEBGENER	797	...
DATEPG7	DATEPG7	778 (sync)	...
View more
Key Design Notes
Two parallel pipelines converge at LASRPRNT: Domestic records go through all 5 programs; foreign records skip the ZIP/tray steps and go through only DXCBBC3E → UIMI0754
DXCBBC3E is invoked twice in the same job — once for domestic (step DXCBBC3E), once for foreign (step DXCBBC3X) — same program, different input/output files
DXCBD54R is not part of this job — it runs upstream and produces the 778-byte source file. Its role (form formatting, field validation, date conversion) is documented in DXCBD54R.md
DXCB166U's internal tray logic is not available at COBOL-rule level in the knowledge base — the JCL-level description is the only documentation
Would you like to explore any of these areas further?

Upstream BC3E form formatting (DXCBD54R)

The reprint trigger and selection logic

Compare with BC2ER laser job L207DCM

_Citations:_
- Citation 1
- Citation 2
- Citation 1
- Citation 2
- Citation 2
- Citation 4
- Citation 5
- Citation 6
- Citation 7
- Citation 2

## v6-Q3

**Q:** In the daily refund reporting stream, how does LOOPS decide whether a refund payment counts as CASH, an offset, or a write-off?

**A** (11:34):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

The classification logic is well-documented across two programs that serve different reporting contexts. Here's the synthesized picture, drawn primarily from the batch program DXCRD99E (the federal refund reporting extract) and the ETA-227 daily reporting program DXCR227E/DXCR227M.

Where the Classification Happens

The account-code classification is performed in program DXCRD99E during the daily federal refund extract. It reads Segment 09 (refund payment) records from the DB09 Cash/Offset file and assigns each record an Account Code of CASH, OFFSET (CLPY), or WRITE-OFF based on the DB09-REFUND-PAY-TYPE field.
DXCRD99E.md

The ETA-227 daily reconciliation program DXCR227E uses a parallel but slightly different classification to route payments into its Section B report lines (Line 202 = Cash, Line 203 = Offset, Lines 204/205 = Write-off/Waiver).
DXCR227M.md
DXCR227E.md

The Decision Cascade

The classification is a four-step waterfall — each step can override the previous:

Step 1 — Reject Payment Type '06'

If DB09-REFUND-PAY-TYPE = '06', the record is immediately rejected as invalid. It gets an error message (NOT-VALID-OFFSET-MSG) and is routed to the DB89FILE error output. No further classification occurs.
DXCRD99E.md

Step 2 — Initial CASH vs. OFFSET Split

After passing the '06' check, the payment type is evaluated against the known cash types:

Table

Classification

	

Payment Types


CASH	'01', '02', '03', '04', '07', '09', '10', '51', '11', '12'
OFFSET (CLPY)	Everything else that isn't in the CASH list above
View more

Note: DXCR227E uses a slightly different CASH/OFFSET split for its Section B accumulation: pay types 01, 02, 03, 04, 07, 09, 10, 11, 12 → CASH (Line 202); pay types 05, 06 → OFFSET (Line 203). Pay type '51' appears only in the DXCRD99E CASH list.
DXCR227M.md

Step 3 — Override to WRITE-OFF for Payment Type '99'

After the initial CASH/OFFSET assignment, a second check fires: if DB09-REFUND-PAY-TYPE = '99', the Account Code is overridden to WRITE-OFF, regardless of whatever CASH or OFFSET was just assigned.
DXCRD99E.md

Step 4 — Override WRITE-OFF Back to CASH If No Waiver Reason

This is the subtlest rule. If the record was just classified as WRITE-OFF (payment type '99'), the system inspects the Write-Off Waiver Reason Code (DB09-WO-WAIVER-REASON-CODE). If it is blank (spaces), the Account Code is reverted from WRITE-OFF back to CASH. The rationale: without a formal waiver reason, the transaction is treated as a cash collection, not a formal write-off.
DXCRD99E.md

Visual Summary of the Decision Flow
DB09-REFUND-PAY-TYPE
        │
        ├─ = '06' ──────────────────► REJECT → Error File (DB89)
        │
        ├─ IN ('01','02','03','04',
        │      '07','09','10','51',
        │      '11','12') ──────────► Account Code = CASH ─┐
        │                                                    │
        ├─ anything else ───────────► Account Code = OFFSET ─┤
        │                                                    │
        │        ┌───────────────────────────────────────────┘
        │        │
        │        ▼
        │   Pay Type = '99'?
        │        │
        │        ├─ No ──────────────► Keep CASH or OFFSET (done)
        │        │
        │        └─ Yes ─────────────► Override to WRITE-OFF
        │                                     │
        │                    Waiver Reason Code blank?
        │                         │
        │                         ├─ Yes ────► Revert to CASH
        │                         │
        │                         └─ No ─────► Keep WRITE-OFF (done)

How Write-Off / Waiver Records Are Created Upstream

The payment type '99' and the associated waiver reason code are assigned by the CICS online write-off module DXCR041S when a claims examiner processes a write-off or waiver action. The documented waiver reason codes and their payment type assignments are:

Waiver code '06' (Bankruptcy) → Payment Type '66' (not '99')
Waiver codes '01' (Death), '02' (Disability), '03' (Interest), '99' (Full Write-Off / Treasury Authorization) → Payment Type '99'

All write-off/waiver payment segments are created with Payment Source Code '2' (system-generated) and transaction code R040.
DXCR041S-cbl.json

How It Feeds the ETA-227 Report

In program DXCR227E, the classified payments flow into three lines on the Section B reconciliation report:

Line 202 — Recovered: Cash (CASH payments, by fraud/nonfraud and UI/Federal)
Line 203 — Recovered: Offset (OFFSET payments, by fraud/nonfraud and UI/Federal)
Line 204 — Waived (waiver amounts)
Line 205 — Written Off (write-off amounts)

The amounts are further broken out by funding type (Non-Federal columns C-09/C-11, Federal columns C-10/C-12) based on the program code classification (UI, UCFE/UCX, or Combined). For Combined program codes, Extended Benefits (EB) amounts are split 50/50 between Federal and Non-Federal.
DXCR227M.md

Important Caveats
The pay-type-to-account-code mapping is derived from the documented rules in DXCRD99E.md for the federal extract and DXCR227E.md/DXCR227M.md for the ETA-227 daily report. There is a minor documented divergence between the two programs on whether pay type '51' and '05'/'06' map to CASH or OFFSET — confirm with an SME whether both programs are intended to be synchronized or reflect different reporting requirements.
Pay type '66' (Bankruptcy Write-Off) is not explicitly covered in the DXCRD99E classification rules retrieved. It would fall into the "anything else → OFFSET" default unless there is handling not visible in the retrieved extract. This is an open question worth verifying.
The actual values of the waiver reason codes ('01', '02', '03', '06', '99') are documented in DXCR041S-cbl.json; other waiver codes may exist in the operations-maintained CODELOOP VSAM dataset outside the knowledge base.
Would you like to explore further?

Walk me through the full ETA-227 daily report

Explain the DXCR041S write-off/waiver CICS module

Deep research on the refund classification pipeline

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 1
- Citation 2
- Citation 1
- Citation 1
- Citation 4
- Citation 2

## v6-Q4

**Q:** What validations and computations does DXCRD88E apply to refund DB08 records, and how does it classify claims?

**A** (11:36):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

Program DXCRD88E is thoroughly documented in DXCRD88E.md (from the Daily CA-7 v2 space). It's a daily batch reformatter that sits between the raw CDT audit file and the downstream refund report suite (DXERD801–DXERD804). Here is a synthesized walkthrough of its three core functions: validation, computation, and classification.

Program Overview

DXCRD88E reads DB08 (Segment 8 — refund/overpayment) records from the CDTFILE input, applies a gauntlet of validations, computes net outstanding balances, and writes one output record per positive-balance funding category to SEG8FILE (the DB88 layout). Invalid records are routed to DB89FILE with a diagnostic error message.
DXCRD88E.md

Part 1 — Record-Level Validations

Each input record runs through a strict fail-fast cascade. The first validation failure flags the record as bad, skips all remaining checks, and routes it to DB89.

Gate 1: Before/After Byte

The byte must be one of B (Before), A (After), I (Insert), or D (Delete). Any other value → error BEF-AFT-BYTE-MSG → DB89. The byte also sets the transaction sign (BUCKET-SIGN): A/I = +1, B/D = -1.
DXCRD88E.md

Gate 2: Delete Byte Rejection

Even though D is a valid byte, DELETE records are always rejected → error DELETE-BYTE-MSG → DB89.
DXCRD88E.md

Gate 3: Program Code 45 Rejection

Program Code 45 is not eligible for refund processing → error PC45-MSG → DB89.
DXCRD88E.md

Gate 4: Federal Amount Presence Check

If all three Federal amounts due (Fraud, Non-Fraud, Agency Error) are zero, the record is silently skipped — no output, no error. This is the only "soft skip" in the cascade.
DXCRD88E.md

Gates 5–9: Claim Percentage Validations (all bypassed for D15U transactions)
Claim Percentage Validations

\#

	

Validation

	

Applies To

	

...


5	PC 20 Fed/UCFE	Program Code = 20	...
6	PC 30 Fed/UCX	Program Code = 30	...
7	Fed + NonFed Total	All records	...
8	PC 80/83 Pure Federal	Program Code = 80 or 83	...
9	UCX + UCFE ≈ Fed	All except PC 80/83	...
View more
Gate 10: Zero Federal Percent with Non-Zero UCX/UCFE

If Fed% = 0 but UCX% or UCFE% > 0 (and not D15U) → error ZERO-FED-PCT-MSG → DB89.
DXCRD88E.md

Gate 11: Federal Amount vs. 100% Non-Federal Contradiction

If any Federal amount due > 0 but NonFed% = 100% (and not D15U) → error FED-AMT-NO-FED-PCT-MSG → DB89. This catches records that carry federal dollars but declare the claim as entirely non-federal.
DXCRD88E.md

Part 2 — Claim Classification

After passing validations (or even before the percentage checks, right after Gate 3), each record is classified. This is a two-step process:

Step 1 — LOOPS vs. SKELETON:

Program Code Classification

Classification

	

Program Codes


LOOPS (active UI programs)	10, 20, 21, 22, 23, 30, 31, 40, 41, 42, 43
SKELETON (inactive/other)	All other codes
View more

Step 2 — SUSPENSE Override: If Program Code = 99, the classification is overridden to SUSPENSE, regardless of the initial LOOPS/SKELETON assignment.
DXCRD88E.md

Step 3 — Account Code: All records, regardless of classification, receive Account Code = RECEIVABLES.
DXCRD88E.md

The classification indicator (DB88-LOOPS-SKELETON-IND) and account code are cleared to spaces before each record to prevent carry-over.
DXCRD88E.md

Part 3 — Balance Computations and Output

For each valid record, 20 outstanding balances are computed as Amount Due − Amount Paid across eight funding categories, each split by overpayment type (Fraud, NonFraud, Agency Error), plus Fines and Interest:

The 20 Balance Buckets
NFED (NonFederal): Fraud, NonFraud, Agency Error
FED / UCX / UCFE (Federal): Fraud, NonFraud, Agency Error
EB (Extended Benefits): Fraud, NonFraud, Agency Error
FSC (Federal Supplemental Compensation): Fraud, NonFraud, Agency Error
EUB (Extended Unemployment Benefits): Fraud, NonFraud, Agency Error
WFD (Workforce Development): Fraud, NonFraud, Agency Error
FINE (Fines): single balance
INTR (Interest): single balance
Output Record Generation

For each balance that is positive (Amount Due > Amount Paid):

Multiply the balance by the BUCKET-SIGN (+1 or −1) to produce a signed amount
Set the Funding Code and Funding Type
Write one record to SEG8FILE with full claimant identification, transaction details, claim percentages, employer info, and the signed bucket amount
Federal Amount Splitting Logic

The routing of Federal balances depends on Program Code:

Federal Balances
      │
      ├─ PC = 80 or 83 ──────────► Write directly as FED / Fraud|NonFraud|AgencyError
      │
      ├─ D15U + PC in (01,04,08,09,15,16,17,
      │         70,71,76,80,83,84,90) ──► Write directly as FED (bypass split)
      │
      └─ All other PCs ──────────► Split between UCFE and UCX:
                                       UCFE portion = Fed Balance × (UCFE% ÷ Fed%)
                                       UCX  portion = Fed Balance − UCFE portion

                                       Special: PC 30 with UCX% = 0 still writes
                                       the full balance as UCX if no UCFE was allocated

UCFE-as-Percent-of-Federal Ratio

This is the key computation: UCFE% ÷ Federal% (rounded). It's computed once per record during validation and stored for use during the Federal balance splitting.
DXCRD88E.md

Empty Bucket Safety Check

After all funding categories are processed for a valid BEFORE or INSERT record (excluding transaction code D070), the bucket counter must be > 0. If no output records were produced, the program ABENDs with code 800 — this indicates a data integrity problem.
DXCRD88E.md

Per-Record Cleanup

After each record (valid or bad), all 20 balance fields are reset to zero, and the bad-record indicator is cleared to NO before the next record is read.
DXCRD88E.md

Part 4 — Error Record Processing

Bad records go through 1301-BAD-IMAGE-PROC, which:

Multiplies each of the 20 Amount Due fields (not balances) by the BUCKET-SIGN
Formats a DB89 error record with SSN, Program Codes, Claim Dates, Before/After Byte, Transaction Code, Local Office, all four Claim Percentages, and the specific error message
Writes the record to DB89FILE
Caveat

This describes the DXCRD88E reformatting step only. It is one program in the daily refund reporting stream — the output SEG8FILE feeds downstream report programs DXERD801 through DXERD804, which are separate programs not covered in this answer. The arithmetic for the UCFE/UCX split (UCFE% ÷ Fed% ratio, remainder calculation) is derived from the documented business rules in DXCRD88E.md and should be confirmed against the source code if precise rounding behavior matters for test case design.

What would you like to explore next?

Downstream refund report programs

D15U special-case handling details

Test case design for DXCRD88E

_Citations:_
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1

## v6-Q5

**Q:** Job L216DA maintains the alpha (name search) file. What are its inputs, and how does a day's activity end up in the alpha VSAM file?

**A** (11:37):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

Job L216DA is thoroughly documented across L216DA.md (JCL), DXCBD08R.md, DXCBD06R.md, and DXCBD13R.md (all from the Daily CA-7 v2 space). It's a two-job pipeline — L216DA produces the updated flat-file detail, and its successor L216DB rebuilds the VSAM cluster from that detail. Here is the synthesized end-to-end walkthrough.

Purpose

L216DA performs daily Alpha file maintenance. The "Alpha file" is a name-search lookup file — it stores Last Name, SSN, First Name, and City for every claimant so that CICS online programs (e.g. DXCA106S) can browse it for name-based claimant search.
DXCA106S-cbl.json
 Each day, three sources of activity are merged into the existing Alpha content and a new generation of the Alpha detail file is written to tape.
L216DA.md

Inputs

The job consumes five distinct inputs:

L216DA Inputs

\#

	

DD Name

	

Dataset

	

...


1	NEWCLM	LAK2LDXP.L213DA.DLY.NEWCLAIM.DTL(0)	...
2	CHGCLM	LAK2LDXP.L213DA.CLMMAINT.DTL	...
3	DABSCLM	LAK2LPAP.TBACKUP.D2LID100.SRTFL.DTL(0)	...
4	TABLE	LAK2LDXP.VSAM.CODES.CLUSTER	...
5	SYSIN (DATECARD)	LAK2LDXP.PROD.CNTLLIB(DATECARD)	...
View more

Plus the existing Alpha VSAM cluster itself, read mid-job:

LAK2LDXP.VSAM.ALPHA.CLUSTER — the current Alpha name-search VSAM KSDS (23,465-byte grouped records, 29-byte key)
Step-by-Step Flow — How a Day's Activity Reaches the Alpha VSAM

The job has seven steps executed in strict sequence (every step has COND=(0,NE) — any non-zero return code halts the chain).
L216DA.md
L216DA.txt

Step 1 — REPRO1A (IDCAMS): Back Up the Daily Sort File

Copies the current generation of the daily sorted detail file (D2LID100.SRTFL.DTL(0)) into a new GDG generation (L216DA.D2LID100.SRTBKP.DTL(+1)) as a safety backup before any processing begins. Records are 1,144 bytes FB.

Step 2 — DXCBD08R (COBOL): Merge Three Activity Sources into 55-Byte Alpha Records

This is the reformatting and merge step. Program DXCBD08R reads all three input files sequentially — New Claims, Change Claims, then DABS Claims — and for each record:

Parses the claimant name by splitting on the / delimiter → Last Name / First Name
Parses the address by splitting on / → Street / City (New Claims and DABS use this; Change Claims provide the city directly in field CM-CITY-TO)
Cleanses all text fields — scans Last Name, First Name, and City character by character, retaining only alphabetic letters and spaces, stripping everything else, and ensuring no leading blank
Tags each record with a claim-type indicator:
A = New Claim
C = Change Claim
B = DABS Claim
Writes a 55-byte standardized record (Last Name, SSN, First Name, City, Claim Type) to the temporary merged file &&MERGE

Output: &&MERGE — a single flat file containing the day's combined alpha-format transactions, 55 bytes FB.

Step 3 — REPRO1 (IDCAMS): Unload the Existing Alpha VSAM Cluster

Extracts all records from LAK2LDXP.VSAM.ALPHA.CLUSTER to a temporary sequential file &&ALPHA, skipping the first record (a header/control record). Output records are 23,465 bytes FB — each one is a grouped record holding up to 434 person entries.
L216DA.md

Step 4 — DXCBD06R (COBOL): Split Grouped VSAM Records into Individual 54-Byte Records

Program DXCBD06R — the "Alpha Lookup File Splitter" — reads each 23,465-byte grouped record and iterates through up to 434 person-entry slots. For each slot where the SSN is non-blank, it extracts Last Name, SSN, First Name, and City and writes a 54-byte flat record to &&SPLIT. A blank SSN at any slot signals the end of valid entries in that grouped record.
DXCBD06R.md

Output: &&SPLIT — the entire existing Alpha file exploded into individual 54-byte person records. The input &&ALPHA is consumed and deleted.

Step 5 — SORT1: Sort the Daily Merged Transactions

Sorts &&MERGE (55-byte records from Step 2) in ascending order by the 9-byte SSN at position 21 (Zoned Decimal). Output: &&SORTA → renamed to DAILYF for Step 7.

Step 6 — SORT2: Sort the Existing Alpha Records

Sorts &&SPLIT (54-byte records from Step 4) in ascending order by the 9-byte SSN at position 21 (Zoned Decimal). Output: &&SORTB → renamed to OLDALPHA for Step 7.

Step 7 — DXCBD13R (COBOL): Reconcile and Produce the Updated Alpha Detail

This is the core merge step. Program DXCBD13R performs a classic sorted-file merge on the two SSN-sorted inputs:

DXCBD13R Merge Logic

Condition

	

Action


Daily SSN < Old SSN	Daily record is a new claim — write it to NEWALPHA (insert)
Daily SSN = Old SSN	Daily record replaces the old record — write daily to NEWALPHA (update)
Old SSN < Daily SSN	No daily update for this claim — write old record unchanged to NEWALPHA (passthrough)
Duplicate daily SSNs	Keep only the last daily record for a given SSN (later record overwrites earlier)
Daily file exhausted	Write all remaining old records unchanged
Old file exhausted	Write all remaining daily records, resolving any pending duplicates
View more

Output: LAK2LDXP.L216DA.ALPHA.DTL(+1) — a new GDG generation on tape (54-byte FB, EXPDT=99000 — never expires). This is the updated Alpha detail flat file.
L216DA.md

From Flat File to VSAM — Job L216DB

Job L216DA does not update the VSAM cluster directly. The successor job L216DB picks up the tape file L216DA.ALPHA.DTL(0) and:

Deletes and redefines LAK2LDXP.VSAM.ALPHA.CLUSTER (KSDS, 23,465-byte records, 29-byte key at position 0)
Seeds it with a blank initial record
Sorts the Alpha detail by the first 20 characters (Last Name) then the next 9 characters (SSN)
Runs program DXCBD04R to load the sorted records back into the VSAM cluster, re-packing individual 54-byte records into the grouped 23,465-byte (434-entries-per-record) VSAM format

After L216DB completes, the VSAM Alpha cluster is fully refreshed and available for CICS online name-search browsing (e.g., via DXCA106S).
DXCA106S-cbl.json

Key Design Points
Restart criticality = 1 (highest). The JCL header documents that any step from REPRO1 through DXCBD13R restarts at DXCBD08R — the entire merge chain re-runs from scratch.
L216DA.txt
Record sizes differ by one byte: daily transactions are 55 bytes (includes the claim-type indicator A/C/B), while existing alpha records are 54 bytes. DXCBD13R handles both.
The VSAM rebuild is destructive: L216DB DELETE/DEFINEs the cluster every day, so the VSAM is always a complete rebuild, never an in-place update.
A JCL comment notes a future placeholder for backing up a TDI-FLI Salesforce/MuleSoft modernization input that will be concatenated into the DABSCLM DD.
Caveat

This describes what the knowledge base documents for L216DA and its immediate successor L216DB. The upstream jobs that produce the NEWCLM, CHGCLM, and DABSCLM inputs (L213DA, D2LID100) are separate job streams not fully covered here. The program DXCBD04R (the VSAM loader in L216DB) is referenced in the JCL documentation but its COBOL source analysis was not retrieved, so the exact re-packing logic from 54-byte flat records into 434-per-grouped-record VSAM format is described from the JCL-level documentation, not from program source.

What would you like to explore next?

How does DXCA106S browse the Alpha file?

What does job L213DA produce?

How does DXCBD04R repack records into the VSAM?

_Citations:_
- Citation 1
- Citation 2
- Citation 2
- Citation 3
- Citation 2
- Citation 5
- Citation 2
- Citation 1
- Citation 3

## v6-Q6

**Q:** The automated handbook update job sorts IB13 updates by state and section within date and time before applying them. Why does that order matter, and what does the update program do with each record?

**A** (11:39):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

This is thoroughly documented across L2AHD13.txt (JCL), UIPBHB01.md, and UIPBHB02.md — all from the Daily CA-7 v2 space. Here is the synthesized end-to-end walkthrough.

The Job: L2AHD13 — Automated Handbook Update

This four-step job reads incoming IB13 interstate messages that carry updated Handbook text, selects the ones addressed to the state's Handbook receiver, sorts them so the most recent update for each state+section is processed last, and then applies them to the Automated Handbook VSAM file (UIFLHB00). Restart criticality is 1 (highest).
L2AHD13.txt

Why the Sort Order Matters

The JCL narrative states the rationale explicitly: "The file is sorted on state and section within date and time to ensure that the most recent updates will be processed last."

Multiple IB13 messages can arrive on the same day for the same state and section — for example, a correction followed by a re-correction. Because the update program (UIPBHB02) processes records sequentially and deletes-then-writes for each record, whichever record it processes last for a given state+section+record-number becomes the final state of the Handbook VSAM entry. By sorting State → Section → Date → Time in ascending order, the pipeline guarantees that for any given handbook location, the chronologically latest IB13 overwrites all earlier ones, and the Handbook file always reflects the most recent content.
UIPBHB01.md
UIPBHB02.md

Step-by-Step Job Flow
Step 1 — VFY01 (IDCAMS VERIFY)

Verifies that the IB13 VSAM file LAK2LDXP.PROD.VSAM.INFL1300.CLUSTER is in a consistent state. If a prior job abended with the file open, VERIFY resets its catalog markers so it can be safely read and written.
L2AHD13.txt
L2AHD13.md

Step 2 — UIPBHB01 (COBOL): Select and Tag Qualifying IB13 Records

Program UIPBHB01 browses the IB13 VSAM file for records addressed to the state's Handbook receiver. For each qualifying record it:

Filters — only processes records of type IB13I with Receiver/Sender ID = .HANDBOOK for the configured state postal code
Skips already-processed — any record where IB13-BATCH-SWITCH = 'Y' is skipped (it was handled in a prior run)
Extracts State and Section — examines the first text line of the IB13 message. If it matches the section-header pattern ***** XXY ***** (where XX = state, Y = section), state and section come from the header. Otherwise, they come from fixed key-level positions in the first line
Builds a sort key — prepends each record with a composite key:
UIPBHB01 Sort Key Layout

Position

	

Length

	

Content

	

...


1–3	3	State + Section (XXY)	...
4–10	7	Century (2) + Julian Year (2) + Julian Day (3)	...
11–16	6	Creation Time	...
17–4785	4769	Full IB13 message record (payload)	...
View more

The Gregorian creation date is converted to Julian via the 8000-GREG-CONVERT routine, and century is determined by a Y2K pivot (year < 50 → '20', else '19').
UIPBHB01.md

Writes the 4,785-byte record to temporary file &&TEMP
Step 3 — SORT01 (DFSORT)

Sorts &&TEMP into &&SORTED with this SORT card:

SORT FIELDS=(1,3,A,4,7,A,11,6,A),FORMAT=CH


This means: ascending on positions 1–3 (State+Section), then 4–10 (Century+Julian date), then 11–16 (Time). The effect is that for any given State+Section, the oldest IB13 is first and the newest is last.

Note: the JCL also contains a commented-out prior SORT card (4,7,A,11,6,A,1,3,A) — the current production version sorts State+Section first.
L2AHD13.txt

Step 4 — UIPBHB02 (COBOL): Apply Updates to the Handbook VSAM

This is the core update program. It opens four files in I-O mode:

UIPBHB02 File Access

DD Name

	

Dataset

	

Mode

	

...


INFLTEMP	&&SORTED	Input	...
UIFLHB00	LAK2LDXP.PROD.VSAM.UIFLHB00.CLUSTER	I-O	...
UIFLHB01	LAK2LDXP.PROD.VSAM.UIFLHB01.CLUSTER	I-O	...
INFL1300	LAK2LDXP.PROD.VSAM.INFL1300.CLUSTER	I-O	...
View more

For each sorted record, UIPBHB02 does the following:

What UIPBHB02 Does with Each Record

1. Map to IB13 layout — Strips the sort key prefix and loads the IB13 message payload into working storage. Resets the line counter to 1.

2. Detect record type — Examines the first text line:

If it matches ***** XXY ***** → this is a new section header (a section boundary)
Otherwise → this is a continuation record for the current section

3. Handle section boundaries:

First section header ever: Save the IB13 key, copy the header line into the Handbook record buffer, turn off the first-time indicator, advance the line counter
Subsequent section header: The previously assembled Handbook record is complete → set its HB-NEXT-RECORD-SWITCH = 'N' (no continuation) and write it to the Handbook VSAM file. Then begin the new section
Continuation record: The current Handbook record has more data coming → set HB-NEXT-RECORD-SWITCH = 'Y' and write the current segment to the Handbook VSAM file

4. Extract the Handbook VSAM key — The key line is the 2nd text line for new sections or the 1st line for continuations. The key is a 5-character composite XXYZZ (State XX + Section Y + Record Number ZZ)

5. Delete-then-replace the Handbook record:

DELETE the existing record with that key from UIFLHB00. Status 23 (not found) is acceptable — the IB13 may be adding a brand-new section
DELETE the corresponding Handbook In Progress (HIP) record from UIFLHB01 with the same key — this cleans up any pending-update tracking. Not-found is acceptable here too

6. Initialize the new Handbook record:

Clear HB-LAST-EXPORT-DATE to zeroes (not yet exported)
Set HB-LAST-UPDATE-DATE to today's date (formatted via the FAPCONF2 conversion routine)
Default HB-NEXT-RECORD-SWITCH = 'N'

7. Copy IB13 text lines — Iteratively copy each remaining IB13 text line into the Handbook record buffer. The line position is offset by −1 to account for the key line that was consumed but not written as content

8. Write the assembled Handbook record to UIFLHB00 with the line count. Display 'HANDBOOK VSAM RECORD UPDATED - ' + key

9. Mark the source IB13 record as processed:

Re-read the IB13 record from INFL1300 using the saved key
Set IB13-READ-SWITCH = 'Y' and IB13-BATCH-SWITCH = 'Y'
Stamp it with today's date in Julian format (century + year + day-of-year)
Rewrite it — this permanently flags it so the downstream IB13 batch purge program will delete it on its next run, and UIPBHB01 will skip it on its next run

10. Re-read the current IB13 record using the saved "next" key to restore working context for the next iteration

11. At end-of-file: If any records were processed, write the final pending Handbook record with NEXT-RECORD-SWITCH = 'N'

Summary: Why the Sort Guarantees Correctness
Sort Order And Its Effect On Processing

Sort Component

	

Position

	

Effect


State + Section (primary)	1–3	Groups all updates for the same handbook location together
Century + Julian Date (secondary)	4–10	Within a location, orders by date oldest-first
Creation Time (tertiary)	11–16	Within the same date, orders by time oldest-first
Combined effect	—	For each XXYZZ key, the last record UIPBHB02 processes is the most recent. Since it deletes-then-writes, the final Handbook VSAM entry always holds the latest content
View more
Caveat

This describes the three programs documented in the knowledge base: UIPBHB01, UIPBHB02, and the L2AHD13 JCL. The IB13 inter-state messaging system that produces the incoming IB13 records, and the downstream IB13 batch purge program that deletes processed records, are referenced but their source is not in the held knowledge base. The FAPCONF2 date conversion routine called by UIPBHB02 is also referenced by name only — its source was not retrieved.

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 1
- Citation 4
- Citation 2
- Citation 1

## v6-Q7

**Q:** Which daily job produces the employer daily charge report, which records make it onto the report, and how is the report organized?

**A** (11:40):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

The employer daily charge report is not a single job but a three-job pipeline: L204DF1 → L205DJ → L206DL. Here's the full end-to-end walkthrough, synthesized from multiple source documents.

Where the Charge Data Originates — L204DF1

Programs DXCBD40E (check payments) and DXCBD50E (direct deposits) process the day's UI payment transactions and produce — among many other outputs — the Daily Charge detail file LAK2LDXP.L204DF.DLCHARGE.DTL as a GDG. This file contains 223-byte employer charge segment records for every payment processed that day.
L204DF1.md

Step 1: Extraction and Classification — Job L205DJ

This is the core employer charge extraction job. Its narrative states: "This job reads the daily EMP charge segments and extracts records for files CHGRPT, FEDRPT, B187REV, SLCTCWC and UC53." It has six steps :
L205DJ.txt
L205DJ.md

Which records make it onto the report?

Step DXCBD90E — reads the GDG charge file, filters out non-chargeable employers (based on void flags 6, 7, or 8, non-charge FEINs, and affidavit-flagged records), writes those to NONCHARG.DTL, and passes all records forward.
DXCBD90E.md

Step SYNCSRT1 — sorts the charge file with:

SORT FIELDS=(1,5,PD,A,6,2,PD,A,8,4,BI,A)


This arranges records by employer account/period (positions 1–5), then charge type/classification (positions 6–7), then sequence/amount (positions 8–11).
L205DJ.txt
L205DJ.md

Step DXCBD43E — the main classification program. It reads each sorted record from LOOPCD04 and applies four application modules. The critical filtering rule: only Segment 4 records (the charge segment) are eligible for charge and penalty accumulation. Records from other segments bypass charge totals entirely.
DXCBD43E.md

For each qualifying Segment 4 record, DXCBD43E:

Validates the program code and transaction code against the CODES reference table
Looks up the employer address from EMPEXADD VSAM
Separates charge amounts by void status (EC-VOID-FLAG = '0' → non-voided; any other value → voided) and accumulates input/output running totals for both charges (AMT-EMP-CHARGE) and penalties (EMPLOYER-PENALTY-CHARGE)
Categorizes each charge by employer type: UI, UCFE, UCX, General Fund, EUB, WFD, TUC, TUCX, FSC, etc.
Writes a 54-byte summary record to the CHGRPT.DTL file for each charge category
The CHGRPT Record Layout
CHGRPT Record Layout (54 Bytes)

Position

	

Length

	

Format

	

...


1	2	Numeric	...
3	24	Alpha	...
27	3	Packed	...
30	6	Packed (2 dec)	...
36	3	Packed	...
39	6	Packed (2 dec)	...
45	6	Packed (2 dec)	...
51	4	Packed	...
View more

This layout comes directly from DXEBD44R.txt
DXEBD44R.txt
.

Step 2: The Printed Report — Job L206DL

Job L206DL is the final reporting job. Its JCL narrative states: "Daily Job Employer Charge Control Report and EB Employer Charge Report." Restart criticality is 1 (highest).
L206DL.txt
L206DL.txt

Step DXEBD44R (Easytrieve)

This program reads the CHGRPT.DTL produced by DXCBD43E, sorts it by CHGTYPE, then dispatches each record to the appropriate sub-report based on its charge type number :
DXEBD44R.txt

How the Report Is Organized

DXEBD44R produces at least six separate printed sub-reports, each covering a range of charge types :
DXEBD44R.txt

DXEBD44R Report Sub-Reports By Charge Type

Report

	

Title

	

Charge Types Included

	

...


RPT1	Daily Employer Charge Control Report (No EB)	1–10 (with non-blank description)	...
RPT2	Daily Extended Benefits Charge Control Report	11–12	...
RPT3	Daily Control Report — Conversion Employer	13	...
RPT4	Daily E.U.B. Charge Control Report	14–17	...
RPT5	(FSC / TUC-related)	18–24, 29–42	...
RPT6	Non-Charge Types Report	25–28	...
View more

Each sub-report has the same column structure :
DXEBD44R.txt

Report Column Layout

Each sub-report prints a standard header block:

PREPARED [SYSDATE] AT DOL DATA CENTER    NEW JERSEY DEPARTMENT OF LABOR
LOCAL OFFICE 999                          DIVISION OF UI DI          REPORT NO  DXEBD44R-RPT-001
                    DAILY EMPLOYER CHARGE CONTROL REPORT (NO EB)
                                     AS OF [DAILY-DATE]

             FUND        DEBIT    DEBIT      CREDIT   CREDIT    NET AMOUNT OF   TOTAL REC
                          CNT     DOLLARS      CNT    DOLLARS      DOLLARS         CNT


For each charge type that has records, one detail line is printed showing:

Fund (the CHGDESCRP description)
Debit Count and Debit Dollars
Credit Count and Credit Dollars
Net Amount of Dollars (NETDOL)
Total Record Count

At the end of each sub-report, a Totals line is printed summing all categories within that report.

Net Dollar Accumulation for Reconciliation

In addition to printing, DXEBD44R saves the NETDOL value from each charge type into a working storage variable (e.g., WL1 for type 1, WL2 for type 2, etc.) and also reads from the RECONCIL VSAM file. This allows the charge control totals to be cross-referenced against the reconciliation file.
DXEBD44R.txt

Step DXEBD49R

The second step processes the CETA Employee detail file (CETAEMP.DTL) also produced by DXCBD43E.
L206DL.txt
L206DL.txt
 This is a separate EB Employer Charge Report.

Caveat

This describes the pipeline as documented across L204DF1.md, L205DJ.txt/L205DJ.md, DXCBD90E.md, DXCBD43E.md, L206DL.txt/L206DL.md, and DXEBD44R.txt. The intermediate upstream programs DXCBD40E and DXCBD50E also produce their own Reports 1A–1J (the individual "LOOPS Daily Employer Charge Report" for Intrastate, Interstate, UCFE 100%, NJ UCFE, etc.) as part of L204DF1 payment processing — those are a parallel set of employer charge reports embedded in the check register job, not the dedicated charge control reports produced by L206DL.
DXCBD40E.md
DXCBD50E.md

What would you like to explore next?

Charge type classification logic in DXCBD43E

The inline employer charge reports from the payment processing job

Downstream processing of the other L205DJ output files

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 2
- Citation 3
- Citation 5
- Citation 6
- Citation 7
- Citation 8
- Citation 6
- Citation 6
- Citation 6
- Citation 6
- Citation 7
- Citation 8
- Citation 9
- Citation 10

## v6-Q8

**Q:** In job L213DC, where do the error records from the DB08 reformat program (DXCRD88E) actually land, and is there anything surprising about it?

**A** (11:42):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

This is a great question — and yes, there's something genuinely surprising here. Let me walk through what the source documents reveal.

What DXCRD88E Thinks It's Doing

At the COBOL program level, DXCRD88E opens three files :
DXCRD88E.md

CDTFILE — input (sorted Segment 8 reference records)
SEG8FILE — valid output (208-byte reformatted refund records)
DB89FILE — error output (159-byte error records for rejected input)

When a record fails any validation check — invalid Before/After Byte, a DELETE record, Program Code 45, etc. — the program signs all 20 refund amount-due fields with the bucket sign, formats a DB89-REFERROR record containing the SSN, program codes, claim dates, transaction code, local office, all four claim percentages, and the specific error message, and writes it to DB89FILE.
DXCRD88E.md
 The record is then re-initialized, and it never touches SEG8FILE.

So from the COBOL's perspective, error records go to a logical file called DB89FILE.

Where They Actually Land — The Surprise

Now look at the JCL for the DXCRD88E step in L213DC.txt
L213DC.txt
 :

jcl

//*DB89FILE DD  DSN=LAK2LDXP.L213DC.DB98FILE.DTL,
//DB89FILE DD  DSN=LAK2LDXP.L213DC.DB98FIL.DTL,DISP=(NEW,CATLG,DELETE),
//             UNIT=SYSALLDA,
//             DCB=(LRECL=159,BLKSIZE=23373,RECFM=FB,BUFNO=20),
//             SPACE=(CYL,(250,250),RLSE)

The DD name is DB89FILE, but the physical dataset it points to is LAK2LDXP.L213DC.DB98FIL.DTL — a DB98 file, not a DB89 file. The commented-out line above it even shows the earlier, longer name DB98FILE.DTL.

The Cross-Wiring, Visualized
DXCRD88E / DXCRD99E DD-To-Dataset Mapping

Program

	

DD Name in COBOL

	

Physical Dataset in JCL

	

...


DXCRD88E (Segment 8)	DB89FILE	LAK2LDXP.L213DC.DB98FIL.DTL	...
DXCRD99E (Segment 9)	DB89FILE	LAK2LDXP.L213DC.DB89FIL.DTL	...
View more

Both programs use the same DD name (DB89FILE) for their error output, but the JCL maps them to different physical datasets — Segment 8's errors go to DB98FIL.DTL, while Segment 9's errors go to DB89FIL.DTL.
L213DC.txt

What Happens Downstream

At the end of the job, step REPRA262 archives both files into GDGs :
L213DC.md

jcl

REPRO INFILE(DB89IN) OUTFILE(DB89OUT)    ← DB89FIL.DTL → DB89FILE.DTL(+1)
REPRO INFILE(DB98IN) OUTFILE(DB98OUT)    ← DB98FIL.DTL → DB98FILE.DTL(+1)

So DXCRD88E's "DB89" error records are archived under the DB98FILE GDG, and DXCRD99E's error records are archived under the DB89FILE GDG.

There's Also a Second Error Output

In addition to the DB89FILE sequential file, both programs also write to D00RFILE, which the JCL maps to SYSOUT=Z — a printed exception report.
L213DC.txt
L213DC.md
 So there are actually two error destinations:

D00RFILE → SYSOUT=Z (printed report for business review)
DB89FILE → DB98FIL.DTL (permanent sequential file, archived to GDG)
Why This Is Surprising

The naming creates a genuine confusion risk:

A developer reading the COBOL source sees records written to "DB89FILE" and structures named DB89-REFERROR — they'd naturally assume the physical output is a "DB89" dataset.
But the JCL silently redirects it to a "DB98" dataset. The only clue is a commented-out line in the JCL.
The job documentation (L213DC.md) itself reflects this by describing DXCRD88E's output as "a DB98 file (DB98FIL.DTL)" — the JCL mapping is authoritative, the COBOL DD name is just a logical alias.
L213DC.md

If you were debugging an error record from Segment 8 processing and went looking in the DB89 GDG, you'd be looking in the wrong place — those are Segment 9's errors. Segment 8's errors live in the DB98 GDG.

Caveat: This analysis is synthesized from L213DC.txt, L213DC.md, and DXCRD88E.md. Whether this cross-naming was intentional (perhaps "DB98" stands for "DB-08 error" using a different convention) or is an accumulated artifact of decades of maintenance is not documented. An SME who was present for the original design would know the naming rationale.

What would you like to explore next?

How does the Segment 9 error handling in DXCRD99E compare?

What specific validations trigger a DB89 error record?

Walk me through the entire L213DC job flow

_Citations:_
- Citation 1
- Citation 1
- Citation 2
- Citation 2
- Citation 3
- Citation 2
- Citation 3
- Citation 3
