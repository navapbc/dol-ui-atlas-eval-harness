# 2026-09-01_1341_quick_playwright_v6

- **Backend:** quick (transport: playwright)
- **Bank:** v6 (`question_sha256` bc49a835de4a…)
- **Agent:** engineering_onboarding_specialist (`093ac4e3-0712-481e-af95-9ddc5e4fc734`)
- **Conversation:** `abc79bfd-2f29-46c7-acd8-64b9c02958ca`
- **Model:** Advanced
- **Started:** 2026-09-01 13:31
- **Finished:** 2026-09-01 13:41
- **Status:** complete
- **Questions asked:** 8, answered: 8

## v6-Q1

**Q:** Walk me through the daily bank reconciliation job L204DF2: what does it produce, and how do check records get from the daily register to the bank files?

**A** (13:32):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

Here's a comprehensive walkthrough of job L204DF2, drawn from the JCL documentation in the Daily CA-7 space. The JCL header describes it as: "THIS DAILY JOB PRINTS THE DAILY BATCH REGISTER AND BANK FILES." The job has restart criticality 9 (high).
L204DF2.md
L204DF2.txt

What L204DF2 Produces

The job produces these key permanent output files :
L204DF2.md

Table

Output Dataset

	

Description

	

Storage / Retention


LAK2LDXP.L204DF.RECON.ACC2528.DTL	Sorted reconciliation detail — O-Category (Acct 2528)	Disk, catalogued
LAK2LDXP.L204DF.RECON.ACC2536.DTL	Sorted reconciliation detail — B-Category (Acct 2536)	Disk, catalogued
LAK2LDXP.L204DF.RECON.ACC0987.DTL	Sorted reconciliation detail — T-Category (Acct 0987)	Disk, catalogued
LAK2LDXP.L204DF.RECON.ACC0499.DTL	Sorted reconciliation detail — E-Category (Acct 0499)	Disk, catalogued
LAK2LDXP.L204DF.BNKFLDTE.DTL(+1)	Date-enriched bank records (88-byte, GDG)	Tape
LAK2LDXP.L204DF.RECNBKP2.DTL(+1)	Consolidated backup of all 4 account files	Tape, 120-day retention
LAK2LDXP.L2BPBNK1.CHECKS.ISSUED.DTL(+1)	Checks Issued file — sorted, deduplicated, 39-byte records	GDG
LAK2LDXP.L204DF.ERROR.DISK.DTL	Unmatched/error records from bank matching (133-byte print-line)	Disk
LAK2LDXP.L204DF.ERROR.FICHE.DTL	Error records archived to microfiche tape	Tape, 30-day retention
LAK2LDXP.L204DF.RECNBKP2.DLY.BCKUP(+1)	Permanent daily backup of consolidated recon	Tape, permanent (EXPDT=99000)
View more
Step-by-Step Job Flow
Phase 1: Cleanup (PREPARE)

The job starts by unconditionally deleting six prior-run files (intermediate recon, error disk, and the four account detail files) to guarantee a clean processing slate.
L204DF2.md

Phase 2: Ingest and Filter (SORTA → BNKFLMOD)
SORTA — Copies the entire Big Record Detail file (BIGREC.DTL, 80-byte records) verbatim into a temporary work file &&RECONCIL. This work file is used by two separate downstream paths.
L204DF2.md
BNKFLMOD — Filters &&RECONCIL to extract only "Old Account" bank records, writing them to OLDACCT.BNKREC.DTL.
L204DF2.md
Phase 3: Date Enrichment and Categorization (BNKFLDTE → UIBNKDAT)
BNKFLDTE — Reads OLDACCT.BNKREC.DTL plus the DATECARD control card and appends 8 bytes of date-related fields, expanding each record from 80 → 88 bytes. Output goes to GDG BNKFLDTE.DTL(+1) on tape.
L204DF2.md
UIBNKDAT — Reads the same OLDACCT.BNKREC.DTL with DATECARD and routes each record into exactly one of four category streams based on bank account type :
L204DF2.md
O → &&BANKO → Account 2528
B → &&BANKB → Account 2536
T → &&BANKT → Account 0987
E → &&BANKE → Account 0499
Phase 4: Sort and Persist Bank Files (SORTO/B/T/E → REPRO4 → BACKUPs)
SORTO / SORTB / SORTT / SORTE — Each temp category file is sorted ascending by the first 20 characters (account key) and written to its permanent reconciliation detail file (e.g., RECON.ACC2528.DTL).
L204DF2.md
REPRO4 — Consolidates all four account files (in order: 2528 → 2536 → 0987 → 0499) into a single tape GDG backup (RECNBKP2.DTL(+1), 120-day retention).
L204DF2.md
BACKUP1–4 — Each of the four account files also gets its own individual GDG backup on disk. These execute unconditionally.
Phase 5: Bank Matching (SORT1 → BNKFLBLD → REPRO5)
SORT1 — Goes back to &&RECONCIL and filters it to only records where positions 71–80 contain account number 0001273518 or 0001273507.
L204DF2.md
BNKFLBLD — Matches those filtered records against the BANKMTCH VSAM cluster. Any records that fail matching are written to ERROR.DISK.DTL (133-byte print-line format).
L204DF2.md
REPRO5 — Backs up the BANKMTCH VSAM cluster to tape (30-day retention).
L204DF2.md
Phase 6: Checks Issued File Build (BUILDOUT → SORTD)

This is the path that answers how check records get from the daily register to the bank files :
L204DF2.md

BUILDOUT — Reads the full BIGREC.DTL (the same "Big Record" daily register) and transforms each record into a standardized 39-byte checks-issued output record, writing to temp file &&OUTSTD.
SORTD — Sorts those 39-byte records in ascending order across the entire record content and removes exact duplicates (SUM FIELDS=NONE). The deduplicated result is written to a new GDG generation of LAK2LDXP.L2BPBNK1.CHECKS.ISSUED.DTL(+1).

In short: BIGREC.DTL → program BUILDOUT (standardize to 39 bytes) → SORT (sort + dedup) → CHECKS.ISSUED.DTL GDG.

Phase 7: Cleanup, Archival, and Final Backup
REPRO6 — Backs up the payment record file (PAYREC.DTL) to a GDG on disk.
L204DF2.md
IEFBR14A — Deletes the spoiled-check file (SPOILCHK.DTL) if all prior steps succeeded; preserves it if anything failed.
L204DF2.md
REPRO8 — Archives ERROR.DISK.DTL to microfiche tape (ERROR.FICHE.DTL, 30-day retention) — but only if step REPRO6 succeeded.
L204DF2.md
REPRO9 — Copies the consolidated RECNBKP2.DTL to a permanently retained daily backup tape (RECNBKP2.DLY.BCKUP(+1), EXPDT=99000) — but only if all prior return codes ≤ 4.
How Check Records Flow: Daily Register → Bank Files

To zoom in on your specific question, the path is a two-step transformation inside L204DF2 :
L204DF2.md

The daily register data arrives as LAK2LDXP.L204DF.BIGREC.DTL (80-byte records).
Program BUILDOUT reads BIGREC.DTL and builds a standardized 39-byte output record per check to temp file &&OUTSTD.
The SORTD step sorts &&OUTSTD ascending across all 39 bytes and eliminates exact duplicates.
The result is written as a new generation of the Checks Issued Detail GDG (LAK2LDXP.L2BPBNK1.CHECKS.ISSUED.DTL(+1)), which is the bank-ready file.

Important caveat: This describes the BUILDOUT → SORTD extract/transform path within L204DF2. The upstream process that populates BIGREC.DTL and the downstream consumer of CHECKS.ISSUED.DTL are not documented in this job's JCL — they would be covered by predecessor and successor jobs in the daily CA-7 schedule.

What would you like to explore next?

Trace the predecessor job that feeds BIGREC.DTL

Trace the successor job that reads CHECKS.ISSUED.DTL

Dive into program-level details (BUILDOUT, BNKFLBLD, UIBNKDAT, etc.)

See the full L204DF daily schedule sequence

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
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1

## v6-Q2

**Q:** How are the daily BC3E claimant forms prepared for laser printing in job L207DCL, and what does each program in the chain do to the record?

**A** (13:34):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

Here's a complete walkthrough of how job L207DCL prepares BC3E claimant forms for laser printing. This is synthesized from the JCL source (L207DCL.txt), job-level business rules (L207DCL.md), and the individual COBOL program analyses (DXCB165U.md, DXCB166U.md, DXCBD24E.md, DXCBBC3E.md, UIMI0754.md) in the Daily CA-7 space.
L207DCL.txt
L207DCL.md
DXCB165U.md
DXCB166U.md
DXCBD24E.md
DXCBBC3E.md
UIMI0754.md

The JCL narrative states: "THIS JOB PRODUCES THE FOLLOWING REPORT: PRINTS NEW BC3E FORMS FOR THE CLAIMANT ON LASER." Restart criticality is 1 (low — force complete when STEP04 returns RC 4, meaning no data). The AFP output is directed to the USPS Daily print bin (ADF_ND-USPS:DAILY) using FORMDEF GEN14 and PAGEDEF DOLB3E.

Overview: Two Parallel Pipelines

The job splits the input into Domestic and Foreign streams, transforms each independently, then merges them for a single laser print output. Each pipeline adds the same enrichments (key field + DB2 sync code) but through separate step names.

Phase 1 — Pre-Processing (Steps VERIFY → STEP04)
Table

Step

	

Program

	

What It Does


VERIFY	IDCAMS	Verifies the LAK2LDXP.VSAM.CODES.CLUSTER integrity. If this fails (RC≠0), all subsequent COND=(0,NE) steps are skipped.
BACKUP1	IDCAMS REPRO	Backs up the source file MAIL.L207DC2.DATA.DTL (778-byte FB records) into GDG MAIL.L207DC2.DATA.BCKUP(+1).
PREPARE1	IEFBR14	Deletes 9 intermediate files from any prior run to guarantee a clean slate.
STEP04	IEBPTPCH	Prints the first record of the source file (STOPAFT=1) so operations can visually confirm the file is readable and populated. RC 4 here means empty input — the JCL header says to force-complete.
View more
Phase 2 — Split into Domestic / Foreign (Steps SORT1, SORT2)

Both sorts read the same source file MAIL.L207DC2.DATA.DTL (778-byte records):

SORT1 — INCLUDE COND=(342,5,CH,EQ,C'00000') → Records with ZIP = 00000 at positions 342–346 are routed to MAIL.L207DCL.FRGN.DTL (the Foreign stream).
SORT2 — OMIT COND=(342,5,CH,EQ,C'00000') → All other records (non-zero ZIP) are routed to MAIL.L207DCL.DATA.DTL (the Domestic stream).

Both files retain the original 778-byte LRECL. No sort key is applied — records are copied in their original sequence.

Phase 3 — Domestic Pipeline (5 Programs)

This is the main transformation chain, each program adding or correcting specific fields before the record is print-ready:

1. DXCB165U — Save ZIP Codes (778 → 787 bytes)
Input: MAIL.L207DCL.DATA.DTL (778 bytes)
Output: MAIL.L207DC3.DATA.DTL (787 bytes)
What it does: Copies the full 778-byte laser output record to the output structure, then extracts the 5-digit ZIP code (BC3L-ZIP-END1) and 4-digit ZIP+4 extension (BC3L-ZIP-END4) from the body of the record and appends them as the last 9 bytes of the output record. This "saves" the ZIP codes at the end of the record for the next program to reference.
Record change: 778 → 787 bytes (+ 9 bytes of saved ZIP data).
Source: DXCB165U.cbl paragraph 420 — MOVE BC3L-ZIP-END1 TO OUT-ZIP5-SAVE; MOVE BC3L-ZIP-END4 TO OUT-ZIP4-SAVE
2. DXCB166U — Restore Blanked ZIP Codes (787 → 778 bytes)
Input: MAIL.L207DC3.DATA.DTL (787 bytes)
Output: MAIL.L207DCL.TRAY.DTL (778 bytes)
What it does: Reads the 787-byte records from DXCB165U. For each record, checks whether the primary ZIP code field (BC3L-ZIP-END1) is blank or zero. If so, it substitutes the ZIP from the saved fields (BC3L-ZIP-END1-SAVED, BC3L-ZIP-END4-SAVED) that were appended to the end of the record in the prior step. After correction, writes only the original 778 bytes to output (the trailing 9 saved-ZIP bytes are consumed but not propagated).
Record change: 787 → 778 bytes (ZIP corrected; trailing save area dropped).
Source: DXCB166U.md business rule "ZIP Code Missing Value Substitution"
3. DXCBD24E — Place ZIP Code on City/State Line (778 → 778 bytes)
Input: MAIL.L207DCL.TRAY.DTL (778 bytes)
Output: EMAIL.ZUMDAHR1.TRA10.DTL (778 bytes)
What it does: Formats the 9-digit ZIP as NNNNN-NNNN and inserts it into the address line (city/state field) of the AFP form record. The program scans the 40-character address field for three consecutive spaces and inserts the formatted ZIP there, ensuring existing city/state data isn't overwritten. Record length stays 778 bytes — this is an in-place address field modification.
Record change: 778 → 778 bytes (address field enriched with formatted ZIP).
Source: DXCBD24E.md
4. DXCBBC3E — Add Sort Key (778 → 790 bytes)
Input: EMAIL.ZUMDAHR1.TRA10.DTL (778 bytes)
Output: MAIL.L207DCL.TRAF.DTL (790 bytes)
What it does: Reads each UI claim record, reformats claimant name fields (splits last name, first name, and middle initial from a combined name field), and appends a 12-byte sort key derived from a partial SSN and the mail date to the end of the record.
Record change: 778 → 790 bytes (+ 12-byte key field).
Source: DXCBBC3E.md
5. UIMI0754 (via step UIMB0754) — DB2 Employer Sync Code (790 → 797 bytes)
Input: MAIL.L207DCL.TRAF.DTL (790 bytes)
Output: L207DCL.SYNC.DTL (797 bytes)
What it does: For each record, extracts the claimant SSN (3 parts → packed numeric) and employer FEIN (3 parts → packed numeric), then queries the DB2 table UIMT_SG03_EMPLOYER using both as a combined key (WHERE SG03_IDN_SSN = :SSN AND SG03_EMP_FEIN = :FEIN). Retrieves the FEIN Synonym Code (SG03_FEIN_SYNONYM_CODE) and appends it to the output record. If no matching employer row exists, the synonym code defaults to zero — the record is still written.
Record change: 790 → 797 bytes (+ 7-byte sync/synonym code area).
Runs under: DB2 plan UIMIPLNP, invoked via TSO batch runner IKJEFT01.
Source: UIMI0754.md
Phase 4 — Foreign Pipeline (Same Programs, Parallel Steps)

The Foreign stream follows the same last two transformations as domestic, but skips the ZIP-save/restore and city-state insertion (those records have ZIP = 00000):

Table

Step

	

Program

	

Input → Output

	

...


DXCBBC3X	DXCBBC3E (same program)	FRGN.DTL → FRG2.DTL	...
UIMB754B	UIMI0754 (same program)	FRG2.DTL → FRG3.DTL	...
View more
Phase 5 — Merge and Laser Print (Step LASRPRNT)

Step LASRPRNT uses IEBGENER with concatenated SYSUT1 input:

MAIL.L207DCL.FRG3.DTL (foreign records, 797 bytes) — read first
L207DCL.SYNC.DTL (domestic records, 797 bytes) — appended after

Output goes to SYSOUT=(,),OUTPUT=(*.AFPOUT1) — the AFP printer queue configured as:

FORMDEF: GEN14
PAGEDEF: DOLB3E
Destination: LOCAL, ROOM='ADF_ND-USPS:DAILY'

No transformation is applied — IEBGENER with SYSIN DD DUMMY copies records straight through.

Phase 6 — Backups and Reprint Support
Table

Step

	

What It Does


BACKUP2	IDCAMS REPRO of SYNC.DTL → TRAY.BCKUP(+1) GDG (797 bytes)
BACKUP3	IDCAMS REPRO of FRG3.DTL → FRGN.BCKUP(+1) GDG (797 bytes)
DATEPG7	Reads SYNC.DTL (797 bytes), appends a 10-byte run date → PLUS10.DTL (807 bytes) for reprint indexing
GDGBUILD	Archives PLUS10.DTL → PLUS10.BCKUP(+1) GDG
DXCBR400	Returns RC=400 only if manually restarted at this step (RESTART=DXCBR400). Normal runs return RC < 100, so the reprint branch is skipped.
DXCBR7A/DXCBR7B/#REPRINT	Conditional reprint path: DXCBR7A selects records by run date from the GDG, DXCBR7B filters by record-number ranges, and #REPRINT sends the subset to the AFP printer.
View more
Record Length Summary Through the Chain
L207DCL Record Length Transformation Chain

Step

	

Program

	

LRECL In

	

...


SORT1/SORT2	SORT	778	...
DXCB165U	DXCB165U	778	...
DXCB166U	DXCB166U	787	...
DXCBD24E	DXCBD24E	778	...
DXCBBC3E	DXCBBC3E	778	...
UIMB0754	UIMI0754	790	...
LASRPRNT	IEBGENER	797	...
DATEPG7	DATEPG7	797	...
View more

Important caveats:

This describes what each program does within this job. The upstream process that populates MAIL.L207DC2.DATA.DTL is not documented in this job's JCL — it would be covered by a predecessor job in the daily CA-7 schedule.
The exact COBOL field layouts for DXCBD24E and DXCBBC3E are described from extracted business rules, not from a line-by-line source walkthrough. The internal field-level details (which bytes of the address field are scanned, exact sort-key composition) are derived from the program analyses and should be confirmed against the source if you need byte-level precision.
What would you like to explore next?

What feeds L207DCL its input?

Deep-dive into the DXCBBC3E key field derivation

Walk through the reprint mechanism

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 5
- Citation 6
- Citation 7

## v6-Q3

**Q:** In the daily refund reporting stream, how does LOOPS decide whether a refund payment counts as CASH, an offset, or a write-off?

**A** (13:35):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

The classification logic lives primarily in program DXCRD99E, a daily batch program that reads Segment 09 (refund payment) records from the Change Data Transaction File (CDTFILE) and assigns an Account Code of CASH, OFFSET (CLPY), or WRITE-OFF (WOFF) to each record based on the value of field DB09-REFUND-PAY-TYPE. That code is then carried into the SEG9FILE extract used by downstream reporting programs like DXCR227E (daily ETA-227 extract) and DXCR227M (monthly ETA-227). Here's the full decision chain, drawn directly from the DXCRD99E business rules.

Step 0 — Gate Check: Reject Pay Type '06'

Before any classification occurs, pay type '06' is rejected outright. The record is flagged as a bad record with the error message NOT-VALID-OFFSET-MSG and routed to the error file DB89FILE. No account code is ever assigned.
DXCRD99E.md

Step 1 — Initial Classification: CASH vs. OFFSET

The first decision evaluates the Refund Pay Type against a fixed list of known cash payment types :
DXCRD99E.md
DXCRD99E.md

Table

If

	

DB09-REFUND-PAY-TYPE

	

is…

	

...


'01', '02', '03', '04', '07', '09', '10', '51', '11', or '12'	CASH	...	
Anything else (and not '06', which was already rejected)	OFFSET (CLPY)	...	
View more

So the default for any unrecognized non-rejected pay type is OFFSET, not CASH. The CASH list is the explicit whitelist.

Step 2 — Write-Off Override for Pay Type '99'

After the initial CASH/OFFSET assignment, a secondary check looks specifically at pay type '99'. If the pay type is '99', the account code is overridden to WRITE-OFF (WOFF), regardless of whether Step 1 had assigned CASH or OFFSET.
DXCRD99E.md
DXCRD99E.md

Step 3 — Write-Off Reversal: No Waiver Reason → Back to CASH

There is one more refinement: if the pay type is '99' but the Waiver Reason Code field (DB09-WO-WAIVER-REASON-CODE) is blank (all spaces), the account code is overridden back from WRITE-OFF to CASH. The logic is that without a formal waiver reason on file, the transaction cannot be treated as a legitimate write-off and must instead be classified as a cash collection.
DXCRD99E.md
DXCRD99E.md

If the Waiver Reason Code is present (non-blank), the WRITE-OFF classification is retained.
DXCRD99E.md

The Complete Decision Flow
Refund Payment Account Code Classification Logic

Step

	

Condition

	

Account Code Assigned

	

...


Gate	Pay Type = '06'	REJECTED — routed to DB89FILE error file; no account code	...
1a	Pay Type ∈ {'01','02','03','04','07','09','10','51','11','12'}	CASH	...
1b	Pay Type NOT in the list above (and ≠ '06')	OFFSET (CLPY)	...
2	Pay Type = '99' (regardless of Step 1 result)	Override → WRITE-OFF (WOFF)	...
3	Pay Type = '99' AND Waiver Reason Code is blank	Override → CASH (reverts from WRITE-OFF)	...
3 (alt)	Pay Type = '99' AND Waiver Reason Code is present	Retain WRITE-OFF (WOFF)	...
View more
How Downstream Programs Use the Classification

The account code assigned by DXCRD99E is written into the DB99-ACCOUNT-CODE field of each SEG9FILE output record. Downstream reporting programs then consume it :
DXCR227E.md
DXCR227E.md

DXCR227E (daily ETA-227 extract) reads the Cash/Offset file and re-classifies records by pay type for accumulation into Section B, Line 202 (Cash) and Line 203 (Offset). It applies the same CASH pay-type list as DXCRD99E — pay types '01'–'04', '07', '09'–'12', '51' are CASH; everything else routes to the Offset line. Records that match neither are skipped.
DXCR227E.md
DXCR227E.md

DXCR227M (monthly ETA-227) also reads the DB09 Cash/Offset file and classifies pay types '05' and '06' specifically as Offset for the monthly report accumulation.
DXCR227M.md

Important Caveat — Scope of the Documented Rules

This describes the DXCRD99E classification logic as documented in the program analysis. The pay-type code values themselves (what '01' means in business terms, what '10' represents) are not defined in the program source — they are maintained operationally, likely in the CODELOOP VSAM dataset or in reference documentation outside the knowledge base. If you need the business meaning of each individual pay-type code (e.g., "01 = personal check, 05 = benefit offset"), that mapping would need to come from an SME or from the T120/CODELOOP reference data.

Also note a documented discrepancy between programs: DXCR227M classifies pay types '05' and '06' as Offset for monthly reporting, while DXCRD99E rejects '06' entirely as invalid. This may reflect different processing contexts (daily federal extract vs. monthly state report), but it is worth flagging for SME review if you are reconciling across both programs.
DXCRD99E.md
DXCR227M.md

What would you like to explore next?

Upstream job flow into DXCRD99E

ETA-227 report accumulation detail

Segment 09 copybook field layout

_Citations:_
- Citation 1
- Citation 1
- Citation 2
- Citation 1
- Citation 2
- Citation 1
- Citation 2
- Citation 2
- Citation 3
- Citation 4
- Citation 3
- Citation 4
- Citation 5
- Citation 1
- Citation 5

## v6-Q4

**Q:** What validations and computations does DXCRD88E apply to refund DB08 records, and how does it classify claims?

**A** (13:36):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

Here is a comprehensive breakdown of DXCRD88E — the DB08 Reformat daily batch program — synthesized from the DXCRD88E.md program analysis in the Daily CA-7 space.
DXCRD88E.md
DXCRD88E.md

DXCRD88E reads Segment 08 (refund claim / overpayment) records from the Change Data Transaction file (CDTFILE), runs them through a gauntlet of structural and percentage validations, computes net outstanding balances across 20 funding-category buckets, and writes one output record per positive-balance bucket to SEG8FILE for downstream report programs (DXERD801–DXERD804). Invalid records are routed to DB89FILE with a diagnostic error message.

Part 1 — Validation Pipeline

Every record is validated in a strict, short-circuiting sequence. The first failing check sets the error message and immediately exits to error processing — no later checks are applied.

DXCRD88E Validation Pipeline

Step

	

Validation

	

Condition to Reject

	

...


1	Before/After Byte validity	Byte ∉ {B, A, I, D}	...
2	Delete Byte rejection	Byte = D (Delete)	...
3	Program Code 45 rejection	Program Code = 45	...
4	Federal amount presence	All three Federal amounts due (Fraud, Non-Fraud, Agency Error) = 0	...
5	PC 20: Fed% and UCFE% must = 100%	PC=20 and (Fed% ≠ 100% or UCFE% ≠ 100%)	...
6	PC 30: Fed% and UCX% must = 100%	PC=30 and (Fed% ≠ 100% or UCX% ≠ 100%)	...
7	Fed% + NonFed% must = 100%	Sum ≠ 100%	...
8	PC 80/83: Fed%=100%, UCX%=0%, UCFE%=0%	Any condition not met	...
9	UCX% + UCFE% ≈ Fed% (rounding tolerance)	Sum outside tolerance range	...
10	Zero Fed% with non-zero UCX/UCFE	Fed%=0 and (UCX%>0 or UCFE%>0)	...
View more
Key Validation Notes
Transaction Code D15U is a special adjustment transaction that is exempt from all percentage validations (steps 5–11). This allows D15U records to carry otherwise-invalid percentage combinations without being rejected.
DXCRD88E.md
DXCRD88E.md
Step 4 (federal amount presence) is not an error — records with no federal amounts are silently skipped with no output and no error record.
DXCRD88E.md
DXCRD88E.md
Step 9 uses a configurable rounding tolerance rather than exact equality, and has three additional bypass conditions: PC 80/83, all-percentages-zero, and the D15U + PC 15 special case.
DXCRD88E.md
Part 2 — Transaction Sign Determination

Before validations begin, the Before/After Byte determines how all financial amounts will be signed in output :
DXCRD88E.md

DXCRD88E Transaction Sign (BUCKET-SIGN)

Before/After Byte

	

Meaning

	

BUCKET-SIGN


B (Before)	State before a change — being reversed	−1 (negative)
A (After)	State after a change — new current value	+1 (positive)
I (Insert)	New record being added	+1 (positive)
D (Delete)	Record being removed	−1 (negative) — but also rejected as bad record
View more

Note: although Delete records receive a −1 sign, they are always rejected (step 2) and routed to the error file. The sign is still applied to their error-file amounts for directional accounting.
DXCRD88E.md

Part 3 — Claim Classification

After the structural validations pass, each record receives a classification and an account code in paragraph 1200-RECORD-HSKG :
DXCRD88E.md
DXCRD88E.md

DXCRD88E Claim Classification Logic

Program Code

	

Classification (DB88-LOOPS-SKELETON-IND)


10, 20, 21, 22, 23, 30, 31, 40, 41, 42, 43	LOOPS (active UI programs)
Any other code (except 99)	SKELETON (inactive/non-standard)
99	SUSPENSE (overrides any prior LOOPS/SKELETON assignment)
View more
The Account Code (DB88-ACCOUNT-CODE) is set to RECEIVABLES unconditionally for every record that reaches this step, regardless of classification.
DXCRD88E.md
Classification and account code fields are cleared to spaces before each record to prevent carry-over.
DXCRD88E.md
Part 4 — Balance Computation (20 Funding Buckets)

For every record that passes all validations, DXCRD88E computes 20 outstanding balances, each as :
DXCRD88E.md
DXCRD88E.md

Balance = Amount Due − Amount Paid

DXCRD88E — 20 Funding-Category Balance Buckets

Funding Category

	

Fraud

	

Non-Fraud

	

...


NFED (Non-Federal)	✓	✓	...
FED / UCX / UCFE (Federal)¹	✓	✓	...
EB (Extended Benefits)	✓	✓	...
FSC (Federal Supplemental Comp.)	✓	✓	...
EUB (Extended Unemployment Benefits)	✓	✓	...
WFD (Workforce Development)	✓	✓	...
FINE (Fines)	— single bucket —		...
INTR (Interest)	— single bucket —		...
View more

¹ Federal balances are written under the FED funding code only for PC 80/83 and D15U special cases; for all other program codes they are split between UCX and UCFE using the UCFE-as-percent-of-Federal ratio.

Only buckets with a positive balance produce an output record. The balance is then multiplied by the BUCKET-SIGN to produce the signed amount written to SEG8FILE.
DXCRD88E.md
DXCRD88E.md

Part 5 — Federal Amount Splitting (UCX/UCFE)

The routing of Federal refund balances depends on the program code :
DXCRD88E.md

DXCRD88E Federal Balance Routing

Condition

	

Routing

	

Funding Code(s)


PC 80 or 83	Direct — no split	FED
D15U + specific PCs (01,04,08,09,15,16,17,70,71,76,80,83,84,90) with Fed amounts > 0	Bypass split — straight FED processing	FED
All other PCs	Split using UCFE-as-%-of-Federal ratio	UCFE (proportional share) + UCX (remainder)
PC 30 special case	UCX output even when UCX% = 0, if UCFE amount is zero	UCX
View more

The UCFE ratio is computed as:

UCFE-as-Pct-of-Fed = UCFE Claim % ÷ Federal Claim % (rounded)

For each fraud type (Fraud, Non-Fraud, Agency Error):

UCFE amount = Federal Balance × UCFE-as-Pct-of-Fed → written with funding code UCFE
UCX amount = Federal Balance − UCFE amount → written with funding code UCX

If no UCFE was allocated (UCFE Claim% = 0), the full Federal balance goes to UCX.
DXCRD88E.md

Part 6 — Safety Checks and Error Processing
Empty Bucket Validation: After processing all 20 funding categories for a valid B (Before) or I (Insert) record (excluding transaction code D070), if zero output records were written, the program abends with error code 800. This guards against data integrity issues.
DXCRD88E.md
DXCRD88E.md
Bad Record Processing (1301-BAD-IMAGE-PROC): For rejected records, all 20 amount-due fields (not balances) are multiplied by BUCKET-SIGN and written to DB89FILE along with SSN, Program Code, Claim Date, Before/After Byte, Transaction Code, Local Office, all four claim percentages, and the specific error message.
DXCRD88E.md
Balance Reset: All 20 balance fields are zeroed after each record to prevent carry-over.
DXCRD88E.md
DXCRD88E.md
Scope Caveat

This describes the DXCRD88E program as documented in its program analysis. It covers only the DB08 reformatting step — the upstream CDT file extraction and downstream report programs (DXERD801–DXERD804) that consume SEG8FILE are separately documented. The business meanings of individual program codes (e.g., what "Program Code 10" or "Program Code 43" represents) are not defined in this program's source — those definitions live in operational reference data or policy documentation outside the knowledge base.

What would you like to explore next?

Downstream report programs

Compare DB08 vs DB09 processing

D15U special cases deep dive

_Citations:_
- Citation 1
- Citation 2
- Citation 1
- Citation 2
- Citation 1
- Citation 2
- Citation 1
- Citation 2
- Citation 2
- Citation 1
- Citation 2
- Citation 2
- Citation 2
- Citation 1
- Citation 2
- Citation 1
- Citation 2
- Citation 1
- Citation 2
- Citation 1
- Citation 2
- Citation 2
- Citation 1
- Citation 2

## v6-Q5

**Q:** Job L216DA maintains the alpha (name search) file. What are its inputs, and how does a day's activity end up in the alpha VSAM file?

**A** (13:38):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

Here is a comprehensive walkthrough of job L216DA — the daily Alpha (name search) file maintenance job — synthesized from the L216DA.md JCL analysis, DXCBD08R.md, DXCBD06R.md, and DXCBD13R.md program analyses in the Daily CA-7 space.

L216DA is a seven-step daily batch job that consolidates all of the day's new claims, claim changes, and the prior day's baseline Alpha records into a single updated Alpha detail file on tape. That tape file is then consumed by the downstream job L216DB, which deletes, redefines, and reloads the actual Alpha VSAM cluster (LAK2LDXP.VSAM.ALPHA.CLUSTER) from it.

Input Files

L216DA consumes five inputs — three claim activity files, one VSAM cluster, and two reference/control files :
L216DA.md
L216DA.txt

L216DA Input Files

DD Name

	

Dataset Name

	

Description

	

...


NEWCLM	LAK2LDXP.L213DA.DLY.NEWCLAIM.DTL(0)	Daily New Claims — all newly filed claims for the current processing day	...
CHGCLM	LAK2LDXP.L213DA.CLMMAINT.DTL	Claim Maintenance — all change/update records for existing claims	...
DABSCLM	LAK2LPAP.TBACKUP.D2LID100.SRTFL.DTL(0)	Daily Sorted Backup (DABS) — the most recently produced sorted detail records (yesterday's baseline activity)	...
(VSAM)	LAK2LDXP.VSAM.ALPHA.CLUSTER	The current Alpha VSAM KSDS — the existing name-search database	...
TABLE	LAK2LDXP.VSAM.CODES.CLUSTER	VSAM Business Codes Reference Table — used for code validation and translation	...
DATECARD	LAK2LDXP.PROD.CNTLLIB(DATECARD)	Processing Date Control Card — supplies the current business processing date	...
View more

The three claim files (NEWCLM, CHGCLM, DABSCLM) represent all of the day's activity: brand-new filings, maintenance changes to existing claims, and the prior day's sorted detail baseline.

End-to-End Flow: How a Day's Activity Reaches the Alpha File

The job runs seven strictly sequential steps. Each step is guarded by COND=(0,NE) — if any prior step returns a non-zero return code, all remaining steps are skipped.
L216DA.md
L216DA.md

Step 1 — REPRO1A (IDCAMS): Backup the Daily Sorted Detail File

Before touching any data, the job creates a GDG backup of the current DABS sorted detail file:

Input: LAK2LPAP.TBACKUP.D2LID100.SRTFL.DTL(0) (1,144-byte FB records)
Output: LAK2LDXP.L216DA.D2LID100.SRTBKP.DTL(+1) — new GDG generation, permanently cataloged
On failure the incomplete generation is auto-deleted.
L216DA.md
L216DA.md
Step 2 — DXCBD08R: Merge Three Claim Sources into One

Program DXCBD08R reads all three claim activity files and produces a single merged Alpha dataset. For each claim record it :
DXCBD08R.md

Parses the claimant name — splits "LAST/FIRST" on the / delimiter into separate last-name and first-name fields
Splits the address into street and city components
Cleanses name and city by stripping non-alphabetic characters
Stamps a claim-type indicator: 'A' = New Claim, 'C' = Change Claim, 'B' = DABS Claim
Validates coded fields against the VSAM Codes Reference Table
Writes a standardized 55-byte FB record containing: last name, SSN, first name, city, and claim type indicator
Input: NEWCLM, CHGCLM, DABSCLM, TABLE, DATECARD
Output: &&MERGE (temp, 55-byte FB, passed to next step)
Reports: D00RFILE — exception/error report
Step 3 — REPRO1 (IDCAMS): Unload the Alpha VSAM Cluster

Extracts the entire current Alpha VSAM cluster into a temporary sequential file, skipping the first record (which is a non-claim header/control record) :
L216DA.md
L216DA.md

Input: LAK2LDXP.VSAM.ALPHA.CLUSTER (KSDS, 23,465-byte records, 29-byte key at offset 0)
Output: &&ALPHA (temp, 23,465-byte FB records — claim data only)
Step 4 — DXCBD06R: Condense VSAM Records to Key Fields

Program DXCBD06R reads each massive 23,465-byte VSAM record and extracts only the essential key identifying fields, condensing them into compact 54-byte records suitable for merge comparison :
L216DA.md
L216DA.md

Input: &&ALPHA, TABLE, DATECARD
Output: &&SPLIT (temp, 54-byte FB records)
&&ALPHA is consumed and permanently deleted after this step
Step 5 — SORT1: Sort the Merged Daily Transactions

Sorts the 55-byte merged daily records from Step 2 in ascending order by the 9-byte claim/member identifier (SSN) at position 21 :
L216DA.md
L216DA.md

Input: &&MERGE → Output: &&SORTA (becomes DAILYF for reconciliation)
&&MERGE is consumed and deleted
Step 6 — SORT2: Sort the Existing Alpha Records

Sorts the 54-byte condensed existing Alpha records from Step 4 in ascending order by the same 9-byte key at position 21 :
L216DA.md
L216DA.md

Input: &&SPLIT → Output: &&SORTB (becomes OLDALPHA for reconciliation)
&&SPLIT is consumed and deleted
Step 7 — DXCBD13R: Reconcile and Produce Updated Alpha Detail File

This is the heart of the job. Program DXCBD13R performs a classic sequential SSN merge of the two sorted files :
DXCBD13R.md

DAILYF (&&SORTA, 55-byte) — today's combined activity
OLDALPHA (&&SORTB, 54-byte) — existing Alpha baseline

The merge logic works as follows:

SSN Match (OLD-SSN = DAILY-SSN): The daily record replaces the old record — the updated claim data is written to output
Daily SSN is lower (new claim not in old file): The daily record is inserted as a new Alpha entry
Old SSN is lower (no change today): The existing Alpha record is carried forward unchanged
Duplicate daily SSNs: When multiple daily records share the same SSN, only the latest (last-encountered) record is kept; earlier duplicates are discarded
Last Daily Record Resolution: A special boundary-handling routine ensures the last buffered daily record is placed in correct SSN order relative to remaining old records

Output: LAK2LDXP.L216DA.ALPHA.DTL(+1) — a new GDG generation on tape with permanent retention (EXPDT=99000). Each output record contains: last name, SSN, first name, and city.
DXCBD13R.md

Both &&SORTA and &&SORTB are consumed and deleted after processing.

The Last Mile: L216DB Reloads the VSAM Cluster

L216DA does not write to the Alpha VSAM cluster directly. Its output is a sequential GDG tape file. The downstream job L216DB completes the cycle :
L216DB.md
L216DB.md

Deletes and redefines LAK2LDXP.VSAM.ALPHA.CLUSTER (KSDS, 23,465-byte records, 29-byte key, 400 primary cylinders)
Initializes the cluster with a blank seed record
Sorts the L216DA.ALPHA.DTL(0) detail file by name + SSN
Loads the sorted records into the freshly defined VSAM cluster using program DXCBD04R

After L216DB completes, the Alpha VSAM cluster reflects all of the day's new claims, changes, and carried-forward records — ready for online CICS name-search queries.

Scope Caveat

This describes the L216DA → L216DB pipeline as documented in the JCL and program analyses in the Daily CA-7 space. The upstream job L213DA that produces the NEWCLM and CHGCLM input files, and the CICS online programs that query the Alpha VSAM cluster for name searches, are separately documented and not covered here. The internal record layout of the 23,465-byte VSAM Alpha records (what fields beyond name/SSN/city they carry) is not detailed in the held program analyses for DXCBD13R — that structure is defined in the VSAM cluster's copybook, which is not in the current knowledge base slice.

What would you like to explore next?

Deep dive into DXCBD08R name parsing logic

Walk through L216DB VSAM reload

Trace the upstream L213DA job

_Citations:_
- Citation 1
- Citation 2
- Citation 1
- Citation 3
- Citation 1
- Citation 3
- Citation 4
- Citation 1
- Citation 3
- Citation 1
- Citation 3
- Citation 1
- Citation 3
- Citation 1
- Citation 3
- Citation 5
- Citation 5
- Citation 6
- Citation 7

## v6-Q6

**Q:** The automated handbook update job sorts IB13 updates by state and section within date and time before applying them. Why does that order matter, and what does the update program do with each record?

**A** (13:39):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

Here is a comprehensive walkthrough of job L2AHD13 — the Automated Handbook Update job — synthesized from the L2AHD13.txt JCL, UIPBHB01.md, and UIPBHB02.md program analyses in the Daily CA-7 space.

Why the Sort Order Matters

The job processes incoming IB13 inter-state messages that carry handbook section updates. Multiple IB13 messages can arrive for the same state and section on a given day — for example, an editor might revise Section 3 of the NJ handbook twice in one afternoon. The sort order guarantees that the last record the update program encounters for each state+section is the most recent one, so that version — and only that version — becomes the authoritative content written to the Handbook VSAM file.
L2AHD13.txt
UIPBHB01.md

The composite sort key is:

State → Section → Century → Julian Year → Julian Day → Creation Time

This produces two critical effects:

Grouping: All records for the same state and section are adjacent, so the update program can detect section boundaries cleanly.
Chronological ordering within each group: Within a state+section, records run oldest-to-newest. Because UIPBHB02 processes records sequentially and does a delete-then-write for each one, the last record in the group overwrites all earlier versions. If the sort were random, a stale earlier revision could land after a newer one and become the version of record.
UIPBHB01.md
UIPBHB01.md
End-to-End Job Flow

Job L2AHD13 runs in three steps :
L2AHD13.txt

Step 1 — UIPBHB01: Select and Extract Qualifying IB13 Records

Program UIPBHB01 browses the IB13 VSAM indexed file for incoming records (IB13I) addressed to the state's .HANDBOOK receiver.
UIPBHB01.md
UIPBHB01.md
 For each record it:

Filters — skips any record whose Receiver/Sender ID is not .HANDBOOK (boundary check), and skips any record whose Batch Switch = 'Y' (already processed by a prior run)
Extracts state and section — reads the first text line of the IB13 message:
If the line matches the section-header pattern ***** XXY ***** (where XX = state, Y = section), state and section are parsed from the header
Otherwise, state and section are parsed from fixed positions at the beginning of the record-key line
Builds the sort key — converts the IB13 creation date (Gregorian → Julian via 8000-GREG-CONVERT), determines century ('20' if year < 50, else '19'), captures creation time, and places all six components into the temporary record prefix: TEMP-STATE, TEMP-SECTION, TEMP-CENTURY, TEMP-JUL-YEAR, TEMP-JUL-DAY, TEMP-TIME
Embeds the payload — copies the full IB13 message record into TEMP-IB13-RECORD alongside the sort key
Writes the assembled record to a sequential temporary file (DA-INFLTEMP)
Reports — displays totals for IB13 records read vs. temporary records written at EOJ
Step 2 — JCL SORT: Sort the Temporary File

The JCL sorts the temporary file on the sort key fields (State, Section, Century, Julian Date, Creation Time) in ascending order. This is what places the most recent update for each section last.
L2AHD13.txt
UIPBHB01.md

Step 3 — UIPBHB02: Apply Sorted Records to the Handbook VSAM

Program UIPBHB02 reads the sorted temporary file sequentially and processes each record as follows :
UIPBHB02.md
UIPBHB02.md

What UIPBHB02 Does With Each Record

For every record read from the sorted file, the program executes this sequence :
UIPBHB02.md
UIPBHB02.md

Map to IB13 layout — extracts the IB13 key, data, text-line count, and text lines from the temporary record into the working IB13 record layout; resets the line counter to 1

Detect new section vs. continuation — examines the first text line:

If it matches ***** XXY ***** → new section header
Otherwise → continuation record for the current section

Section-boundary handling:

First section header ever (first-time switch = 'Y'): saves the IB13 key, copies the header line into the handbook record buffer, turns off the first-time switch, and advances the line counter — no VSAM write yet
Subsequent section header (first-time switch = 'N'): marks the previous handbook record as having no continuation (HB-NEXT-RECORD-SWITCH = 'N'), writes it to the Handbook VSAM, then copies the new header into the buffer
Continuation record: marks the current handbook record as having a continuation (HB-NEXT-RECORD-SWITCH = 'Y') and writes it to the Handbook VSAM

Extract the VSAM key — reads the key line from the IB13 text (second line for new sections, first line for continuations) and parses the 5-character key: State (2) + Section (1) + Record Number (2) = XXYZZ

Delete the existing handbook record — issues a DELETE HB-FILE RECORD using the extracted key. Status '23' (not found) is acceptable — the IB13 may represent a brand-new section.
UIPBHB02.md
UIPBHB02.txt
 As the source code comments state: "When a section of the automated handbook is updated, the whole section will be replaced on the VSAM file"

Delete the corresponding HIP record — attempts to remove the matching entry from the Handbook In-Progress file (DA-UIFLHB01) using the same key, cleaning up pending-update tracking

Initialize the new handbook record — clears the last-export date to zeros, sets the last-update date to today's system date (formatted via FAPCONF2), clears filler, and defaults HB-NEXT-RECORD-SWITCH to 'N'

Copy IB13 text lines into the handbook record — iteratively moves each text line from the IB13 record into the handbook record being built, adjusting the line counter to account for the key line that is read but not written to the text area

Write the handbook record to VSAM — writes the completed record to DA-UIFLHB00 and displays a confirmation message with the key

Mark the source IB13 as processed — re-reads the previous IB13 record from the IB13 file, sets IB13-READ-SWITCH = 'Y' and IB13-BATCH-SWITCH = 'Y', stamps it with the current Julian date, and rewrites it. This marks it for purge by the next IB13 batch cleanup run

Re-read the current IB13 — re-reads the current IB13 using its saved key and saves that key for the next write cycle

End-of-file — when the sorted file is exhausted, writes the final pending handbook record with HB-NEXT-RECORD-SWITCH = 'N'

At the end, the program displays totals: sorted records read and handbook records written, which should be equal (one-to-one correspondence).
UIPBHB02.md

Summary: Why Sort-Then-Process Works

The sort order (State + Section + Date + Time ascending) combined with UIPBHB02's delete-before-write logic means that for any given state+section, each successive record replaces the prior one. The last record in each group — the most recent — becomes the final version on the Handbook VSAM file. Without the sort, an older revision could overwrite a newer one, producing an incorrect handbook.

Scope Note

This describes the UIPBHB01 → SORT → UIPBHB02 pipeline as documented in the Daily CA-7 space. The origin of the IB13 records themselves (the inter-state messaging system that creates them) and the CICS online programs that display the Automated Handbook to users are separately documented and not covered in this slice of the knowledge base.

_Citations:_
- Citation 1
- Citation 2
- Citation 2
- Citation 3
- Citation 1
- Citation 2
- Citation 3
- Citation 1
- Citation 2
- Citation 4
- Citation 5
- Citation 4
- Citation 5
- Citation 4
- Citation 6
- Citation 4

## v6-Q7

**Q:** Which daily job produces the employer daily charge report, which records make it onto the report, and how is the report organized?

**A** (13:41):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

The employer daily charge report is produced by a two-job pipeline: job L205DJ extracts and categorizes the raw charge segments, and downstream job L206DL formats and prints the control reports. Here is a synthesized walkthrough drawn from the DXCBD43E.md, L206DL.md, L206DL.txt, DXEBD44R.txt, and DXEBD49R.txt source analyses in the Daily CA-7 space.

The Jobs

L205DJ — Runs program DXCBD43E (COBOL batch). This is the heavy-lifting extract-and-categorize step. It reads every daily employer charge segment from the LOOPCD04 input file, validates and classifies each record, and writes one summary record per charge category to the CHGRPT output file (plus several side-effect files).
DXCBD43E.md
DXCBD43E.md

L206DL — Runs two Easytrieve programs sequentially :
L206DL.md
L206DL.md

Step 1 — DXEBD44R: reads the CHGRPT summary file from DXCBD43E, sorts it by charge type, and prints up to eight separate control reports
Step 2 — DXEBD49R: reads the CETAEMP detail file from DXCBD43E and prints the Daily Charge Report — CETA Employers
Which Records Make It Onto the Report

Program DXCBD43E applies a multi-gate validation to every record read from LOOPCD04. A record must pass all gates to be categorized, accumulated into the charge table, and ultimately appear on the report :
DXCBD43E.md
DXCBD43E.md

Transaction code = E010 or E012 — any other code is written to the control error report and skipped
Non-zero charge or penalty — records where both the employer charge amount and the penalty charge are zero are classified (assessment-only, C-week/balance-restore, or zero-charge) and counted but are not written to the charge category report
Valid program code + pay transaction code — the combination must match the Unit Record Code table; mismatches go to the error report
Valid pay transaction code — must be found in the Prefix Pay Code table (binary search); invalid pay codes go to the error report
Non-zero employer FEIN — all-zeroes FEINs are flagged as errors
Not a CETA or SP01 employer — CETA employers (FEIN prefix 800000) and SP01 special FEINs bypass the main charge-category pipeline and are routed directly to the CETAEMP output file for the separate CETA report

Records that survive all six gates are classified into one of 42 charge categories by employer FEIN and pay-transaction-code range, accumulated in a charge table, and at wrap-up one summary record per category is written to the CHGRPT file.
DXCBD43E.md

How the Report Is Organized
Step 1 — DXEBD44R (Charge Control Reports)

DXEBD44R sorts the incoming CHGRPT records by CHGTYPE (charge type code) and then splits them across multiple reports by charge-type range :
DXEBD44R.txt

DXEBD44R Report Breakdown By Charge Type

Report

	

Report Number

	

Title

	

...


RPT1	DXEBD44R-RPT-001	Daily Employer Charge Control Report (No EB)	...
RPT2	DXEBD44R-RPT-002	Daily Extended Benefits Charge Control Report	...
RPT3	DXEBD44R-RPT-003	Daily Charge Report — Conversion Employer	...
RPT4	DXEBD44R-RPT-004	Daily E.U.B. Charge Control Report	...
RPT5	DXEBD44R-RPT-005	Daily W.F.D. Charge Control Report	...
RPT6	(added 3/99)	Non-Charge Types Report	...
RPT7	(added 3/02)	FSC Charge Types Report	...
RPT8	(added 4/02)	TUCX Charge Types Report	...
View more

Each report shares the same columnar layout :
DXEBD44R.txt

Fund (charge category description, e.g. "UI-CONTRIBUTORY", "UCFE", "UCX", "GENERAL FUND")
Debit CNT — count of debit transactions
Debit DOLLARS — total debit dollar amount
Credit CNT — count of credit transactions
Credit DOLLARS — total credit dollar amount
Net Amount of DOLLARS — net (debit minus credit)
Total REC CNT — total record count for that category

At the bottom of each report, a Totals line sums all the columns. After all the sub-reports print, DXEBD44R also computes reconciliation cross-totals from the individual category net amounts and writes those to a reconciliation VSAM cluster.
DXEBD44R.txt

Step 2 — DXEBD49R (CETA Report)

DXEBD49R is a simple detail-listing report titled "Daily Charge Report — CETA Employers" (DXEBD49R-RPT-001). It prints one line per CETA charge record with :
DXEBD49R.txt

SSN, Claimant Name, Date of Claim, Local Office, Charge Week Ending, Charge Amount, WBR, MBA, Pay Code, Balance, Partial amount, Employer Registration Number

At the bottom it prints an Amount Total of all charge amounts.

Upstream: The 42 Charge Categories

The category index assigned by DXCBD43E determines which sub-report a category lands on. Here is the documented mapping (synthesized from the DXCBD43E.md business rules) :
DXCBD43E.md
DXCBD43E.md

DXCBD43E Charge Category Index Map

Index

	

Category

	

Employer FEIN / Condition

	

...


1	UI Contributory (Regular)	Regular NJ employer, regular pay codes	...
2	General Fund (Regular)	FEIN 888888, regular pay code	...
3	UCFE (Regular)	FEIN 000002, regular pay code	...
4	UCX (Regular)	FEIN 000003 or 444444, regular pay code	...
5	General Fund – FSC/Extended	FEIN 888888, FSC/extended pay code	...
10	Out-of-State	FEIN 999998	...
11	UI Contributory – EB	Regular NJ employer, EB pay code	...
12	EB Charged to Federal	FEIN 777777, federal EB	...
13	General Fund – EB First Week	FEIN 888888, pay codes 107/108	...
14	General Fund – EB Unfunded	FEIN 888888, EB unfunded code	...
View more
Scope Note

This describes the extraction step (L205DJ / DXCBD43E) and the control-report printing step (L206DL / DXEBD44R / DXEBD49R). The same extraction also feeds several other downstream jobs and files — the Federal Charge Report (FEDRPT, printed by L206DN), the B187 bank tape (L206DK), the CWC selection file (SLCTCWC), and the UC53 Penalty Assessment (L206DP) — but those are separate report streams. Programs DXCBD40E and DXCBD50E, which appear in the source code with the same per-claim-type report title literals (Intrastate 1A, Interstate 1B, UCFE 1C, etc.), are different programs producing the per-claim-type detail employer charge reports; their full business rules were not fully retrieved in this search, so the detail-report pipeline is not described here.

Would you like to explore a related topic?

B187 reverse file details

UC53 penalty assessment pipeline

Per-claim-type detail reports (DXCBD40E / DXCBD50E)

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 1
- Citation 2
- Citation 2
- Citation 5
- Citation 5
- Citation 5
- Citation 6
- Citation 1
- Citation 2

## v6-Q8

**Q:** In job L213DC, where do the error records from the DB08 reformat program (DXCRD88E) actually land, and is there anything surprising about it?

**A** (13:41):

ENGINEERING ONBOARDING SPECIALIST
Completed 1 step

This is a great question — and yes, there is something quite surprising here. Let me walk through the full picture.

Where the Error Records Land

Program DXCRD88E (the "DB08 Reformat" step) opens three files at startup in its 200-HSKG paragraph :
DXCRD88E.txt
DXCRD88E.txt

cobol

OPEN INPUT CDTFILE
     OUTPUT SEG8FILE
     OUTPUT DB89FILE.

Inside the COBOL code, the program writes error records to the FD named DB89FILE — the DB89-REFERROR record is written via WRITE DB89-REC to the DB89FILE logical file.
DXCRD88E.md
DXCRD88E.md

Now here's where the JCL becomes important. In the DXCRD88E step of job L213DC, the DD card for DB89FILE is wired to :
L213DC.txt

jcl

//*DB89FILE DD  DSN=LAK2LDXP.L213DC.DB98FILE.DTL,       ← commented out
//DB89FILE DD  DSN=LAK2LDXP.L213DC.DB98FIL.DTL,DISP=(NEW,CATLG,DELETE),
//             DCB=(LRECL=159,BLKSIZE=23373,RECFM=FB,BUFNO=20),
//             SPACE=(CYL,(250,250),RLSE)
The Surprising Part

The COBOL program's error output (DB89FILE) is mapped by the JCL to the DB98FIL.DTL dataset — not to a dataset with "DB89" in its name.

In other words:

The program thinks it's writing to "DB89FILE" (its FD name and internal purpose: error records for bad Segment 8 / DB08 records)
The JCL redirects that logical file to LAK2LDXP.L213DC.DB98FIL.DTL
The JCL documentation and flow diagrams explicitly label this as "DB89FILE - DB98 Detail File" or "DB89FILE - DB98 Filter Detail"

So the error records from the Segment 8 validation step end up in a file called DB98FIL, and the commented-out line even shows a previous name DB98FILE — revealing the file was always meant for the DB98 path, not a DB89-named error file. The naming collision is this: the COBOL FD is called DB89FILE (following a naming convention for error/exception output from DB08 processing), but the physical dataset follows the segment number convention (DB98 for Segment 8 data, DB89 for Segment 9 data).

The mirror image happens in the very next step (DXCRD99E), where that program's DB89FILE DD is mapped to LAK2LDXP.L213DC.DB89FIL.DTL — which makes intuitive sense because DXCRD99E processes Segment 9.
L213DC.md
L213DC.md

What Happens to the Error Records Downstream

At the end of job L213DC, the REPRA262 step uses IDCAMS REPRO to archive both files into GDG versioned storage :
L213DC.md

DB98FIL.DTL → DB98FILE.DTL(+1) (Segment 8 errors/filter detail)
DB89FIL.DTL → DB89FILE.DTL(+1) (Segment 9 errors/filter detail)

Both archives are permanently catalogued for downstream use.

Summary
DXCRD88E Error Output Mapping

Layer

	

Name

	

Physical Dataset

	

...


COBOL FD	DB89FILE	(logical only)	...
JCL DD	DB89FILE	LAK2LDXP.L213DC.DB98FIL.DTL	...
GDG Archive	DB98FILE.DTL(+1)	LAK2LDXP.L213DC.DB98FILE.DTL(+1)	...
View more

The surprising takeaway: if you're looking at production datasets and searching for "DB89" to find the Segment 8 error records, you won't find them — they're hiding in the DB98 file. The "DB89" COBOL FD name is an internal convention for "error file from the DB08 reformat," but the JCL maps it by segment number to DB98. This naming cross-over is an easy source of confusion during debugging. An SME or the original system designer would be the right person to confirm whether this was always intentional or an artifact of historical naming evolution (the commented-out DB98FILE line hints at the latter).
L213DC.txt

Would you like to explore more about this job?

Show me the full list of validation rejection reasons

Compare DXCRD88E vs DXCRD99E

Trace the error files downstream

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 5
- Citation 6
- Citation 7
- Citation 6
- Citation 5
