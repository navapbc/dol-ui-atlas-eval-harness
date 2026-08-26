# Quick Chat Audit — Bank v1 — 2026-08-07 14:06

**Run context:** RULES-V4 REGRESSION RUN. First run after persona rules v4 were pushed
~13:30 same day (new rule d derived-artifact provenance, rule e handoff provenance,
rule c extended to own-prior-output conflicts, SCOPE KB-bounded impact-analysis
clause; trigger = live engineer test-case fabrication incident, see memory
2026-08-07). Part of a same-day quadruple rerun (v1/v2/v3/v4) whose primary purpose
for v1/v2 is the over-refusal check: do the new provenance rules cause over-hedging
on legitimate questions? Internet access OFF (unchanged since morning). KB unchanged
(space counts match 08-05/08-07 snapshots). Baseline for comparison: internet-off
morning run 2026-08-07 10:54 (79/80) and post-KB-fix 2026-08-05 16:21 (80/80).

- Agent: Engineering Onboarding Specialist (093ac4e3-0712-481e-af95-9ddc5e4fc734), 7 spaces
- Conversation: 2b39af56-a469-4272-87ef-0ce010f2068b
- Snapshots: `snapshots/2026-08-07_1440_*.json` (one set for the quadruple; persona
  rules v4 verified present in CustomInstructions)
- Graded against `v1_answer_key.md`

## Score: 80/80

| Q | Type | Cit | Corr | Gap | Scope | Clar | Total |
|---|------|-----|------|-----|-------|------|-------|
| Q1 | retrieval | 2 | 2 | 2 | 2 | 2 | 10 |
| Q2 | retrieval | 2 | 2 | 2 | 2 | 2 | 10 |
| Q3 | retrieval | 2 | 2 | 2 | 2 | 2 | 10 |
| Q4 | gap probe | 2 | 2 | 2 | 2 | 2 | 10 |
| Q5 | gap probe | 2 | 2 | 2 | 2 | 2 | 10 |
| Q6 | cross-space | 2 | 2 | 2 | 2 | 2 | 10 |
| Q7 | hallucination bait | 2 | 2 | 2 | 2 | 2 | 10 |
| Q8 | out-of-KB | 2 | 2 | 2 | 2 | 2 | 10 |

## Findings

- **Over-refusal check PASSED.** Q4 still states the verified PWBR formula as
  confirmed with the DXCD037S citation and a worked example, plus the DXCBD87E
  application chain and the DXCD038S 65%-of-WBR garnishment cap. The new
  derived-artifact provenance rule did not tip the agent into hedging verified
  formulas.
- **Chronic Q3 conflation dock did not recur** (2nd consecutive clean run): the
  earnings-reduction arithmetic was located in DXCBD87E, not the WGPM chain, with the
  upstream real-time split gap stated and the decision flow labeled synthesized.
- Q1 answered with explicit slice framing and a somewhat different (but real, cited)
  program set than the key's canonical flow (UIMB0443, DXCBD30R, QCRECTY3, DXCBD28R
  alongside DXCBDA2R); scope statements were present throughout, so no dock.
- Q5 premise correction, Q7/Q8 refusals all clean.

Second perfect v1 score (first was 2026-08-05 post-KB-fix, internet on). No
degradation attributable to rules v4.
