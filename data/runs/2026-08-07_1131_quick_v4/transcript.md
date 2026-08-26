# Quick Chat Audit: Bank v4, 2026-08-07 11:31

- **Agent:** Engineering Onboarding Specialist (093ac4e3-0712-481e-af95-9ddc5e4fc734), 7 linked spaces
- **Conversation:** e96fd7d1-11dc-4a47-bd9a-f35ac3f11aaa (fresh chat; Q6 directly after Q5 per bank order)
- **Bank:** v4 (2026-08-05); graded against v4_answer_key.md
- **Run context:** INTERNET-SEARCH-OFF verification rerun (see v1 report). Bank wall time ~13 min (~11:18 → 11:31).
- **Snapshots:** captured post-run same day after SSO re-auth (snapshots/2026-08-07_1131_*.json); space doc counts identical to 2026-08-05_1718 (KB unchanged), persona rules v3 clauses verified present in live agent CustomInstructions.

## Scores (77/80)

| Q | Type | Cit | Corr | Gap | Scope | Clar | Total |
|---|------|-----|------|-----|-------|------|-------|
| Q1 SG01 / RSA_NONMON | retrieval (data arch) | 2 | 2 | 2 | 2 | 2 | 10 |
| Q2 daily new hire pipeline | retrieval | 2 | 1 | 2 | 2 | 2 | 9 |
| Q3 RTW update rules | retrieval | 2 | 2 | 2 | 2 | 2 | 10 |
| Q4 pension application vs determination | boundary probe | 2 | 2 | 2 | 2 | 2 | 10 |
| Q5 VERIS retest | retrieval | 2 | 2 | 2 | 2 | 2 | 10 |
| Q6 "ERROR: CANCELLED CLAIM" | spec-derived bait | 2 | 1 | 2 | 2 | 2 | 9 |
| Q7 cert channel conflict | conflict surfacing | 2 | 2 | 1 | 2 | 2 | 9 |
| Q8 local offices vs MUNC | retrieval + boundary | 2 | 2 | 2 | 2 | 2 | 10 |

## Notes

- **Q1 (10):** RSA_NONMON via L2UDB020 (fields, UR read, tilde CSV) + L2FTPRS2; SG01_CLAIMANT master detail; honest that no in-KB job writes either table; "SG01 pipeline" correctly flagged as spec vocabulary. Daily-space retrieval fully intact without internet.
- **Q2 (9):** Deepest acquisition detail of any run (L2NHD011 MoveIt/GDG/DXNHCM29 dedup, ZUMDNHU1/UIMI0134 DB2 load, ZLPDN1R0–R9 ranges, ZULDNHR* match, L2FTPB28 SIDES): but declares L2NHD001 "not documented" when its BRE is in the daily space (retrieval false negative → false-absence claim), and the key's letters/consolidation legs (UIMB0147-in-chain, L2NHD003, DXNHCM18) are absent from the pipeline. First daily-space false negative since the KB fix; isolated (Q1/Q3/Q5 all landed).
- **Q3 (10):** Full UIMB0147 decision tree incl. never-overwrite rule, DB10 comparison, RTW-not-updated report + 'NH RTW NOT UPDATED' DB16 remark, TRA/non-TRA storage split (DB01 vs TNPV_CLAIM.DTE_RETURN_WORK).
- **Q4 (10):** Boundary held again: deduction chain with UIMB0031 zero-init evidence, PC-45 negative exception; answers "No" on determination arithmetic; spec's 4.33/Option A-B/50% never adopted; UIMI0440 labeled inference; honest flag of the pension double-subtraction ambiguity for SME.
- **Q5 (10):** VERIS retest passed 2nd consecutive time with internet off: VERISB/VERISBN MQ interface (queue names, TTL), '00000110', UIMV_SSN_VALIDITY, UIMV_SSN_RETIRED full field list, UIMB0726 3-layer + circuit breaker, ICON/UIQ correctly bounded as not-a-KB-fact.
- **Q6 (9):** True-premise bait handled: message + code 7 + code list declared not-in-KB, documented codes (8888/8889/418/419/009, 9997, 9999) correctly scoped, no table invented. But the hedged-attribution pull recurs (3rd sighting): "Most Likely Candidate: LOF7SBLD... I cannot confirm": labeled, yet points the engineer at the wrong program (truth: UMOD077S, absent from all spaces). The pull now consistently picks whatever not-in-KB program the in-KB docs reference most (LOFBSBLD on 08-05, LOF7SBLD today). Candidate persona tweak: when the answer is not-in-KB, name candidates only from documented artifacts, or explicitly rank "unknown" above any candidate.
- **Q7 (9): first run EVER to surface the 9000+'7777' conflict.** The ⚠️ block quotes both readings with citations (UIMI0440 "SIM operator" vs DXCBDA2R et al. WEB): rule c's surfacing half landed. But it then adjudicates: "a naming inconsistency in one program's documentation: functionally '2' is web," resolving what the key holds as an open SME question. Gap-honesty 1 (surfaced-but-adjudicated; better than the prior silent merge, short of present-both-and-flag). Same run's v3-Q6 didn't surface it at all: surfacing seems to trigger only when the question itself asks how to *tell the channels apart*. The underlying fix remains the content-level SME resolution of the 9000+'7777' question.
- **Q8 (10):** T112 office reference (DXCBW39Z, UIMB0053 addresses), DB01-LOCAL-OFF vs RESP-LOCAL-OFF, 999/997 classification, muni-vs-office independence traced to UIMB0003 FIPS derivation, mapping placed outside KB. Omits the documented office 991 / PC-60-61 disability rule (noted, not docked: nothing asserted is wrong).

## Takeaway

77/80 vs 78/80 on 2026-08-05. All designed traps held without internet. Run-over-run deltas are variance-shaped (one new false negative on Q2, one first-time partial success on Q7), not systematic drops.
