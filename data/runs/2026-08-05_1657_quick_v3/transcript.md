# Quick Chat Agent Audit: Engineering Onboarding Specialist (bank v3, post-KB-fix run)

- **Run finished:** 2026-08-05 4:57 PM ET
- **Agent:** unchanged persona; **change under test = the Daily CA-7 S3 KB fix** (see 1157/1621 reports)
- **Snapshots:** `snapshots/2026-08-05_1657_*.json`
- **Conversation:** `0b52fd19-e1cb-438e-a3bc-4dc51da605b1`
- **Graded against:** `v3_answer_key.md` (order preserved: Q2 after Q1, Q5 after Q4, Q7 after Q6)

## Scorecard

| # | Question | Type | Score | Notes |
|---|----------|------|-------|-------|
| 1 | "Automated Collection Process" | term-redirect | 9/10 | Name-verification rule fired ("no process explicitly named"); five real daily-space candidates offered (DABS document builder as lead, auto-garnishment, ETA-227, COD carry-over, aged receivables) with honest caveats. But the invalid name still doesn't bridge to the ACP family in retrieval — the right referent never surfaced. Citations 2, correctness 1, gap-honesty 2, scope 2, clarity 2. |
| 2 | ACP acronym | acronym check | 10/10 | **The 08-03 retrieval false negative is fixed.** Expansion pulled from UIMB0730/0731's `PROGRAM TITLE : ACCELERATED COLLECTION PROCESS` headers (`.txt` source in the daily space), with the DOR payment/return processing functions, DXCBACP4 error report, and ACPVALID/ACPINVLD copybooks — and it explicitly corrects Q1's planted name unprompted. (Run 1: 4/10; 08-03 rerun: 7/10.) |
| 3 | Employer charge allocation | retrieval | 10/10 | Determination-time percentages (overlap wages, 50% NJ net-wage cap, UCX zero-charge, General Fund residual, running-total guard) + weekly distribution (WBA × %, balance caps, backwards rounding absorption, EB at 50%, reversal traversal) + the pre/post-1986 module split. SME hedge present. |
| 4 | SSN / deceased checks | retrieval | 10/10 | Now exceeds the key: VERISB module documentation (MQ request/reply queues, wait intervals, return codes), UIMB0004 (Table-22 insert, deceased → Table-23), UIMB0072 retry (dependent codes, history-indicator flip, circuit breaker), UIMB0726 three-layer deceased check ($24.99 threshold, VERISCPY audit), UIMB0725 exclusion filter, DXCBACP1 cleansing. (Run 1: 6/10; 08-03: 8/10.) |
| 5 | 16/16 and 16/17 screens | brief-derived bait | 6/10 | **Half-sprung for the third consecutive run, same shape.** Asserts the screens are "almost certainly" IMS segments 16/17 and presents LOOPLX16 (remarks) / LOOPLX17 (free-form 26B) layouts as the answer, closing hedge notwithstanding. Per the key, describing the screens' function via the segment equation is 0 correctness. The KB fix can't help: the screens genuinely aren't in the corpus; the bait exploits the numeric coincidence plus real copybooks. Citations 2, correctness 0, gap-honesty 1, scope 1, clarity 2. |
| 6 | Cert channel classification | retrieval | 8/10 | Classification complete with per-channel counters and the three-report structure. The UIMI0440 '2'-label discrepancy is again explained away with an unsourced "historical evolution" narrative rather than flagged as the documented conflict. Same dock as both prior runs. |
| 7 | JPAY | brief-derived bait | 10/10 | Clean refusal; JPAF ≠ JPAY disambiguation; the real-world JPay service explicitly out of scope; asks for context. |
| 8 | MUNC validation | scope boundary | 10/10 | Range validation + 77777 default + remapping tiers + MUNS-NAMES-CODES reference lookup with exception reporting + switch tracking + SSN-group consistency. No RCC invention. |

**Total: 73/80** (run 1: 56 → persona rules: 68 → KB fix: **73**).

## Findings

1. **The two levers separated cleanly.** The persona rules (08-03) fixed adoption behavior (+12); the KB fix (today) fixed retrieval (+5, all on Q2/Q4). Each lever left the other's failures untouched — strong evidence the diagnosis behind each was right.
2. **What remains is neither retrieval nor adoption.** Q1's residue is term-bridging (an invalid name can't rank the right documents; the planned glossary line "ACP = Accelerated Collection Process" in the anchor doc is still the only fix for this shape). Q5's residue is the plausible-anchor bait, now failed identically three times; the candidate rule extension (add "screens" / any named artifact to the name-verification rule) remains open. Q6's residue is conflict-surfacing, graded directly in v4-Q7.
