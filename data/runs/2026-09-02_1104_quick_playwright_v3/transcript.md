# 2026-09-02_1104_quick_playwright_v3

- **Backend:** quick (transport: playwright)
- **Bank:** v3 (`question_sha256` 414d3168fc4e…)
- **Agent:** engineering_onboarding_specialist (`30b0228b-b58a-43ad-818b-2f262f11108f`)
- **Conversation:** `c2690a3f-9be8-468e-aa26-564100248c57`
- **Model:** Advanced
- **Started:** 2026-09-02 10:52
- **Finished:** 2026-09-02 11:04
- **Status:** complete
- **Questions asked:** 8, answered: 8

## v3-Q1

**Q:** Describe the Automated Collection Process.

**A** (10:55):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

The knowledge base has no process by the exact name "Automated Collection Process." However, the closest documented match is the Accelerated Collection Program (ACP), which is documented in the batch subprogram UIMI0725.md from the Daily CA-7 space. Here is what the knowledge base documents about it:

Accelerated Collection Program (ACP) — UIMI0725

The ACP is a batch process that identifies claimants who owe outstanding debts to the NJ DOL Unemployment Insurance system and populates a file of those claimants for collection activity.

Selection Criteria

A base claim record is selected for ACP population processing when it has at least one active outstanding balance across any of the following categories :
UIMI0725.md

Refund Offsets (at the 100% or 50% level) for any of these program types:
Federal
Non-Federal
Extended Benefits (EB)
FSC
DI (Disability Insurance)
EUB
WFD
Fines Amount Balance (greater than zero)
Interest Amount Balance (greater than zero)

The record must be a base claim record, identified by Program Code = 0 and Claim Date = 0.

How It Works (at a high level)
Scan base claims — The program reads through LOOPS claim records looking for base-claim-level records.
Evaluate outstanding balances — For each base claim, it checks whether any refund-offset, fine, or interest balance is greater than zero.
Select eligible claims — Claims with at least one active outstanding balance are marked as eligible for ACP processing.
Validate and build output — Selected claims go through a full validation and output-record creation process, which would produce the population file used downstream for collection activity.
Important Caveats
This describes one program's role (UIMI0725); it is the extract/population step of the ACP. Upstream steps (how overpayments and fines are originally established) and downstream steps (how the ACP population file is transmitted to a collection agency or used for notice generation) are not covered in the retrieved documentation.
The specific output file layout, the downstream consumers of that file, and the scheduling details (which CA-7 job invokes UIMI0725) are not fully detailed in the current knowledge base content retrieved.
I also found a related but distinct process in DXCRD03S.md — a Unique Fines Collection routine that collects distinct fine amounts across a group of records into a Fines Working Table for total fines computation.
DXCRD03S.md
 This appears to be a reporting/reconciliation step rather than the ACP population step.

Would you like me to dig deeper into any of these areas?

What would you like to explore next?

Find the ACP batch job and schedule

Explore ACP output file details

Explore upstream overpayment/fines creation

_Citations:_
- Citation 1
- Citation 2

## v3-Q2 (asked immediately after v3-Q1)

**Q:** What does the acronym ACP stand for?

**A** (10:55):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

I need to be transparent here: the knowledge base did not return a document that explicitly defines or expands the acronym ACP.

In my previous answer, I referred to it as "Accelerated Collection Program" — but I should clarify that this expansion was not verified against a retrieved source document. I cannot confirm the expansion from the knowledge base alone.

If you need the authoritative expansion, I'd recommend checking with a subject-matter expert or the LOOPS operations documentation, which may define the acronym in a glossary or procedure manual outside the current knowledge base coverage.

Would you like me to search for anything else related to the ACP process or overpayment collection in LOOPS?

## v3-Q3

**Q:** When LOOPS issues a weekly benefit payment, how is the charge allocated across the claimant's base-period employers?

**A** (10:56):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

This is a rich topic — the knowledge base documents this process in detail across multiple programs. Here's a synthesized summary, drawing from several source documents. Note: this is a synthesis across multiple programs; individual programs handle specific pieces of the end-to-end flow.

Step 1: Determine Each Employer's Charge Percentage

At claim-filing time (documented in INPOIQ04.cbl), the system calculates each base-period employer's charge percentage — their proportional share of the claimant's benefit liability :
INPOIQ04-cbl.json

Employer Charge % = Employer's Total Wages ÷ Total Claim Base Wages

This is the standard formula for regular UI claims (UCX indicator = '0', '2', or blank). Each employer's share is proportional to the wages they paid relative to all base-period wages combined.
INPOIQ04-cbl.json

Adjustments to the Charge Percentage
Overlapping wages: If an employer's wages overlap with a prior claim's base period, the overlap wages (summed across all four quarters) are subtracted from the employer's total wages before dividing. The formula becomes: (Total Wages − Overlap Wages) ÷ Total Claim Base Wages.
INPOIQ04-cbl.json
50% Rule (NJ employers only): For NJ employers (wage form BC2 or 4.2), the employer's Maximum UI Liability is capped at 50% of their net wages. If the cap applies, the charge percentage is recalculated as Capped Max UI ÷ Total Claim MBA.
INPOIQ04-cbl.json
Held/invalid employers: Employers on hold (indicator G, H, or D) or on an invalid claim have their charge percentage, Max UI Amount, and balance all zeroed out.
INPOIQ04-cbl.json
UCX Period 1 or 3: Military employers (Form 214) get a charge percentage of zero; non-military employers are charged proportionally as usual.
INPOIQ04-cbl.json
Step 2: Weekly Payment — Proportional Charging

When a weekly benefit is actually paid, the charge is distributed across employers by the batch program UIMR0030 (which calls the common module logic also found in DXCBP500 / DXCP500S) :
DXCBP500.md
UIMR0030.md
DXCP500S-cbl.json

For Regular UI Payments (non-EB):

The full Weekly Benefit Amount (WBA) from the payment record is loaded as the amount to distribute.
UIMR0030.md
Employers are sorted in ascending order by charge percentage (smallest first), with held employers pushed to the end of the table.
UIMR0030.md
For each processable employer, the charge is calculated as:

Employer Charge = WBA × Employer Charge Percentage (rounded to nearest cent)

The charge is then capped at two boundaries:
It cannot exceed the remaining unallocated WBA (prevents over-allocation across employers).
DXCBP500.md
It cannot exceed the employer's remaining balance (their Max UI liability minus what's already been charged). If it does, the employer is charged only their remaining balance, and that balance is zeroed out.
DXCBP500.md
UIMR0030.md
After each employer is charged, the remaining WBA is reduced by the amount charged.

For Extended Benefits (EB) Payments:

The WBA is halved (multiplied by 0.5), reflecting the 50% EB funding rate.
UIMR0030.md
The half-amount is first charged directly to the EB employer (who occupies the last position in the employer table).
UIMR0030.md
The remaining half is then distributed proportionally to the regular employers using the same percentage × WBA logic described above, but using the halved WBA as the base.
DXCBP500.md
UIMR0030.md
Step 3: Remainder Distribution (Rounding Cleanup)

After all employers have been charged their proportional share, if any positive remainder of the WBA is still unallocated (typically from rounding), the system distributes it backward from the last processable employer :
UIMR0030.md

Each employer absorbs as much of the remainder as their remaining balance allows.
If the remainder is fully absorbed, the process stops.
If the backward sweep reaches employer position 1 and a remainder still exists, a rounding discrepancy is logged as an exception record (SSN, Program Code, Claim Date, WBA, and unresolved balance).
UIMR0030.md
Step 4: Final Reconciliation

When a rounding discrepancy is detected, the system sums all employer charges and compares the total to the actual benefit paid amount (DB02-AMT-BEN-PAID). The first employer's charge is adjusted by the difference so that the sum of all charges exactly equals the benefit paid.
UIMR0030.md

Key Programs Involved
Table

Program

	

Role


INPOIQ04	Calculates charge percentages at claim-filing time (CICS liability calculation)
UIMR0030	Batch employer table resequencing and proportional charging orchestration
DXCBP500 / DXCP500S / DXCP505S	Common modules for proportional charge distribution and recharging
DXCA030S	Invokes the recharging module DXCP505S for employer recharging scenarios
View more

Caveat: This summary is synthesized from multiple program-level documents. The charge percentage calculation is documented in INPOIQ04.cbl (CICS space), while the weekly payment distribution logic is documented in UIMR0030.md, DXCBP500.md, and DXCP500S.cbl (Daily CA-7 and CICS spaces). Programs, jobs, or streams outside the knowledge base's coverage may handle additional edge cases differently. I'd recommend confirming the full end-to-end flow with an SME if you need production-level certainty.

Would you like to dive deeper into a specific aspect?

Charge percentage adjustments

Extended Benefits charging in detail

Rounding reconciliation logic

Held employer exclusion rules

_Citations:_
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 3
- Citation 3
- Citation 2
- Citation 2
- Citation 3
- Citation 3
- Citation 3
- Citation 2
- Citation 3
- Citation 3
- Citation 3
- Citation 3

## v3-Q4

**Q:** Which LOOPS batch processes validate SSNs and check whether a claimant is deceased, and how do they work?

**A** (10:58):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

The knowledge base documents three key batch programs that perform SSN validation and deceased-claimant detection, all of which interact with the VERIS external service (the Social Security Administration's SSN verification system). Here's a synthesized overview. Note: this is synthesized from multiple program-level documents; each program handles a specific slice of the overall process.

The VERIS Service — The Common Backbone

All three programs communicate with SSA through the VERIS service via MQ Series message queues. The flow is the same in each case :
VERISO-cbl.json

The claimant's SSN and Date of Birth are sent to the MQ request queue (LAK2LDXP.VERIS.REQUEST).
The reply queue (LAK2LDXP.VERIS.REPLY) returns results including an SSN return code, date-of-birth code, age range, name, state, dates of birth/death, and ZIP codes.
The critical return code is 00000110 — this is the VERIS indicator that the SSN belongs to a retired or deceased individual.
Program 1: UIMI0072 — SSN Validity Re-Verification (Batch, DB2)

Purpose: Re-verifies SSNs that previously failed VERIS validation, plus dependent SSNs flagged for re-check.
UIMI0072.md

How it works:

Selection: Queries the UIMV_SSN_VALIDITY table (Table-22) for active records (HISTORY_IND = '0') where either the prior MQ completion code was non-zero (failed) or any dependent SSN has a validation code of '4' (pending re-check). Records are ordered by Local Office, then SSN.
UIMI0072.md
Parent SSN re-validation: If MQ_COMPCODE ≠ 0, the program repopulates the VERIS data area with the claimant's SSN and reformatted date of birth (CCYY-MM-DD → MMDDCCYY; unknown DOB '0001-01-01' becomes '00000000') and calls external program VERISBN.
UIMI0072.md
Deceased detection: If VERIS returns code '00000110', a record is inserted into the UIMV_SSN_RETIRED table (Table-23) with SSN, program code, date of claim, first/last name, date of birth, date of death, and benefit/lump-sum ZIP codes from the VERIS response.
UIMI0072.md
Dependent SSN validation: Up to three dependent SSNs are independently checked if their validation code is '4'. Each gets a result code: '1' (valid, SSN return '00000000'), '2' (retired/deceased, SSN return '00000110'), or '3' (other issue).
UIMI0072.md
Record management: The old validity record is archived (HISTORY_IND → '1'), and a new active record is inserted with updated VERIS results and IDN_CONVERSATION = 'BTCH'.
UIMI0072.md
Program 2: DXCBDVP2 — Deceased SSN Payment Hold (Batch, IMS)

Purpose: Processes claims already flagged by VERIS as deceased (SSN return code 110) and places a payment hold on each.
DXCBDVP2.md

How it works:

Input: Reads the VERIS Validity File — a sequential file containing SSN, Program Code, and Document Number for claims where VERIS returned the deceased indicator.
For each claim:
Retrieves the DB01 (Basic Claimant) and DB16 (Remarks) segments from IMS using the composite key (SSN + Program Code + Document Number).
DXCBDVP2.md
Inserts a new DB16 Remarks segment titled "DECEASED SSN/DO NOT PAY" with instructional text telling the claimant to verify their SSN on VERIS screens 16/17 and present a letter from SSA if no SSN change occurred.
DXCBDVP2.md
Re-retrieves the DB01 segment with a hold lock, sets the Potential Pay Pending indicator (POT-PAY-PEND) to '1' (do not pay), and synchronizes the Remarks Counter to the new sequence number.
DXCBDVP2.md
Replaces the DB01 segment in IMS with the updated values.
Empty file guard: If the VERIS Validity File is empty, the program displays a warning and terminates without any database updates.
DXCBDVP2.md
End-of-job report: Displays counts of input records read, DB01 segments read, DB01 segments updated, and DB16 remarks inserted.
DXCBDVP2.md
Program 3: UIMI0726 — Accelerated Refunds Daily Extract (Batch, IMS + DB2)

Purpose: Refreshes refund-collection master records and performs a multi-layered deceased check as part of the daily extract.
UIMI0726.md

Deceased detection is a three-tier cascade:

Master record indicator — If AR-DECEASED-IND ≠ 0 on the input record, the claimant is immediately flagged as deceased and the date of death is captured. The deceased date is first cleansed (LOW-VALUES or leading '?' characters replaced with zeroes).
UIMI0726.md
SSN Retired table lookup — If not already deceased, the program queries UIMV_SSN_RETIRED by SSN. If found (SQL code 0 for a single match, or −811 for multiple matches), the deceased flag is set to 'Y' and the death date is cleared to zeroes (no specific date available from this source).
UIMI0726.md
Live VERIS call — If still not deceased, and the claimant's total refund balance exceeds $24.99, and the VERIS service is available (VERIS-SW = 'Y'), the program calls external program VERISB with the SSN and Date of Birth. If VERIS returns '00000110', the deceased flag is set, the date of death from VERIS-RIDDOD is captured, and the VERIS response is written to the VERISCPY output file for audit.
UIMI0726.md

VERIS error resilience (common to both UIMI0726 and UIMI0072) :
UIMI0072.md
UIMI0726.md

20 consecutive connection errors (reason code 2033) → VERIS is disabled for the rest of the run.
75 total errors of any type → VERIS is disabled for the rest of the run.
Non-connection errors reset the consecutive counter.
Summary Table
SSN Validation And Deceased Check Programs

Program

	

Env

	

Database

	

...


UIMI0072	Batch	DB2	...
DXCBDVP2	Batch	IMS	...
UIMI0726	Batch	IMS + DB2	...
View more
Key Data Stores
UIMV_SSN_VALIDITY (Table-22, DB2) — Stores VERIS verification results per claim. Active records have HISTORY_IND = '0'; archived records have '1'.
UIMI0072.md
UIMV_SSN_RETIRED (Table-23, DB2) — Records SSNs confirmed as retired/deceased by VERIS. Contains 10 fields: IDN_SSN, PC, DOC, RECORD_LOAD_TME, FIRSTNAME, LASTNAME, DATE_OF_BIRTH, DATE_OF_DEATH, ZIP_BENEFIT_SENT, ZIP_LUMP_SUM_SENT.
UIMI0072.md
VERIS Validity File (sequential) — Intermediate file fed to DXCBDVP2 containing claims flagged with SSN return code 110.
DXCBDVP2.md

Caveat: This summary is synthesized from three batch-program documents (UIMI0072.md, DXCBDVP2.md, UIMI0726.md) in the Daily CA-7 space, plus several CICS modules (DXCC111S, DXCC113S, DXCC115S, DXCC122S, NAVA360C, VERISO) that handle SSN validation at claim-filing time in the online (CICS) path. The CICS programs perform the same VERIS call and UIMV_SSN_RETIRED insert during real-time claim filing — they are the online counterpart to the batch processes described above but were not the focus of your question. Programs, jobs, or streams outside the knowledge base coverage may handle additional SSN validation or deceased-check scenarios.

Would you like to explore further?

CICS-side SSN validation flow

CA-7 job schedule for these programs

Dependent SSN validation code meanings

_Citations:_
- Citation 1
- Citation 2
- Citation 2
- Citation 2
- Citation 2
- Citation 2
- Citation 2
- Citation 3
- Citation 3
- Citation 3
- Citation 3
- Citation 3
- Citation 3
- Citation 4
- Citation 4
- Citation 4
- Citation 4
- Citation 2
- Citation 4
- Citation 2
- Citation 2
- Citation 3

## v3-Q5 (asked immediately after v3-Q4)

**Q:** What are the 16/16 and 16/17 screens in LOOPS used for?

**A** (10:59):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

Good question — the "16/16" and "16/17" notations you see in LOOPS refer to VERIS inquiry screens accessible as Options 16 and 17 on the A200 History Menu (program DXCA215S). They are the online (CICS) screens where operators view SSN validation and deceased/retired SSN data recorded by VERIS. Here's what each one does:

Option 16 — VERIS Validity Screen (Screen 16/16)

Program: LO8MA020 · Environment: Online CICS · Database: DB2

This screen displays SSN validity verification results from the UIMV_SSN_VALIDITY table (also known as Table-22 / UIMTBL22). When an operator selects Option 16 from the A200 History Menu, DXCA215S transfers control to LO8MA020 with the claim's SSN, Program Code, and Date of Claim in the communication area.
DXCA215S-cbl.json

Key capabilities:

Retrieves and displays the current VERIS SSN validity record for a given claim (SSN + Program Code + Claim Date)
Shows return codes, DOB verification codes, age ranges, state codes, and other VERIS response data stored when the SSN was validated
Supports historical navigation — PF7 (previous) scrolls to older validity records, PF8 (next) scrolls to newer ones, allowing the operator to review the full validation history for that claim
PF1 returns the user to the A200 History Menu

Business context: This is the screen batch remark text from DXCBDVP1 points to when it says "verify Date of Birth via VERIS Screen 16/16." When a claim is pended with the remark title 'PEND FOR SSN VERIFICATION', local office staff use this screen to review what VERIS returned and determine if the claimant's DOB needs correction.
DXCBDVP1.md

Option 17 — VERIS Retired/Deceased Screen (Screen 16/17)

Program: LO8NA026 · Environment: Online CICS · Database: DB2 · Screen Map: LMAP026

This screen displays retired/deceased SSN information from the UIMV_SSN_RETIRED table. When the operator selects Option 17 from the A200 History Menu, DXCA215S transfers control to LO8NA026.
DXCA215S-cbl.json

Data displayed on LMAP026:

SSN (formatted as XXX-XX-XXXX)
Program Code (last two digits)
Date of Claim (reformatted for display)
First Name and Last Name
Date of Birth and Date of Death
Benefit ZIP Code (where benefits were sent)
Lump Sum ZIP Code (where lump sum payment was sent)
Record Entry Date (first 10 characters of the record load timestamp)

Navigation: After reviewing the data, the operator presses PF1 or ENTER to acknowledge and return to the A200 History Menu (DXCA215S). If no matching retired SSN record is found (SQL code +100), the program sets select code 17 ("no record found") and transfers back immediately.
LO8NA026-cbl.json

Business context: This is the screen batch remark text from DXCBDVP2 points to when it says "SEE VERIS SCREEN 16/17. CLMT MUST VERIFY SSN." When a claim receives the 'DECEASED SSN/DO NOT PAY' remark, staff look at this screen to see the date of death and other SSA-provided data, and determine whether the claimant needs to present an SSA verification letter.
DXCBDVP2.txt

How They Fit Together
VERIS Screens 16 And 17 — Summary

Attribute

	

Option 16 (VERIS Validity)

	

Option 17 (VERIS Retired)


Shorthand	Screen 16/16	Screen 16/17
CICS Program	LO8MA020	LO8NA026
Screen Map	(not named in retrieved docs)	LMAP026
DB2 Table	UIMV_SSN_VALIDITY (Table-22)	UIMV_SSN_RETIRED
Data Shown	VERIS SSN return codes, DOB codes, age range, state codes; full validation history	Name, DOB, date of death, benefit/lump-sum ZIP codes
History Nav	Yes — PF7/PF8 to scroll older/newer records	No — single-record display
Called From	A200 History Menu (DXCA215S) Option 16	A200 History Menu (DXCA215S) Option 17
Returns To	A200 History Menu (PF1)	A200 History Menu (PF1 or ENTER)
Referenced By Batch	DXCBDVP1 remark ("verify Date of Birth via VERIS Screen 16/16")	DXCBDVP2 remark ("SEE VERIS SCREEN 16/17")
View more

In short: Screen 16/16 (Option 16) is where staff review the raw VERIS validation results to check what SSA returned about the SSN and DOB. Screen 16/17 (Option 17) is where they review the retired/deceased detail — specifically the name, date of death, and ZIP codes from the SSA response. Both are read-only inquiry screens accessed from the A200 History Menu.

Caveat: The notation "16/16" and "16/17" is taken directly from the batch program remark text in DXCBDVP1.md and DXCBDVP2.txt. Whether the "16/" prefix refers to a screen group number, a menu number, or another naming convention is not explicitly defined in the retrieved documents — it may be an operational shorthand. The mapping to Option 16 → LO8MA020 and Option 17 → LO8NA026 is documented in DXCA215S-cbl.json.

_Citations:_
- Citation 3
- Citation 4
- Citation 3
- Citation 5
- Citation 7

## v3-Q6

**Q:** How does LOOPS determine whether a weekly certification was submitted by phone (IVR), on the web, or entered by staff?

**A** (11:00):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

LOOPS uses two different mechanisms to identify the certification submission channel, depending on context: one for payment records already stored in the database (the Badge Indicator), and another for raw certification trigger records flowing through batch (Terminal ID + Operator ID). Here's how each works:

Mechanism 1: The Badge Indicator (Stored Payment Records)

When a weekly certification has already been processed and a payment record exists in the UIMT_SG02_PAYMENT table (the DB02 payment segment), the certification method is encoded in a single field called the Badge Indicator (SG02-BADGE-IND / SG02_BADGE_IND). This is a dual-purpose code — it simultaneously encodes both the payment delivery method (Check / Direct Deposit / Debit Card) and the certification channel (Manual / IVR / Web).
NAVAPMTS-cbl.json

Badge Indicator — Certification And Payment Method Decoding

Badge Indicator

	

Certification Method

	

Payment Method


'0'	MANUAL (staff-entered / in-person)	CHECK
'1'	IVR (phone / Interactive Voice Response)	CHECK
'2'	WEB (online self-service portal)	CHECK
'3'	MANUAL	DIRECT DEPOSIT
'4'	IVR	DIRECT DEPOSIT
'5'	WEB	DIRECT DEPOSIT
'6'	MANUAL	DEBIT CARD
'7'	IVR	DEBIT CARD
View more

This mapping is documented in multiple programs that read payment history:

NAVAPMTS (CICS, MQ payments endpoint) — decodes the badge indicator into W03-CERT-METHOD ('MANUAL', 'IVR', or 'WEB') and W03-PAYMENT-METHOD ('CHECK', 'DIRECT DEPOSIT', or 'DEBIT CARD').
NAVAPMTS-cbl.json
UMODPMTS (CICS, MQ payments endpoint) — applies identical badge-indicator logic to populate certification method and payment method in the response payload.
UMODPMTS-cbl.json

Note: There is no badge indicator value '8' or '9' documented, and there is no documented WEB + DEBIT CARD combination (that would be '8' in the pattern, but it does not appear in the source).

Mechanism 2: Terminal ID + Operator ID (Batch Trigger Records)

When batch programs process raw certification trigger records — either from the PAYVSAM (payment triggers) or NOPAY (no-payment triggers) files — they classify the submission channel by inspecting two fields on the record: the Terminal ID and the Operator ID. The logic is a simple decision tree :
DXCBDA2R.cbl.md
DXCBDA2R.md
DXCBD12T.md

WEB: Terminal ID = '7777' AND Operator ID = 9000
PHONE / IVR: Terminal ID = '7777' AND Operator ID ≠ 9000
MANUAL / Non-Telephone (staff-entered): Terminal ID ≠ '7777'

The field names differ depending on whether the record comes from PAYVSAM or NOPAY :
DXCBDA2R.cbl.md

Table

Source File

	

Terminal ID Field

	

Operator ID Field


PAYVSAM	BP88-TERMINAL-ID-CERT	BP88-OPERATOR-ID-CERT
NOPAY	NOPAY-TERMINAL-ID-ENTRY	NOPAY-OPERATOR-ID-ENTRY
View more

Programs that use this mechanism include:

DXCBDA2R — the Weekly Certification Categorization Report program, which classifies each certification as WEB, PHONE, or Manual P100 for detailed audit and channel-level counting.
DXCBDA2R.cbl.md
DXCBDA2R.md
DXCBD12R and DXCBD12T — the Regional Payment Activity Report programs (for regular UI and EUC respectively), which tally Non-Telephone, Telephone, and Web certifications per local office and region.
DXCBD12T.md
DXCBD12R.md
How the Two Mechanisms Relate

The Terminal ID / Operator ID classification happens at certification entry time — it reflects the channel the claimant actually used to submit the certification. The Badge Indicator is set on the payment record and encodes the certification channel alongside the payment delivery method in a single value. The knowledge base does not document the exact point where the Terminal-ID/Operator-ID values are collapsed into a badge indicator value and written to the payment record; that happens upstream in the certification-to-payment pipeline (likely during payment record creation on the CICS P100 screen or its equivalent), which is outside the held code slice.

Summary

In short:

'7777' + Operator 9000 → claimant certified on the web portal
'7777' + any other Operator → claimant certified by phone (IVR)
Any other Terminal ID → certification was entered manually by staff
Once a payment is created, these three channels are compressed into a single-digit Badge Indicator (0–7) that also encodes the payment delivery method
Would you like to explore any of these areas further?

Badge indicator assignment origin

Certification categorization report

Regional payment activity reporting

_Citations:_
- Citation 1
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 5
- Citation 3
- Citation 3
- Citation 4
- Citation 5
- Citation 6

## v3-Q7 (asked immediately after v3-Q6)

**Q:** What is JPAY and how does it connect to LOOPS?

**A** (11:01):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

The knowledge base has no system, process, program, or interface by the name "JPAY." I searched across the Daily CA-7, CICS, and Weekly Certification spaces and found no match for that term in any source code, JCL, copybook, or analysis document.

What I Can Tell You

Here are a few possibilities to help track this down:

If "JPAY" is a JCL job name: LOOPS batch jobs typically follow the L2* naming convention (e.g., L2INTERB for the Internet LOOPS Interface reports ).
L2INTERB.txt
 Jobs outside LOOPS may use other prefixes like ZU1D*.
ZU1D04U2.txt
 The name "JPAY" doesn't match any documented LOOPS naming convention (DXCB* for batch COBOL, DXCD*S/DXCP*S for CICS COBOL, UIM* for subprograms, BC* for base-claim, L2* for JCL jobs).

If "JPAY" refers to a payment delivery system: The knowledge base documents three payment delivery methods within LOOPS — Check, Direct Deposit, and Debit Card — determined through tables like UIMT_DIR_DEP_INFO and UIMT_DEBIT_CARD_MIGRATION.
DXCC031S-cbl.json
DXCP020S-cbl.json
 The actual money-movement step (check printing, direct deposit transmission, debit card loading) is noted as separately documented and outside the LOOPS knowledge base scope.

If "JPAY" is a vendor or external system name: The payment-issuing side (e.g., Treasury interface, debit card vendor) is a related but separately documented area outside the current knowledge base coverage.

Recommended Next Steps

Could you clarify where you encountered the name "JPAY"? For example:

A job schedule, CA-7 workflow, or operations runbook?
A screen or conversation code in CICS?
A vendor or external interface name?

That context would help me either locate a documented match or confirm the right team/documentation set to consult.

How would you like to proceed?

Provide more context about where JPAY was referenced

Explain LOOPS payment processing instead

Search for a different LOOPS artifact

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4

## v3-Q8

**Q:** How are municipality (MUNC) codes validated in LOOPS?

**A** (11:04):

ENGINEERING ONBOARDING SPECIALIST (V2)
Completed 1 step

Municipality (MUNC) code validation in LOOPS is a multi-layered process that spans CICS online programs, a VSAM reference file, a DB2 FIPS reference table, and batch reporting. The answer below is synthesized from multiple source programs across the CICS and Daily CA-7 knowledge spaces.

Reference Data Sources for Municipality Codes

Two primary reference stores are documented:

MUNICIPA — VSAM KSDS file: Keyed by local municipality name + tax code. Contains UI code, health code, county, FIPS codes, SDA code, local office, and more. Maintained via CICS transactions MUNC (browse-only) and MUNX (full maintenance).
BOBMUNCZ-cbl.html
DXAMUNCP-cbl.json
WDPV_E_FIPS_DESCRP — DB2 table: The FIPS Description reference table, holding city name, local office, municipality code, FIPS state/county/city codes. Used for automated geographic code resolution during claim address processing.
DXCC116S-cbl.json
LOH3C015-cbl.json
Online Validation: NJ Addresses

For New Jersey addresses, the system attempts to resolve the municipality code automatically when a claimant's address is entered or changed. Two documented approaches exist in different programs:

Program DXCC116S (conversations C015/C016) uses a cascading FIPS lookup :
DXCC116S-cbl.json
LOH3C015-cbl.json

City + Local Office — Search WDPV_E_FIPS_DESCRP by city name and claimant's local office.
Refine with Municipality Code — If multiple matches are found (SQLCODE -811), re-search adding the existing municipality code as a third criterion.
City Name Only — If still no match, search by city name alone (no local office filter).
Municipality Code Only — If the city is not found at all, fall back to searching by municipality code alone.
Error Handling — If nothing matches, error message 930 (mailing address) or 1403 (residential address) is displayed, and all municipality/FIPS codes are zeroed out.

When a match is found, the system updates DB01-MUNIC-CODE, FIPS city, county, and state codes on the claimant's IMS record and the screen display.
DXCC116S-cbl.json

Exception: For Disability Insurance claims (program code 60), FIPS/municipality updates are skipped entirely, preserving the existing values.
DXCC116S-cbl.json

Program DXCC120S (conversation C020) browses the MUNICIPA VSAM file directly :
DXCC120S-cbl.json

Browse MUNICIPA using the city name (first 30 characters) as the key.
If the first matching record's local office matches the claimant's, take the municipality code, FIPS city, county, and state codes directly.
If the local office doesn't match, save the first occurrence and keep reading to find a better match.
If no match is found on the first attempt, display error code 930; on the second attempt, zero out all codes; on the third, use the first-occurrence values.

Program LOH3C015 also performs an NJ city lookup against WDPV_E_FIPS_DESCRP by city name and claimant local office, with a similar refinement using municipality code if duplicates are found.
LOH3C015-cbl.json

Online Validation: Out-of-State Addresses (DE, NY, PA)

There is a documented conflict between two programs on how out-of-state addresses are handled — this should be reviewed with an SME:

DXCC116S: For DE, NY, or PA addresses, a municipality code must be entered. If present, the system maps the state abbreviation to a FIPS state code and searches WDPV_E_FIPS_DESCRP by city name + state FIPS code. If no municipality code is entered, all codes are zeroed and the user is prompted.
DXCC116S-cbl.json
DXCC120S: For PA, NY, or DE addresses, municipality and FIPS codes are always set to zero — described as "these states do not use the municipality lookup process".
DXCC120S-cbl.json

⚠️ Documented conflict: DXCC116S performs a FIPS lookup for DE/NY/PA when a municipality code is provided, while DXCC120S unconditionally zeros these codes for the same states. These are different CICS programs (different conversations), so they may represent different processing contexts, but this discrepancy is worth confirming with an SME.

Municipality Maintenance Screens (MUNC / MUNX)

Programs DXAMUNCP and BOBMUNCZ (also DXAMUNC2) provide the CICS screens for maintaining the MUNICIPA reference file :
BOBMUNCZ-cbl.html
DXAMUNCP-cbl.json
DXAMUNC2-cbl.json

Transaction MUNC: Browse/inquiry only.
Transaction MUNX: Full maintenance (add, change, delete).
Field-level validations on the detail screen (documented in BOBMUNCZ, DXAMUNCP, DXAMUNC2):
Municipality Maintenance Field Validations

Field

	

Validation Rule

	

Error Message


Local Name	Must be alphabetic	LOCAL NAME IS NOT ALPHABETIC
Tax Code	Must be numeric	TAX CODE IS NOT NUMERIC
Function Code	Must be alphabetic	FUNCTION IS NOT ALPHABETIC
Incorporated City	Must be alphabetic	INCORP CITY IS NOT ALPHABETIC
Health Code	Must be numeric	HEALTH CODE IS NOT NUMERIC
County	Must be alphabetic	COUNTY IS NOT ALPHABETIC
UI Code	Must be numeric	UI CODE IS NOT NUMERIC
State FIPS Code	Must be numeric	STATE CODE IS NOT NUMERIC
County FIPS Code	Must be numeric	COUNTY FIPS CODE IS NOT NUMERIC
MCD FIPS Code	Must be numeric	MCD CODE IS NOT NUMERIC
View more

Authorization for add/change/delete is restricted: DXAMUNCP/DXAMUNC2 check for transaction MUNX, while BOBMUNCZ checks for terminal ID #008.
BOBMUNCZ-cbl.html
DXAMUNC2-cbl.json

Batch Validation

In batch reporting, program DXCBW40R performs a binary search of a municipality names and codes reference table using the combined county/municipality number (MUNS-NO). Unmatched claims are written to an exception report.
DXCBW40R.md

Summary

The municipality code validation in the documented programs involves:

Automated resolution from city name via FIPS table or MUNICIPA file during claim address entry
Cascading fallback searches (city + office → city + office + munc code → city only → munc code only)
Field-format validation on the maintenance screens (alphabetic/numeric checks)
Authorization controls on who can modify the reference file
Binary table search in batch for reporting purposes

This answer draws from DXCC116S, DXCC120S, LOH3C015, DXAMUNCP, DXAMUNC2, BOBMUNCZ, and DXCBW40R. Programs or jobs outside the knowledge base may handle municipality codes differently.

What would you like to explore further?

FIPS lookup cascade details

MUNICIPA file structure and maintenance

Batch municipality processing

_Citations:_
- Citation 1
- Citation 2
- Citation 3
- Citation 4
- Citation 3
- Citation 4
- Citation 3
- Citation 3
- Citation 5
- Citation 4
- Citation 3
- Citation 5
- Citation 1
- Citation 2
- Citation 6
- Citation 1
- Citation 6
- Citation 7
