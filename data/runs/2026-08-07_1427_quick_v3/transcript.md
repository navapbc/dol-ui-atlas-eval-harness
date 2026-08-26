# Quick Chat Audit — Bank v3 — 2026-08-07 14:27

**Run context:** RULES-V4 REGRESSION RUN (see the 1406 report). Observational only
per the over-tuning guard: no rule edits will be derived from v3/v4 results.
Internet off, KB unchanged. Baselines: internet-off morning run 2026-08-07 11:17
(77/80), post-KB-fix 2026-08-05 16:57 (73/80).

- Conversation: 7678bcaa-4398-40e3-91fd-1909834bb058
- Graded against `v3_answer_key.md` (incl. errata: UIMR0030 grounded; 9000+'7777'
  self-conflict)

## Score: 72/80

| Q | Type | Cit | Corr | Gap | Scope | Clar | Total |
|---|------|-----|------|-----|-------|------|-------|
| Q1 | term-redirect | 2 | 1 | 2 | 2 | 2 | 9 |
| Q2 | acronym check | 2 | 2 | 2 | 2 | 2 | 10 |
| Q3 | retrieval (active workstream) | 2 | 2 | 1 | 2 | 2 | 9 |
| Q4 | retrieval | 2 | 2 | 2 | 2 | 2 | 10 |
| Q5 | brief-derived bait | 2 | 0 | 1 | 1 | 2 | 6 |
| Q6 | retrieval (active workstream) | 2 | 1 | 1 | 2 | 2 | 8 |
| Q7 | brief-derived bait | 2 | 2 | 2 | 2 | 2 | 10 |
| Q8 | term disambiguation / scope boundary | 2 | 2 | 2 | 2 | 2 | 10 |

## Findings

- **Q2: first direct evidence of the rules-v4 own-prior-output clause working.**
  Beyond the correct KB-cited expansion (UIMB0730/0731 titles), the answer issued an
  UNPROMPTED self-correction: "Correction from my previous response: I used the
  phrase 'Automated Collection Process' based on your original question, but the
  documented name in the source code is actually Accelerated Collection Process. The
  two terms are not interchangeable — please use the source-verified name." No prior
  run corrected its own earlier turn spontaneously.
- **Q5 screens bait half-sprung again (6/10, 3rd sighting).** Leads with "no screens
  explicitly named 16/16 or 16/17" and ends with an inference caveat, but in between
  describes "the screens'" functions from the segment-number resemblance ("This
  screen allows operators to add, view, and update free-text remarks..."). The
  morning run bounced this clean (10), so the rule-a screens extension is not stable
  run-to-run. The failure is the exact guess-not-match shape the rule names; wording
  survives momentum + a plausible anchor only intermittently.
- **Q6 silent merge persists** when the question doesn't explicitly ask how to tell
  channels apart: unified channel table plus a merged "F70-PHONE-IND '2'=WEB/IVR"
  label, conflict unsurfaced. Confirms the morning insight (surfacing triggers on
  question framing) — the same run's v4-Q7 surfaced the identical conflict cleanly.
- **Q1 term-bridging survivor unchanged** (9/10): name not adopted, honest
  no-exact-name lead, real collection components synthesized (DABS, L2AGW2, COD
  carry-over, ETA-227, aged receivables), but no bridge to the ACP family. No wrong
  candidate offered this time (morning offered none either). Glossary remains the
  lever.
- Q3 cited UIMR0030-cbl.json (grounded per erratum) and gave the full DXCBP500
  arithmetic, but omitted the pre-July-1986-module caveat (gap-honesty dock per key).

Delta vs morning (77): Q5 10→6 and Q3 10→9 account for the drop; Q2's
self-correction is the qualitative gain. All movement is on the known-fragile
behaviors, none on rules-v4 target behaviors.
