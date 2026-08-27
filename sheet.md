# Quick run sheet

Ask these in EXACTLY this order, all in the same conversation. Do not start a
new chat partway through, and do not interleave any other question: some
questions only mean something when they immediately follow the one before them.

Paste each answer back between its `<!-- atlas:answer <question-id> -->`
marker and the next one, in the Answers section below. Leave the markers
exactly as they are; only replace the placeholder text under each one.
Record the conversation id, if you have it, on the `conversation:` line at
the end (it is read wherever it appears, but the slot at the end is where it
belongs).


## Questions

## 1. v3-Q1

Describe the Automated Collection Process.

## 2. v3-Q2  _(must be asked immediately after v3-Q1)_

What does the acronym ACP stand for?

## 3. v3-Q3

When LOOPS issues a weekly benefit payment, how is the charge allocated across the claimant's base-period employers?

## 4. v3-Q4

Which LOOPS batch processes validate SSNs and check whether a claimant is deceased, and how do they work?

## 5. v3-Q5  _(must be asked immediately after v3-Q4)_

What are the 16/16 and 16/17 screens in LOOPS used for?

## 6. v3-Q6

How does LOOPS determine whether a weekly certification was submitted by phone (IVR), on the web, or entered by staff?

## 7. v3-Q7  _(must be asked immediately after v3-Q6)_

What is JPAY and how does it connect to LOOPS?

## 8. v3-Q8

How are municipality (MUNC) codes validated in LOOPS?

## Answers

<!-- atlas:answer v3-Q1 -->

The knowledge base has no process documented by the exact name "Automated Collection Process." However, the closest documented match is the Accelerated Collection Process, which is the name given to program UIMB0730. If that's what you're looking for, here's what's documented:

UIMB0730 — Accelerated Collection Process
This is a batch COBOL program that processes payment records received from the Department of Revenue (DOR) and updates the UIMT_DOR_REFUND_PAYMENTS DB2 table.UIMB0730.md

Environment details:

Execution: Batch
Database: DB2
MQ Calls: No
Module Type: Main/Driver module
Key processing logic:

The program handles two distinct payment channels:

Web-based payments (EFT or CRD types) — It matches incoming payment records to existing database entries in UIMT_DOR_REFUND_PAYMENTS and updates them with processed/received dates and a match code.

Lockbox/coupon payments — It looks up the claimant's SSN from UIMT_UNIQUE_CLAIMANT_ID and inserts a new payment record into UIMT_DOR_REFUND_PAYMENTS.

Error handling:

Unmatched CRD payments are written to an error output file
Unresolved claimant IDs are also written to the error output file
Important note: This describes a single batch program step. Upstream processes (how the DOR payment file arrives) and downstream processes (what consumes the updated DB2 table) are not fully detailed in this particular program's documentation.

Is this the process you were asking about, or were you referring to something else? There are also related debt-collection concepts documented in the knowledge base — such as the DABS (Debt Automated Build System) document generation process (in JCL job D2FND222) and the broader Collection of Debt (COD) lifecycle tracked across claims — if either of those is a better fit.

<!-- atlas:answer v3-Q2 -->

In the LOOPS system, ACP stands for Accelerated Collection Process.06_terminology_gl...

This is documented in the LOOPS terminology glossary (06_terminology_glossary.md), which cites the "LOOPS Daily Flowchart" as the source for this expansion. The acronym is used as a prefix throughout related programs and copybooks — for example, fields like ACP-DOR-VALID-PAYMENT, ACP-AMT-PAID, ACP-CLAIMANT-ID, etc. appear in programs UIMB0730, UIMB0731, and copybook ACPVALID.ACPVALID.txt
UIMB0731.txt
UIMB0730.txt

<!-- atlas:answer v3-Q3 -->

This is a detailed topic that the knowledge base documents thoroughly. The employer charge allocation process in LOOPS involves two phases: (1) establishing each employer's charge percentage at claim setup time, and (2) distributing each weekly payment proportionally against those percentages. Here's the synthesized answer drawn from multiple programs:

Phase 1: Establishing the Charge Percentage (Claim Setup)
This is handled by DXCD037S (CICS monetary determination) and UIMB0004 (batch monetary determination). Each employer's share is computed when the claim is initially filed or redetermined.DXCD037S-cbl.json
UIMB0004.md

Core formula:

Employer Charge % = Employer's Total Base-Period Wages ÷ Total Claim Base Wages

Adjustments to the base formula:
Overlap wages — If an employer's wages overlap with a prior claim's base period, the overlap amount is subtracted from the numerator before dividing: (Total Wages − Overlap Wages) ÷ Claim Base Wages
50% cap (NJ employers) — For BC2 and 4.2 form-type employers, the maximum charge amount (AMT-MAX-UI = Charge % × MBA) cannot exceed 50% of the employer's net wages. If it does, the charge % is recalculated as Capped AMT-MAX-UI ÷ MBA
UCX/military exclusion — Under UCX Periods 1 and 3, employers with form type '214' (military) are set to 0% and bear no charge; only NJ state employers share liability. Under Period 2, all employers including military share proportionally.DXCD037S-cbl.json
UIMB0004.md
General Fund employer — The "General Fund" employer (identified by a special FEIN) is skipped during the loop and receives whatever portion of the MBA remains unallocated after all other employers are charged.UIMB0004.md
The per-employer maximum charge amount (AMT-MAX-UI) is then: Charge % × MBA. A running accumulator ensures the sum of all employers' max charges never exceeds the total MBA.DXCD037S-cbl.json
UIMB0004.md

Phase 2: Weekly Payment Distribution (Each Benefit Week)
This is performed by batch program DXCBP500 (called module) and online-path program UIMR0030.DXCBP500.md
UIMR0030-cbl.json

When a payment is issued, the WBA is distributed across the employer table as follows:

For Regular UI payments (transaction code < 100):
Employer Charge = Charge % × WBA (rounded to nearest cent)

For Extended Benefits (EB) payments (transaction code ≥ 100):
Employer Charge = 0.5 × Charge % × WBA (rounded to nearest cent)

This 50% rate reflects the federal/state cost-sharing arrangement for extended benefits.

Capping and distribution loop:
The system iterates through the employer table starting at position 1.
For each employer, it calculates the proportional charge.
Cap against remaining WBA — The calculated charge can never exceed the remaining unallocated portion of the WBA.DXCBP500-cbl.json
Cap against employer's remaining balance — If the calculated charge exceeds the employer's remaining chargeable balance (BAL-EMP-REM), the charge is capped at that balance, the balance goes to zero, and only the capped amount is deducted from the remaining WBA.UIMR0030-cbl.json
DXCBP500-cbl.json
Rounding adjustment — If deducting a charge causes the remaining WBA to go negative (due to rounding), the employer's charge is reduced by the overage and remaining WBA is set to zero.UIMR0030-cbl.json
Last-employer residual — When processing reaches the last employer in the table and a remaining WBA balance still exists (due to rounding across multiple employers), the entire residual is assigned to the last employer, ensuring the full WBA is charged out.DXCBP500.md
DXCBP500-cbl.json
A charge record (DB04 segment) is inserted for each employer with a non-zero charge.DXCBP500.md
Negative payments (credits/reversals):
When the WBA is negative (e.g., an interstate credit adjustment), the system processes employers in reverse order, restoring their balances up to their maximum benefit amount.DXCBP500.md

Key Programs Involved
Table



Program


Role


Environment


DXCD037S	Calculates charge percentages during monetary determination	CICS
UIMB0004	Calculates charge percentages (batch monetary)	Batch
DXCBP500	Distributes weekly WBA across employers, creates charge records	Batch (called module)
UIMR0030	Online employer charging for weekly certification payments	CICS (called by CWC)
UIMB0030	Creates/populates charge segment records	Batch
View more
Note: This is a synthesized summary drawn from multiple source programs. The charge percentage calculation happens once at claim setup (and on redetermination), while the weekly distribution happens each time a payment is issued. The knowledge base documents the batch charging path (DXCBP500) and the online path (UIMR0030); both implement the same core proportional logic but differ in how they handle the EB employer slot and rounding adjustments. If you need the specifics of either path in more detail, let me know.

<!-- atlas:answer v3-Q4 -->

The knowledge base documents several batch programs that perform SSN validation and deceased-status checking. Here's a synthesized summary across the documented programs:

Overview: SSN Validation & Deceased Detection in LOOPS Batch
LOOPS uses the VERIS (Verification Information System) external service — accessed via MQSeries — to validate Social Security Numbers and detect whether a claimant is deceased or retired. Multiple programs participate in this process, each in a different context.

1. UIMB0004 — Batch Monetary Determination (Initial SSN Validation)
During batch monetary determination (new-claim filing), UIMB0004 calls VERIS with the claimant's SSN and date of birth.UIMB0004.md

How it works:

VERIS is called as part of the monetary-determination flow.
If the VERIS completion code is zero (success) and the SSN return code equals '00000110', the claimant is flagged as retired/deceased.
The system collects the three primary claim identifiers (SSN, Program Code, Date of Claim) from the DB01 segment and inserts a record into the UIMV_SSN_RETIRED DB2 table (Table-23).UIMB0004.md
2. UIMB0726 — Accelerated Refunds Master Processing (Multi-Source Deceased Check)
This program performs the most comprehensive deceased-detection workflow, using three sequential sources for each claimant on the Accelerated Refunds Master File.UIMB0726.md

Step A: Input Record Deceased Indicator
The Deceased Indicator on the input master record is checked.
If non-zero → Deceased Flag = 'Y', date of death captured from the master record.
If zero → Deceased Flag = 'N', proceed to next check.UIMB0726.md
Step B: UIMV_SSN_RETIRED Table Lookup (only if not already deceased)
The claimant's SSN is queried against the UIMV_SSN_RETIRED DB2 table.
If found → Deceased Flag = 'Y', date of death set to zeroes (unknown — this table doesn't store the date reliably).
If not found → no change, proceed to VERIS.UIMB0726.md
Step C: VERIS External Service Call (only if not already deceased AND refund > $24.99 AND VERIS is available)
SSN and DOB are passed to the called program VERISB (MQ-based).
On success, if return code = '00000110' → deceased confirmed:
Deceased Flag = 'Y'
Date of death captured from VERIS response field VERIS-RIDDOD
Full response written to VERIS copy file (VERISCPY) for audit
Deceased counter incremented
VERIS Error Handling / Circuit-Breaker:
Connection error (reason 2033): consecutive counter incremented. If ≥ 20 consecutive connection errors → VERIS disabled for remainder of run.
Other errors: consecutive counter reset, total error counter incremented.
Total threshold: if total errors > 75 → VERIS disabled for remainder of run.UIMB0726.md
Deceased Date Cleanup:
Before evaluating deceased status, invalid deceased dates (LOW-VALUES or leading '?' characters) are cleansed to zeroes.UIMB0726.md

3. UIMB0072 — SSN Validity Re-Verification
This program handles retry/re-verification of SSNs that previously failed VERIS validation.UIMB0072.md

How it works:

Queries the SSN Validity table (Table-22, UIMV_SSN_VALIDITY) for active records where:
The prior VERIS call returned a non-zero completion code, or
Dependent SSNs have a validation code of '4' (unresolved)
For each qualifying record, calls the VERISBN MQ service module to re-submit the SSN.
Updates the existing validity record's history indicator from '0' → '1'.
Inserts a new record with the latest VERIS results.
If VERIS returns success and the SSN return code indicates a retired/deceased SSN → inserts a record into the Retired SSN table (Table-23, UIMV_SSN_RETIRED), including the date of death from VERIS-RIDDOD.UIMB0072.md
Writes an output file for downstream reporting (used by DXCVRS2B and DXCVRS3B).
4. DXCBACP1 — Automated Collection Process (Compare/Update)
This program compares a new extract file against the Original Master VSAM and tracks changes — including changes in the Deceased Indicator and Deceased Date.DXCBACP1.md

How it works:

Performs field-level change detection across 16 fields, including Deceased Indicator and Deceased Date.
Cleanses invalid deceased dates (placeholder '????????') before writing to output:
If claimant is deceased (indicator = 1) → replaces with current system date.
If not deceased → replaces with zeroes.
Filters out records with fraudulent SSNs from a hardcoded exclusion list of ~22 SSNs.DXCBACP1.md
5. D2PAD180 — Death Record Processing Job
This JCL job processes death records from external feeds (DABS and FLI categories).D2PAD180.md

How it works:

Combines incoming death data with existing death records from file LAK2LPAP.D2PAD005.DEATH.DTL.
Sorts combined data by SSN, date, and key fields.
Removes duplicate death records using the DEATHDUP program.
Enriches data through database lookups.
Splits final output into 10 separate files by SSN range.
Creates GDG (Generation Data Group) backups for audit and recovery.
6. Supporting MQ Interface Programs
Table



Program


Role


Source


VERISB	Called batch module — MQ interface for VERIS verification (SSN + DOB in, results out)
VERISBN	Called batch module — same MQ interface used by UIMB0072 for re-verification
View more
Both accept an SSN and DOB, submit to an MQ request queue, wait for a response from the reply queue, and return verification results (name, age, state, return codes).

7. Reporting Programs
Table



Program


Report


Source


DXCVRS2B	Verified/pended SSN report by local office (VERIS failures or Post-Randomization SSNs)
DXCVRS3B	Dependent verified SSN listing by local office
View more
Key Data Stores
Table



Table/File


Purpose


UIMV_SSN_RETIRED (Table-23)	Registry of SSNs confirmed retired/deceased by VERIS
UIMV_SSN_VALIDITY (Table-22)	SSN validity records tracking VERIS results and dependent SSN status
LAK2LPAP.D2PAD005.DEATH.DTL	Death detail file (input to D2PAD180)
VERISCPY (output file)	Audit copy of VERIS death confirmation responses
View more
Summary of the Deceased-Detection Cascade
In the documented programs, deceased status is determined by a layered approach:

Input record indicator — did a prior process already flag this claimant?
UIMV_SSN_RETIRED table — was this SSN previously confirmed retired/deceased?
Real-time VERIS call — query the external SSN verification service for current deceased status (return code '00000110').
Each layer short-circuits: once a claimant is confirmed deceased, later checks are skipped.

Important caveat: This describes the programs held in the Daily CA-7 knowledge space. The knowledge base does not document the full upstream flow of how death records initially enter LOOPS (e.g., the SSA Death Master File feed mechanism or the IVR/CICS real-time path for staff-entered death notices). Those processes are separately documented outside the held code slice.

<!-- atlas:answer v3-Q5 -->

The knowledge base does not contain any CICS screen explicitly labeled "16/16" or "16/17" by those exact identifiers. However, the most likely candidates — based on how LOOPS numbers its database segments and the corresponding CICS display screens — are Segment 16 (Remarks) and Segment 17 (Free-Form Text / 26B) of the LOOPS IMS database. These are the two "notes" segments on a claimant's record, and CICS conversations that display claimant data typically present each segment on its own screen panel.

Segment 16 — Remarks (LOOPLE16)
This segment stores structured remarks attached to a claimant's claim. Each remark is a separate segment occurrence under the claimant root.LOOPLX16.txt
LOOPLX16.cpy.csv

Fields in each remark record (copybook LOOPLX16):

Table



Field


Type


Purpose


DB16-REMARKS-SEQUENCE-NUMBER	S999 COMP-3	Orders remarks chronologically
DB16-REMARKS-TITLE	X(25)	Title/heading of the remark
DB16-REMARKS-TEXT	X(250)	Full text content
DB16-LAST-MODIFY-OPERATOR-ID	S9(4) COMP	Who last modified it
DB16-LAST-MODIFY-LOCAL-OFFICE	S9(4) COMP	Office where last modified
DB16-LAST-DATE-MODIFIED	S9(8) COMP	Date of last modification
DB16-ORIG-REMARKS-ENTRY-OP-ID	S9(4) COMP	Who originally entered it
DB16-ORIG-REMARKS-ENTRY-LOCOFF	S9(4) COMP	Office where originally entered
DB16-ORIG-REMARKS-ENTRY-DATE	S9(8) COMP	Date originally entered
View more
How it's used: Both batch and online programs insert remarks here. For example, UIMB0141 inserts "S.A.V.E PEND" or "S.A.V.E RESPONSE" remarks when processing SAVE verification responses, and UIMB0147 inserts batch-generated remarks with operator ID = 0. In online CICS, the SPAD communication area slot 16 (SPADDX2K-LOOPLE16) holds the current remarks segment for the active screen session.UIMB0141.md
UIMB0147.md
DXCD035S-cbl.json

Segment 17 — Free-Form Text / 26B (LOOPLE17)
This segment stores free-form text associated with the claimant, also referred to as "26B" records (likely named after a paper form).DXCBD09R.md

Fields (from the audit report program DXCBD09R):

Table



Field


Purpose


Phrase Number	Identifies a pre-defined phrase or category
26B History Indicator	Tracks historical status
Free-Form Text	The unstructured narrative text itself
Prime Date	Date associated with the text entry
View more
In online CICS, the SPAD communication area slot 17 (SPADDX2K-LOOPLE17) holds this segment.DXCD035S-cbl.json

Key Differences (Synthesized)
Table



Aspect


Segment 16 (Remarks)


Segment 17 (Free-Form Text / 26B)


Structure	Structured: title + text with full modification audit trail	Less structured: phrase-coded free-form narrative
Record size	323 bytes	Varies (documented in LOOPLX17)
Audit tracking	Full: original and last-modified operator, office, date	Minimal: prime date and history indicator
Typical use	System-generated and staff-entered operational remarks (e.g., SAVE pend, non-monetary actions)	Longer narratives and 26B form content
View more
Important Caveat
The exact screen identifiers "16/16" and "16/17" are not confirmed by literal name in the knowledge base documents. What is documented is that Segments 16 and 17 are the remarks and free-form text segments of the LOOPS IMS database, and that CICS online programs load them into SPAD slots 16 and 17 for display. The notation you're using may come from operator training materials or screen navigation guides that are not in the held code slice. If you can point me to where you saw "16/16" and "16/17" referenced, I can try to narrow it down further.

<!-- atlas:answer v3-Q6 -->

LOOPS determines the submission channel of a weekly certification using a simple two-field decision rule based on the Operator ID and Terminal ID stamped on the certification record at entry time. The logic is consistent across both PAYVSAM (payment) and NOPAY (no-payment) record types.

The Channel Classification Rule
The system evaluates the combination of two fields to classify each certification into exactly one of three channels :DXCBDA2R.md
UIMB0440.md

Weekly Certification Channel Classification




Channel


Condition


Meaning


WEB	Operator ID = 9000 AND Terminal ID = '7777'	Claimant self-certified through the internet portal
PHONE/IVR	Operator ID ≠ 9000 AND Terminal ID = '7777'	Claimant self-certified via the automated telephone (IVR) system
Manual P100 (Staff)	Terminal ID ≠ '7777'	Staff member entered the certification manually (e.g., from a P100 paper form)
View more
The key insight is that Terminal ID '7777' is the sentinel value assigned to all self-service channels (both web and phone). The Operator ID of 9000 is then used to distinguish which self-service channel: web uses 9000, IVR does not.DXCBDA2R.md
DXCBDA2R.cbl.md

Where the Fields Come From
The specific fields evaluated depend on whether the record is a PAYVSAM or NOPAY record :DXCBDA2R.cbl.md

PAYVSAM records: BP88-OPERATOR-ID-CERT and BP88-TERMINAL-ID-CERT
NOPAY records: NOPAY-OPERATOR-ID-ENTRY and NOPAY-TERMINAL-ID-ENTRY
Downstream Usage of the Classification
The channel classification is used in multiple programs:

DXCBDA2R (Daily/Weekly Certification Audit Report): Classifies every certification record and produces three separate audit reports — Overall, WEB-only, and PHONE-only — with volume counts broken down by channel.DXCBDA2R.md
UIMB0440 (Payment Extract): Sets the phone indicator field F70-PHONE-IND on the payment output record: '2' = Web/Automated IVR, '1' = Phone, '0' = in-person/other.UIMB0440.md
UIMB0441 (No-Pay Extract): Sets the Phone Claim Indicator F45 to '2' (Web or Automated Phone) or '1' (Regular Phone) using the same logic.UIMB0441.md
Decision Flow (Synthesized)
Evaluate Operator ID + Terminal ID
       │
       ├── Terminal ID = '7777'?
       │      │
       │      ├── YES ──► Operator ID = 9000?
       │      │              │
       │      │              ├── YES ──► WEB
       │      │              └── NO  ──► PHONE/IVR
       │      │
       │      └── NO ──────────────────► MANUAL P100 (Staff)
Important Notes
The classification is applied identically whether the certification resulted in a payment (PAYVSAM) or not (NOPAY).DXCBDA2R.md
The real-time intake processes that originally stamp these Operator ID/Terminal ID values (the IVR system and the web application) live outside the held LOOPS code base. What the mainframe programs document is how they read and interpret the values that were already stamped at entry time.

<!-- atlas:answer v3-Q7 -->

The knowledge base has no system, process, interface, or artifact by the name "JPAY." I searched across both the terminology and the program/JCL documentation and found no match for that term.

Closest Documented Matches
If you might be thinking of one of these, here are documented concepts that relate to payment channels in LOOPS:

Table



Documented Name


What It Is


Where Documented


JMR	A downstream payment release system/process. Referenced in D2PAD149 (debit card claims "not released to regular payments in JMR") and D2FLD506 (FLI debit card payment listing "in JMR")	Daily CA-7 space
Debit Card Migration (UIMT_DEBIT_CARD_MIGRATION table)	DB2 table tracking claimants migrated to a debit card payment method. Program UIMB0889 checks this before processing payments.	Daily CA-7 space
Account Type Code = 'D'	In the Direct Deposit Information table, account type 'D' classifies a claimant's payment method as "DEBIT CARD" (vs. Direct Deposit for any other value). Documented in UIMB0903.	Daily CA-7 space
View more
Possible Explanations
If "JPAY" is a vendor brand name (e.g., the JPay debit card service used in some states for incarcerated individuals' accounts): The knowledge base does not document it by that commercial name. LOOPS tracks debit card payments generically via the account type code and the migration table above — but how those relate to a specific card vendor is not documented in the held code.
If "JPAY" is a typo for "JMR": JMR appears to be the downstream payment release mechanism that LOOPS hands off to. The knowledge base references it but does not contain its own documentation — it lives outside the LOOPS code slice.
Would you like me to look deeper into how LOOPS handles debit card payments specifically, or into the JMR payment release interface? Either may be what you're looking for under a different name.

<!-- atlas:answer v3-Q8 -->

The knowledge base documents municipality (MUNC) code validation across several batch reporting and extract programs. The validation approach varies by claim type — here's the full picture:

Core Validation Rule: Range Check
The primary validation method is a numeric range check against the valid boundary:

Valid Range: 01001 – 76999 (MUNCI-CUR greater than 01000 AND less than 77000)

If a municipality code falls outside this range, it is replaced with the sentinel/default value 77777 (meaning "unknown/invalid municipality").DXCBW39E.md
DXCBW39U.md
DXCBW30U.md

Validation Differs by Claim Type
1. Interstate Claims (Program Code 11 or 12)
No validation is performed. The municipality code is taken directly from the claim record and assigned to the output field without any range check or substitution. Processing immediately exits the classification routine.DXCBW39E.md

Rationale: Interstate claimants reside outside NJ, so their municipality codes follow a different scheme and cannot be validated against NJ ranges.

2. Special Office / Out-of-State Claims (Local Office = 999 or 997, Claim Type 3)
The range check is applied:

Within range (01001–76999): The actual municipality code is retained and assigned to the output record.
Outside range: The municipality code is defaulted to 77777 (both on the current record and as the stored reference value for the SSN group).
If MUNCI-CUR > 01000 AND MUNCI-CUR < 77000
    → Use actual municipality code
Else
    → Set municipality code = 77777
3. Intrastate Claims (Claim Type 1 or 4) — Reference Table Lookup
Intrastate claims undergo a more rigorous validation: the municipality code is matched against a county/municipality reference table (MUNS-NAMES-CODES) using a binary search:

If the municipality code on the claim matches the previous record's code, the table search is skipped and the previously matched position is reused (performance optimization).DXCBW40R.md
DXCBW38R.md
If the code is new/changed, a SEARCH ALL (binary search) finds the municipality number in the reference table.
Match found: The municipality position is saved and used for count accumulation in statistical reports.
No match found: The record is written to an error/exception report (PRINT2-FILE) with the message 'INTRASTATE DATA WITH NO MATCH' and the unmatched counter (UNM-INTRA-CNT) is incremented.DXCBW40R.md
DXCBW38R.md
The error report includes: SSN, Program Code, Transaction Code, Responsible Local Office, Sex, and Municipality Code.DXCBW40R.md
DXCBW38R.md

4. Commuter Claims (Interstate, Claim Type 2)
Commuter claims use a different lookup mechanism: the claim's State FIPS Code is searched against FIPS code ranges in a commuter reference table (COMM-MUNS). A new search is only performed when the FIPS code changes from the previous record.DXCBW38R.md

Summary Table
Municipality Code Validation by Claim Type




Claim Type


Trigger Condition


Validation Method


...


Interstate	Program Code 11 or 12	None — direct pass-through	...
Special Office / Out-of-State	Local Office 999 or 997 (Type 3)	Range check: 01001–76999	...
Intrastate	Claim Type 1 or 4	Binary search of county/municipality reference table	...
Commuter	Claim Type 2	Sequential search by FIPS code range in commuter table	...
View more
Programs Documenting This Logic
Table



Program


Context


Source


DXCBW39E	Weekly journal extract — claim type classification and municipality assignment
DXCBW30E	Weekly statistical reporting — interstate/special claims
DXCBW39U	Weekly extract (update variant) — out-of-state validation with SSN group reference
DXCBW30U	Weekly statistical reporting (update variant) — range validation
DXCBW40R	Claims-by-municipality report — binary search lookup for intrastate
DXCBW38R	Claims-by-municipality report (variant) — intrastate + commuter lookup
View more
Important Notes
The county/municipality reference table (MUNS-NAMES-CODES) used for intrastate lookup is a hardcoded in-memory table within the reporting programs. It contains municipality names, codes, and county assignments for all 21 NJ counties. Its maintenance process is not documented in the knowledge base.
The 77777 default is a sentinel value meaning "unknown/unresolvable municipality" — it appears in output files and reports but is not a real NJ municipality code.
The validation described here is in the context of batch statistical reporting and extract programs. Online CICS validation of municipality codes at claim-entry time may use different mechanisms (e.g., the T120/CODELOOP table), but that specific path is not documented in the held code slice.

conversation: bcb698b1-7fa8-4e24-ba23-8e08c8c1af0d

