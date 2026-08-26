# DRAFT — 2801 answer-quality tracker (for issue body, pending review)

Not posted. Contains no program identifiers, source content, or restricted
values; question-level detail stays in the restricted audit folder.

---

## Answer-quality benchmark tracker

Scope: Amazon Quick "Engineering Onboarding Specialist" agent
(`093ac4e3`, 7 linked LOOPS spaces). Benchmark: question banks v1-v5
(8 questions each), scored 0-2 on five dimensions (citations,
correctness, gap-honesty, scope discipline, clarity; 80 max/run).
Detailed transcripts, answer keys, and per-question grades are stored in
the restricted evaluation folder; this issue records summaries only.

**Benchmark status.** v1-v5 are the DEVELOPMENT set: they were run
repeatedly and several interventions below were direct responses to
their results, so scores on them measure improvement-on-known-questions,
not generalization. A held-out set (v6, 10 questions, adjudicated
2026-08-18) is frozen under gold-set hash `683082e6…5173dc` (50
questions total) and reserved for the Quick-vs-OKF-bundle comparison.
New or revised questions stay in a candidate/draft state until
adjudicated and re-frozen under a new hash (process demonstrated by v6).

### Configuration versions

Personas (agent custom instructions), identified by sha256 of the
instruction text; full config snapshots are archived per run:

| Version | sha256 (prefix) | First seen | Note |
|---|---|---|---|
| P1 | `ffafa14af0ac` | 2026-07-27 | baseline (614 chars) |
| P2 | `302275d611a2` | 2026-07-27 | post-v1-baseline rewrite (3,176) |
| P3 | `e2a667989300` | 2026-08-03 | (4,154) |
| P4 | `346edf615ffa` | 2026-08-07 | (4,935) |
| P5 | `3e0a1ecbfb0b` | 2026-08-07 | (7,063) |
| P6 | `e915330bdbfd` | 2026-08-12 | current (8,085); flagged in leakage
review: encodes guidance matching a v1 grading distinction |

Corpus states (Daily CA-7 space): C0 = pre-anchor-doc; C1 = anchor doc
added 2026-07-27; C2 = 2026-08-12 push (overview doc revised, job
purpose index + terminology glossary added). Corpus digest for the
current BRE package: `450983fb…` (Phase 0 snapshot 2026-08-19; KB
ingestion `734a4dbd` confirmed synced 2026-08-20).

### Run history (retroactive backfill, best-effort)

Fields recorded going forward: date, evaluator, agent/model config
snapshot, persona version, KB/corpus state, bank version, scores,
changes since previous run, regressions. Historic rows below are
reconstructed from per-run snapshots; rows 22-23 straddle the 08-12
persona update and content push, so their P/C attribution is
approximate. Evaluator for all rows: M. Angeli.

| # | Finished (ET) | Bank | Persona | Corpus | Overall | Cit | Cor | Gap | Scope | Clar | Δ same-bank |
|--:|---|---|---|---|--:|--:|--:|--:|--:|--:|---|
| 1 | 2026-07-27 11:19 | v1 | P1 | C0 | 68/80 | 16 | 14 | 11 | 11 | 16 | — |
| 2 | 2026-07-27 13:04 | v1 | P2 | C1 | 79/80 | 16 | 15 | 16 | 16 | 16 | +11 |
| 3 | 2026-07-28 11:17 | v2 | P2 | C1 | 75/80 | 16 | 13 | 15 | 15 | 16 | — |
| 4 | 2026-08-03 13:20 | v3 | P2 | C1 | 56/80 | 14 | 7 | 10 | 9 | 16 | — |
| 5 | 2026-08-03 16:15 | v1 | P3 | C1 | 79/80 | 16 | 15 | 16 | 16 | 16 | +0 |
| 6 | 2026-08-03 16:35 | v2 | P3 | C1 | 76/80 | 16 | 13 | 15 | 16 | 16 | +1 |
| 7 | 2026-08-03 16:54 | v3 | P3 | C1 | 68/80 | 15 | 9 | 13 | 15 | 16 | +12 |
| 8 | 2026-08-05 11:57 | v4 | P3 | C1 | 68/80 | 16 | 11 | 9 | 16 | 16 | — |
| 9 | 2026-08-05 16:21 | v1 | P3 | C1 | 80/80 | 16 | 16 | 16 | 16 | 16 | +1 |
| 10 | 2026-08-05 16:38 | v2 | P3 | C1 | 80/80 | 16 | 16 | 16 | 16 | 16 | +4 |
| 11 | 2026-08-05 16:57 | v3 | P3 | C1 | 73/80 | 16 | 12 | 14 | 15 | 16 | +5 |
| 12 | 2026-08-05 17:18 | v4 | P3 | C1 | 78/80 | 16 | 15 | 15 | 16 | 16 | +10 |
| 13 | 2026-08-07 10:54 | v1 | P4 | C1 | 79/80 | 16 | 15 | 16 | 16 | 16 | -1 ⚠ |
| 14 | 2026-08-07 11:05 | v2 | P4 | C1 | 75/80 | 16 | 15 | 14 | 14 | 16 | -5 ⚠ |
| 15 | 2026-08-07 11:17 | v3 | P4 | C1 | 77/80 | 16 | 15 | 14 | 16 | 16 | +4 |
| 16 | 2026-08-07 11:31 | v4 | P4 | C1 | 77/80 | 16 | 14 | 15 | 16 | 16 | -1 ⚠ |
| 17 | 2026-08-07 14:06 | v1 | P4 | C1 | 80/80 | 16 | 16 | 16 | 16 | 16 | +1 |
| 18 | 2026-08-07 14:16 | v2 | P4 | C1 | 75/80 | 16 | 15 | 14 | 14 | 16 | +0 |
| 19 | 2026-08-07 14:27 | v3 | P4 | C1 | 72/80 | 16 | 12 | 13 | 15 | 16 | -5 ⚠ |
| 20 | 2026-08-07 14:40 | v4 | P5 | C1 | 77/80 | 16 | 13 | 16 | 16 | 16 | +0 |
| 21 | 2026-08-12 13:50 | v5 | P5 | C1 | 71/80 | 16 | 13 | 13 | 13 | 16 | — |
| 22 | 2026-08-12 15:11 | v1 | P5* | C2* | 80/80 | 16 | 16 | 16 | 16 | 16 | +0 |
| 23 | 2026-08-12 15:23 | v2 | P5* | C2* | 79/80 | 16 | 16 | 15 | 16 | 16 | +4 |
| 24 | 2026-08-12 16:08 | v1 | P6 | C2 | 80/80 | 16 | 16 | 16 | 16 | 16 | +0 |
| 25 | 2026-08-12 16:20 | v2 | P6 | C2 | 77/80 | 16 | 15 | 14 | 16 | 16 | -2 ⚠ |
| 26 | 2026-08-12 16:33 | v3 | P6 | C2 | 77/80 | 16 | 14 | 15 | 16 | 16 | +5 |
| 27 | 2026-08-12 16:47 | v4 | P6 | C2 | 75/80 | 16 | 14 | 14 | 15 | 16 | -2 ⚠ |
| 28 | 2026-08-12 17:04 | v5 | P6 | C2 | 79/80 | 16 | 15 | 16 | 16 | 16 | +8 |

### Readings (kept separate from volume/coverage claims)

- First exposure of each new bank is the honest capability signal:
  v1 68, v2 75, v3 56, v4 68, v5 71 (avg 80%). Post-intervention retests
  recover to 91-100% — improvement on known questions, expected under a
  development-set regime.
- Clarity and citations are ceiling-level throughout; correctness and
  gap-honesty carry nearly all variance. First-exposure correctness
  averages 58%.
- Run-to-run noise on identical config (e.g. rows 17-19 vs 13-15, same
  persona/corpus, same day) spans ±5 points; single-run deltas smaller
  than that should not be attributed to interventions.
- The 08-12 intervention (P6 + C2 together) confounds persona and corpus
  effects; per ticket 2803 these are versioned separately going forward.

### Per-run comment template (subsequent runs go in comments)

```
Run: <YYYY-MM-DD HH:MM ET> | Evaluator: <name>
Bank: <version> (frozen hash <prefix>) | Persona: <P#> (<sha256 prefix>)
Corpus: <state/digest> | KB ingestion: <id>
Overall: <n>/80 | Cit <n> Cor <n> Gap <n> Scope <n> Clar <n>
Changed since last run: <one line>
Regressions: <question ids + one line each, or "none">
Decision(s): <any>
```
