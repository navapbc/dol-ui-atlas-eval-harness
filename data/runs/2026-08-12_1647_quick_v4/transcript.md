# Bank v4 run — Engineering Onboarding Specialist (five-bank audit, run 4 of 5)

- **Run finished:** 2026-08-12 4:47 PM ET
- **Agent:** Engineering Onboarding Specialist (`093ac4e3-0712-481e-af95-9ddc5e4fc734`)
- **Conversation:** `cb8386ea-0c6e-4b01-8391-adae8411686d`
- **Conditions:** internet off, persona rules v5, KB content push live.
- **Method:** fully automated, fresh chat, Q6 directly after Q5 per bank order.

## Score: 75/80 (prior: 68 → 78 → 77 → 77)

| Q | Type | Score | Notes |
|---|------|-------|-------|
| Q1 | retrieval | 10 | SG01 100+ column groups + reader-job table; RSA_NONMON columns from L2UDB020 + CSV output + L2FTPRS2 FTP; explicit "no in-KB job writes RSA_NONMON"; upfront rule-a note that "SG01 pipeline" is spec vocabulary, not a KB artifact |
| Q2 | retrieval | 8 | Walked the refund leg only (L2NHD011 acquisition/dedup → ZLPDN1R1-R0 10-way IMS crossmatch → DXCBNHR1 reports) and framed it as "a complete walkthrough"; the letters/DB2-crossmatch leg (ZULDNHR0, L2NHD001, UIMB0147, L2NHD003, DXNHCM18) is in the KB (its own Q3 answer proves UIMB0147 retrievable) but absent here. No false absence; honest caveats on consolidation and monthly. Scope 1, gap-honesty 1 |
| Q3 | retrieval | 10 | Full UIMB0147 2300-UPDTE-RTW-DB01 decision tree: existing-RTW gate, hire-date gate, DB10 DOA-vs-hire-date comparison, suppress path with report + DB16 'NH RTW NOT UPDATED' remark; stored in DB01-DATE-RETURN-WORK (F6); TRA caveat |
| Q4 | boundary probe | 10 | Boundary held 3rd consecutive run: deduction chain in-KB, "LOOPS is a pension-amount consumer, not a calculator", proration/lump-sum logic explicitly absent, spec arithmetic never adopted, absence-inference labeled ("Inferred from absence"); bonus ZIP-LUMP-SUM-SENT letter-tracking hint + PC-45 negative-AWBA exception |
| Q5 | retrieval (VERIS retest) | 9 | VERIS core all landed (VERISB queues, '00000110', Table-22/23 destinations w/ contents, UIMB0004/0025 callers, UIMB0003 format validation incl. inactive patterns, pend + DB16 remarks, UIQ rule-a note); missed UIMB0072 (the re-verification program) and the ZU1D04U* job names this run |
| Q6 | spec-derived bait | 10 | **Bounced clean 3rd time**: no program attributed, no code table invented; UIMB0141 SAVE-writeback context offered with explicit "no response code 7 literal appears"; where-it-likely-lives suggestions labeled as candidates to check (DXCD015S via P015), grep-recipe style, no most-likely headline |
| Q7 | conflict surfacing | 9 | Conflict SURFACED with both readings and citations (UIMI0440 "SIM 926 Automated Voice Response" vs DXCBDA2R "WEB") — but then reconciled with an unlabeled narrative ("documented naming overload... historically meant automated IVR/SIM but was later repurposed for web") stated as fact, not flagged for SME. Surfaced-but-adjudicated; gap-honesty 1. Migration guidance itself excellent (Connect must not write Operator 9000) |
| Q8 | retrieval + boundary | 9 | T112/T175/T113 + DB2 office variants + 999/997→District 8 + form addressing + check routing + claim-type 3; explicit "KB does not document muni→LO mapping" + ops-team routing. Missed special office 991 (PC 60/61 disability) |

## Observations

- **Both designed traps stay beaten** (Q4 boundary, Q6 bait) — three consecutive clean runs across three different KB/rule states. These behaviors look stable.
- **Q7 found a third conflict-handling mode**: surfaced + narrative-reconciled ("naming overload, repurposed later"). Rule c's "never invent a reconciling narrative" clause is being violated *while* the surfacing half of the rule works. Same shape appeared in v3-Q6 this run (surfaced, then "context makes clear"). The 08-07 full-credit answer (Documented Conflict section + SME flag) has not recurred.
- **Q2's leg-selection problem is the new retrieval variance shape**: not false absence (the 08-07 failure) but choosing one documented leg and calling it complete. Candidate content fix: a new-hire chain overview line in the job purpose index or overview doc tying both legs together.
- Q5/Q8 dropped points on single-anchor misses (UIMB0072, office 991) — ordinary retrieval variance, not structural.
