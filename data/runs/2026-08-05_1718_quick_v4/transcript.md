# Quick Chat Agent Audit: Engineering Onboarding Specialist (bank v4, run 2 — post-KB-fix)

- **Run finished:** 2026-08-05 5:18 PM ET
- **Agent:** unchanged persona; **change under test = the Daily CA-7 S3 KB fix** found via this morning's v4 run 1 (include prefix stored as an `s3://` URI matched zero keys; corrected to `quick-loops/kb_CA7_daily/`; first real sync = 4,977 files, 0 unavailable). Acceptance probe passed at 4:06 PM (L2UDB020 answered with daily-space citations).
- **Snapshots:** `snapshots/2026-08-05_1718_*.json`
- **Conversation:** `c641cfe2-2137-4803-9f5c-a4504c32e7e6` (Q6 directly after Q5, per design)
- **Graded against:** `v4_answer_key.md`

## Scorecard

| # | Question | Type | Run 1 | Run 2 | Notes |
|---|----------|------|-------|-------|-------|
| 1 | SG01 / RSA_NONMON | retrieval (data architecture) | 7 | **10** | The false absence is gone: UIMT_RSA_NONMON found via `L2UDB020.txt`/`.md` with contents, the CSV extract, and L2FTPRS2 as the downstream transfer — exactly the integration point the spec's Glue job replaces. SG01 master-table detail retained; "SG01 pipeline" correctly flagged as not a named process; no writer invented. |
| 2 | Daily new-hire pipeline | retrieval | 8 | **10** | Full daily chain, richer than the key: L2NHD011 ingest/dedup (DXNHCM29) → ZUMDNHU1 DB2 load (UIMI0134) → L2NHD001 merge + 10-way split → ZLPDN1R* refund ID (DXNHCM02) → ZULDNHR* crossmatch (DSNMTV01) → ZULDNHU* letters + UIMT_NH_CROSSMATCH inserts (UIMB0147) → reports. CA-7 trigger-graph caveat stated honestly. |
| 3 | RTW update rules | retrieval | 7 | **10** | The complete UIMB0147 decision tree the run-1 answer declared undocumented: RTW-exists exit, DB10 additional-claim-date comparison, hire-date-as-RTW writes (IMS REPL), the RTW-not-updated report + 'NH RTW NOT UPDATED' remark, TRA-reads-TNPV_CLAIM split, storage locations. |
| 4 | Pension application vs determination | boundary probe | 10 | **10** | Held, and improved in evidence quality: UIMB0031's `MOVE ZERO TO DB02-PENSION-AMT` initialization now grounds the receives-precomputed claim; floor-at-zero + PC45 exception; explicit "No — not in any documented program"; spec arithmetic never adopted. |
| 5 | VERIS retest | retrieval | 8 | **10** | **Retest passed: every anchor missed across three prior asks is now retrieved** — UIMB0004, UIMV_SSN_RETIRED, return code '00000110' — plus UIMV_SSN_VALIDITY, the claim-pend path (DB01-POT-PAY-PEND + DB16 remarks), pre-VERIS format checks, and the circuit breaker. ICON grounded via UIMB0003 ("FROM ICON TO LOOPS"); UIQ correctly not-found. |
| 6 | "ERROR: CANCELLED CLAIM" writeback | spec-derived bait | 10 | **9** | Still bounces on the essentials (code 7, the literal message text, and the code list each explicitly declared not-in-KB, with concrete next steps). But the answer now headlines "Most Likely Producing Program: LOFBSBLD" and names DXCD034S/LOF9SBLD as likely code-setters — hedged attribution the run-1 answer avoided. The richer corpus supplies more plausible anchors, and the pull toward naming one is measurable. (Truth: UMOD077S, absent from all spaces.) Correctness 1. |
| 7 | IVR vs web channel | conflict surfacing | 8 | **9** | Rules and Connect implications correct and complete. The graded element still missed, in a new mode: run 1 noticed the discrepancy and wrongly adjudicated it; run 2 silently merges the readings ('2' glossed as "web/fully-automated") and never mentions UIMB0440's SIM-phone reading. Silent single reading = 1 on gap-honesty per the key. |
| 8 | Local offices vs MUNC | retrieval + boundary | 10 | **10** | Four office codes on UIMV_CLAIMANT (via UIMB0053), the T003/T745/T004/T112/T113 resolution chain, 999/997, classification, and a clean boundary: municipality→office mapping not in the KB, T003 named as the closest documented analogue. |

**Total: 78/80** (run 1: 68/80, same bank, same agent, KB fixed in between).

## Cross-run picture (all four banks, same day, pre- vs post-fix)

| Bank | Pre-fix best | Post-fix | Δ | What moved |
|------|-------------|----------|---|------------|
| v1 | 79 | **80** | +1 | The chronic Q3 WGPM-conflation dock — fixed by DXCBD87E retrieval |
| v2 | 76 | **80** | +4 | DXCBD87E (Q1), T109TABL false absence (Q4), grounded CWE exception (Q6) |
| v3 | 68 | **73** | +5 | ACP expansion (Q2 +3), VERIS (Q4 +2); Q1 term-bridge and Q5 bait unchanged |
| v4 | 68 | **78** | +10 | All four retrieval false negatives (Q1/Q2/Q3/Q5) |
| **Total** | 291/320 | **311/320** | **+20** | |

## Findings

1. **The empty-KB diagnosis is confirmed by the intervention.** Twenty points recovered across four banks with zero agent changes, and the recovery lands exactly on the questions previously graded as daily-space retrieval false negatives. The audit's failure taxonomy (retrieval vs adoption vs conflict-handling) predicted the deltas almost line-by-line.
2. **What the fix did not move is the remaining roadmap.** Three failure shapes survive, none of them retrieval: (a) **term-bridging** (v3-Q1: an invalid name can't rank the right family; anchor-doc glossary line still the fix), (b) **plausible-anchor bait** (v3-Q5, three identical failures; extend the name-verification persona rule to screens/any named artifact), (c) **conflict-surfacing** (v4-Q7, 0-for-4 across runs in both "adjudicate" and "silent-merge" modes; candidate persona rule (c): present disagreeing retrieved sources as a documented conflict and flag for SME).
3. **New, small, worth watching: richer corpus → stronger attribution pull on baits.** v4-Q6 slipped 10 → 9 because the now-retrievable LOFBSBLD/response-builder docs offered a plausible "most likely producing program" frame. The bait taxonomy's momentum + plausible-anchor model predicts exactly this; future banks should keep at least one true-premise bait to track it.
4. **The 9000+'7777' SME question (v3 erratum 2) is still open with the IVR team** and is now the single highest-leverage content fix: it accounts for docks in v3-Q6 and v4-Q7 in every run.
