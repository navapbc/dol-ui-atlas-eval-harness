# Persona and overview documentation inventory (ticket 2803, AC1)

Status: initial inventory, taken 2026-08-21 by michaelangeli@navapbc.com.
Location note: kept in the restricted local audit folder (with the run
snapshots and answer keys); GitHub gets summaries only, per ticket
constraints. This file is the versioned index; changes to any artifact
below get a new row in the change log.

## 1. Agent persona (Amazon Quick)

| Field | Value |
|---|---|
| Agent | Engineering Onboarding Specialist, `093ac4e3-0712-481e-af95-9ddc5e4fc734` |
| Lifecycle / status | PUBLISHED / ACTIVE |
| Last updated | 2026-08-12T14:46:39-04:00 (same day as the corpus content push) |
| Custom instructions | 8,085 chars; sha256 `e915330bdbfd5f7ec2616c8664eee81bc131d0f1125166a9752a70c6d65c3c86` |
| Full config snapshot | `agent_093ac4e3_2026-08-21.json` (sha256 `a7824b447f2343d14b97d4218cce91cee8344699a0d9149c89db4f78f5d3ec9f`) |
| Role | Defines answer structure, citation expectations, fact-vs-inference distinction (see promptSummary in snapshot) |
| Linked spaces (7) | DailyUI, NewHire, CWC, WGPM, Weekly Certification, Monthly CA-7, Daily CA-7 |
| Also carries | 3 starter prompts, welcome message, model profile `1be676b3-c664-4152-93f8-52064c1c0fbe` |

Prior versions: per-run `describe-agent` snapshots exist in `snapshots/`
for benchmark runs since v1; those capture the pre-2026-08-12 persona.

## 2. Overview / acronym documentation (Daily CA-7 space)

All live in S3 `dol-dev2-transform-poc/quick-loops/kb_CA7_daily/docs/`
(ingested into the Quick KB, last ingestion 2026-08-20 04:19 EDT).

| Doc | Role | Versions known |
|---|---|---|
| `docs/00_ca7_daily_overview.md` | System boundaries / module overview | 2026-07-24 (4,487B, archived here as `00_ca7_daily_overview.2026-07-24.md`) → 2026-08-12 (6,125B, current) |
| `docs/05_job_purpose_index.md` | Per-job purpose index | added 2026-08-12 (118,633B) |
| `docs/06_terminology_glossary.md` | Acronym / terminology guidance | added 2026-08-12 (3,796B) |

Local mirror (`quick_space_ca7_daily_s3/s3/`) verified byte-identical to
S3 on 2026-08-24: 4,979/4,979 keys, zero ETag-vs-MD5 mismatches,
184,464,736 bytes both sides, no multipart ETags. Capture:
`one_offs/2026-08-24_s3_etag_verification.txt` (the 2026-08-21 assertion
had no artifact; this supersedes it). Corpus digests: `450983fb…`,
`d856d669…`, and current `9eb8aa8d…` (snapshot
`daily-ca7-bre-2026-08-24`, 4,979 objects after a stray `.DS_Store` was
removed from the sync root; first snapshot taken with the fail-closed
count gate armed). See the loops-knowledge-base source matrix.

## 3. Change log

Rows before 2026-08-21 are retroactive reconstructions, built from the
per-run config snapshots in `snapshots/` and the run history in ticket
2801. Persona versions are identified by sha256 of the instruction text.

| Date | Artifact(s) | Change | Rationale | Review |
|---|---|---|---|---|
| 2026-07-27 | Persona P1 → P2 (`ffafa14af0ac` → `302275d611a2`, 614 → 3,176 chars) | Baseline instructions replaced with a structured prompt (answer format, citation expectations, fact-vs-inference framing) | Response to the v1 baseline run the same morning (68/80; gap-honesty 11/16, scope 11/16 were the weak dimensions). Same-day retest scored 79/80 | None at the time. Retroactive entry |
| 2026-08-03 | Persona P2 → P3 (`302275d611a2` → `e2a667989300`, 3,176 → 4,154 chars) | Instructions expanded | Response to the v3 first-exposure run earlier that day (56/80 — the lowest recorded; correctness 7/16). v3 retest the same afternoon scored 68/80 | None at the time. Retroactive entry |
| 2026-08-07 | Persona P3 → P4 (`e2a667989300` → `346edf615ffa`, 4,154 → 4,935 chars) | Instructions expanded | Response to the v4 first-exposure run of 2026-08-05 (68/80; gap-honesty 9/16). Note the v1/v2/v4 retests immediately after this change went *down* (-1, -5, -1), within the ±5 same-config noise band | None at the time. Retroactive entry |
| 2026-08-07 | Persona P4 → P5 (`346edf615ffa` → `3e0a1ecbfb0b`, 4,935 → 7,063 chars) | Instructions expanded substantially (+2,128 chars) same day as P4 | Response to the v3 regression in the 14:06-14:27 run block (72/80, -5 vs. the morning). Two persona revisions in one day means P4's effect is not separable from P5's | None at the time. Retroactive entry |
| 2026-08-12 | Persona P5 → P6 (`3e0a1ecbfb0b` → `e915330bdbfd`, 7,063 → 8,085 chars); overview doc revised; job purpose index (new); glossary (new) | Persona revised + 3-doc content push, same day | Response to the v5 first-exposure run (71/80). Persona and corpus changed together, so their effects are confounded for runs 22-23 | Not reviewed at the time. Leakage review completed 2026-08-21: CONFIRMED benchmark-specific guidance in P6 (v1-Q3 grading distinction) and CONFIRMED v5-Q4 answer in the revised overview. See section 4 |
| 2026-08-21 | This inventory | Created; current persona and config hashed | 2803 AC1 | Second review pending (Billy) |
| 2026-08-24 | Daily CA-7 space include paths | Single prefix `quick-loops/kb_CA7_daily` replaced with three explicit prefixes (`/bre`, `/docs`, `/source`) | The single prefix was matched literally and also pulled in the sibling `kb_CA7_daily_v2` corpus during a forced sync; v2 documents landed under v1 document names. A trailing slash could not be saved in the console | Repair verified by content probe (v5-Q4 question returned the v1 overview's "derived, not enforced" section). Recorded on tickets 2802 and 2829 |

**Pattern this backfill establishes:** every persona revision from P1 to P6
was triggered by a benchmark result, and each was followed by a retest on
the same banks. This is the same intervention-response loop the 2026-08-12
leakage review flagged for the documentation, applied to the prompt across
the whole series. It does not by itself mean each revision encodes answer
content — only P6 was confirmed to do that — but it does mean v1-v5 scores
after any of these dates measure improvement on known questions. The 10
held-out v6 questions (exposure `none` in the frozen set) are unaffected.

## 4. Open items against 2803

- Leakage review of the 2026-08-12 persona + docs (AC7): first-pass scan
  2026-08-21 found benchmark-adjacent content in the instructions:
  (a) CONFIRMED benchmark-specific guidance: the persona hard-codes the
  v1-Q3 grading distinction ("earnings/pension offset arithmetic (UIMI0440)"
  is inference; PWBR/WBR formulas "verified against DXCD037S ... may be
  stated as confirmed") — this is the recurring-conflation dock from the
  v1 answer key, tuned into the prompt. Affects any v1-v5 dev-set retest;
  does NOT affect v6 (no v6 question touches these programs).
  (b) Minor: DXCBDA2R (Q001/Q002 anchor) used as the citation-format
  example.
  (c) Doc scan 2026-08-21 — `00_ca7_daily_overview.md` (08-12 revision):
  CONFIRMED leakage of v5-Q4. The "Week-ending dates: derived, not
  enforced" section reproduces the v5-Q4 answer key's graded content
  (UIMB0018 prev-Saturday tables, UIMB0248 commented-out guard and
  day-of-week math, derived-not-enforced framing, KB-bounded exception),
  pushed 57 minutes after the v5 first-exposure run. The v5 retest that
  evening (79/80, gap-honesty and scope recovered) therefore partly
  measures retrieval of a planted answer.
  (d) Doc scan 2026-08-21 — `05_job_purpose_index.md`: mechanical
  extraction (1,864 job one-liners from JCL comments); no fabricated
  ZLPDYOR rows, no v5 graded chain internals; NOT answer-leaky, but a
  broad retrieval aid unique to Quick's corpus. Grading note: its
  L2AHD13 row fragment ("WILL BE PROCESSED LAST") brushes v6-Q6's
  design-intent answer, though the same fact exists in the JCL/BRE both
  arms hold, so no asymmetric leak.
  (e) `06_terminology_glossary.md`: benign (2 incidental anchor
  mentions).
  Net: v6 remains clean. The exclude-from-bundle-input recommendation
  for these three docs is now evidence-backed, not just precautionary.
- Overview docs traced to approved source evidence (AC4): unverified.
- AC2 (versioning + rationale + review history): MET as of 2026-08-25 —
  section 3 now carries the full P1-P6 series plus the include-path
  change, each with rationale and review status. Retroactive rows are
  labelled as such.
- AC5 (frozen-benchmark evaluation before promotion): still open, and
  blocked on the P6 remediation decision. Forward process: changes get a
  change-log row BEFORE upload and a frozen-benchmark evaluation before
  promotion.
