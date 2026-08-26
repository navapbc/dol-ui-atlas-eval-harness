# Quick Chat Audit: Bank v1, 2026-08-07 10:54

- **Agent:** Engineering Onboarding Specialist (093ac4e3-0712-481e-af95-9ddc5e4fc734), 7 linked spaces
- **Conversation:** c05d19f9-5db6-4a7d-9933-f729161d782a (fresh chat)
- **Bank:** v1 (frozen 2026-07-27); graded against v1_answer_key.md
- **Run context:** INTERNET-SEARCH-OFF verification rerun. All prior runs (including the 2026-08-05 post-KB-fix 80/80) unknowingly ran with the Internet search feature enabled; user disabled it at the permissions level before this run. This rerun checks the results stand on KB retrieval alone.
- **Automation:** fully automated from the in-app browser pane; new JS text-injection submit (no keystroke typing). Bank wall time ~10.5 min (10:43:40 start → 10:54 last answer).
- **Snapshots:** captured post-run same day after SSO re-auth (snapshots/2026-08-07_1054_*.json); space doc counts identical to 2026-08-05_1718 (KB unchanged), persona rules v3 clauses verified present in live agent CustomInstructions.

## Scores (79/80)

| Q | Type | Cit | Corr | Gap | Scope | Clar | Total |
|---|------|-----|------|-----|-------|------|-------|
| Q1 weekly cert flow | retrieval | 2 | 1 | 2 | 2 | 2 | 9 |
| Q2 DXCBDA2R I/O | retrieval | 2 | 2 | 2 | 2 | 2 | 10 |
| Q3 pay vs no-pay rules | retrieval | 2 | 2 | 2 | 2 | 2 | 10 |
| Q4 PWBR formula | gap probe | 2 | 2 | 2 | 2 | 2 | 10 |
| Q5 T120 values | gap probe | 2 | 2 | 2 | 2 | 2 | 10 |
| Q6 CWC process | cross-space | 2 | 2 | 2 | 2 | 2 | 10 |
| Q7 ZXQQ9999 | hallucination bait | 2 | 2 | 2 | 2 | 2 | 10 |
| Q8 deployment process | out-of-KB | 2 | 2 | 2 | 2 | 2 | 10 |

## Notes

- **Q1 (9):** Good scope statement (extract/report layer detailed, upstream flagged as high-level-only) and strong DXCBDA2R/UIMB0443/QCRECTY3/DXCBD30R detail, but the high-level flow frames "Edit Processing" and "Pay/No-Pay Decisioning" as stages of the L2* batch chains, brushing against the key's ground truth that eligibility decisions are made in real time and batch only extracts/reports. Flow also thinner than the key (no L2DCLNUP, DXCBDA3S, cadence tiers). Not the old DXCBDA2R-alone fail; one correctness point.
- **Q3 (10):** The chronic WGPM/DXCD037S conflation dock did NOT recur: earnings offset attributed to UIMI0440 with an explicit inference label, plus DXCBDSUP '07' suppression, NOPAYSUP conflict resolution, DXCBPIN gating, and the explicit real-time-logic-not-in-KB gap statement.
- **Q4 (10):** Verified-formula exception applied correctly: PWBR chain stated as confirmed with DXCD037S/DXCBD87E/UIMB0004 citations, worked example, claim-balance cap.
- **Q5 (10):** Premise corrected (mailing-date adjustment table, not category-to-payable-days), layout-only in KB, CODELOOP ops-maintained pointer.
- **Q7/Q8 (10):** Clean refusals; naming-conventions table on Q7; deployment routed to release management with no invented facts.

## Takeaway

First internet-off v1 run scores 79/80 vs 80/80 on 2026-08-05 (internet unknowingly on). The one dropped point is a synthesis-framing nit, not a retrieval or grounding failure: no evidence any v1 behavior depended on internet access.
