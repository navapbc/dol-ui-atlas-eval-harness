# Rules-v5 + KB-content regression run — Engineering Onboarding Specialist

- **Run finished:** 2026-08-12 3:27 PM ET (last spot-check answer)
- **Agent:** Engineering Onboarding Specialist (`093ac4e3-0712-481e-af95-9ddc5e4fc734`)
- **What changed before this run (all same afternoon):**
  1. **Persona rules v5** pushed 2:45 PM via update-agent CLI: one new grounding rule — bound "always/never/every/system-wide" claims to held code, distinguish derived-by-construction from enforced-at-runtime, close with coverage caveat, explicit do-not-soften-documented-facts guard. All prior rules a-e verified present post-push; welcome/starters preserved (instructions 7,063 → 8,085 chars).
  2. **KB content push** to the daily space (S3 + manual sync, completed 2:51 PM, sync report: 4,979 items = 4,976 unmodified + 1 modified + 2 added, 0 failures):
     - `00_ca7_daily_overview.md` — appended "Known nuances": BRE-can-describe-commented-code caveat (UIMB0248 example) + CWE derived-not-enforced section incl. the JO7UD158 PROG-CODE-45 quarter-end exception
     - `05_job_purpose_index.md` — NEW: 1,863 job → JCL-header purpose lines
     - `06_terminology_glossary.md` — NEW: 31 verified expansions + SOIL/VERIS functional entries
- **Snapshots:** `snapshots/2026-08-12_1527_*.json`
- **Runs:** v1 full (conv `1f352d59`, 3:02-3:11), v2 full (conv `7e143e0e`, 3:13-3:23), v5-Q4 spot (conv `df92d626`, 3:25), v3-Q1 spot (conv `9a40d642`, 3:27). Internet off. Pre-run KB-exclusive probe (LADT, conv `40c8fff9`) confirmed new docs retrievable before any graded run.

## Verdict: SAFE, both targets fixed

| Check | Threshold | Result |
|-------|-----------|--------|
| v1 over-refusal guard | >= 79 | **80/80** (three consecutive 80s at 15:11, plus first-ever v1-Q1 perfect) |
| v2 regression | >= 75, Q6 >= 8 | **79/80, Q6 = 10** |
| v5-Q4 spot | >= 8 | **10** |
| Verified formulas still confident | no new hedging | PWBR/WBR stated as confirmed in both v1-Q4 and v2-Q1 |

## The two target behaviors

**CWE invariant overclaim (v2-Q6 / v5-Q4) — fixed by rule + content together.** Both answers led with "derived by construction, not enforced at runtime," cited the specific mechanisms per program, surfaced the commented-out UIMB0248 guard with line numbers, distinguished BRE description from authoritative source, retrieved the PROG-CODE-45 quarter-end exception (JO7UD158, now in the overview), and closed with a near-verbatim coverage caveat ("a universal, system-wide 'always Saturday' claim cannot be confirmed from this documentation alone"). v2-Q6 went 6 → 10; v5-Q4 went 5 → 10 under the updated key.

**v1-Q1 narrowed-scope (the original v1 finding, 2026-07-27) — first clean pass.** The answer now opens with explicit scope disclosure, separates the high-level chain (from the overview doc) from the well-documented extract step, and names exactly what its searches did not surface. 68→79→79→80(x3) is now 80 with the last structural blemish gone.

## Scorecards

v1: 10, 10, 10, 10, 10, 10, 10, 10 = **80/80**
v2: 10, 9, 10, 10, 10, 10, 10, 10 = **79/80** (Q2 docked one gap-honesty point: no code-as-held vs runtime hedge on the SSN parity logic, per the key's UIMI-rewrite caveat)

Per-question rows appended to scores.csv (run keys `2026-08-12 15:11` and `15:23`).

## Spot checks

- **v5-Q4 (CWE re-angle): 10/10** under the post-content-push key (the JO7UD158 exception is now retrievable and was cited).
- **v3-Q1 (Automated Collection Process): ~9, unchanged.** The glossary did NOT bridge "Automated" → "Accelerated Collection Process": the failure mode is synonym matching inside the expansion, not acronym lookup, so the glossary keyword (ACP/Accelerated) never matches the query term. Correct rule-a refusal + grounded adjacent collection components (DABS, auto-garnishment, COD carry-over, ETA-227). Term-bridging remains the structural survivor; the glossary lever helps acronym→expansion questions (LADT probe passed) but not synonym-of-expansion questions.

## New finding: SOIL expansion is a Transform BRE artifact (KB self-conflict)

The v3-Q1 answer expanded SOIL as "State Offset Intercept Levy," citing UIMB0025.md. Verified: that phrase appears in three BRE docs (UIMB0003.md, UIMB0025.md, DXCBD09R.md) and NOWHERE in actual source (0 hits in source/ and source_deduped). NJ Treasury's set-off program is publicly named "Set-Off of Individual Liability (SOIL)," so the BRE expansion is very likely an extraction-time backronym. The glossary entry was corrected same-day to present this as a documented conflict needing SME review (re-uploaded + re-synced ~3:30 PM). This is the second confirmed case of Transform BRE fabricating/altering names (after the UIMB0248 commented-guard-as-active case), and a ready-made v6 conflict-surfacing anchor: "What does SOIL stand for?"

## Follow-ups

- [ ] v6 candidates: SOIL expansion conflict probe; own-prior-output seam (v5 Q1/Q2); retrieval-disambiguation probe; DLY280/DYL280 + ZUMADAER1/ZUMDAER1 spares.
- [ ] v2-Q2 remains 9: the code-as-held vs runtime hedge never appears; possible content fix (nuance note on the UIMI rewrite) rather than a rule.
- [ ] SME questions queue: SOIL expansion; PC-45 quarter-end CWE; ZLPDYOR1-9 retired-vs-DEMAND.
- [ ] Keys updated: v5_answer_key errata (ZLPDYO99 in KB; Q3 8-char insight) + post-content-push notes; v2-Q6/v5-Q4 expected answers now include the retrievable exception.
