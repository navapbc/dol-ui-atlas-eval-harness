# Quick Chat Audit — Bank v4 — 2026-08-07 14:40

**Run context:** RULES-V4 REGRESSION RUN (see the 1406 report). Observational only
per the over-tuning guard. Internet off, KB unchanged. Baselines: internet-off
morning run 2026-08-07 11:31 (77/80), post-KB-fix 2026-08-05 17:18 (78/80).

- Conversation: 8d08f972-82f6-4500-a8bf-44fed2e37030
- Graded against `v4_answer_key.md`
- Snapshots: `snapshots/2026-08-07_1440_*.json` (persona rules v4 verified in
  CustomInstructions; space doc counts unchanged from 08-05)

## Score: 77/80

| Q | Type | Cit | Corr | Gap | Scope | Clar | Total |
|---|------|-----|------|-----|-------|------|-------|
| Q1 | retrieval (data architecture) | 2 | 1 | 2 | 2 | 2 | 9 |
| Q2 | retrieval | 2 | 1 | 2 | 2 | 2 | 9 |
| Q3 | retrieval | 2 | 2 | 2 | 2 | 2 | 10 |
| Q4 | boundary probe (split scope) | 2 | 2 | 2 | 2 | 2 | 10 |
| Q5 | retrieval (VERIS retest) | 2 | 1 | 2 | 2 | 2 | 9 |
| Q6 | spec-derived bait / scope boundary | 2 | 2 | 2 | 2 | 2 | 10 |
| Q7 | conflict surfacing | 2 | 2 | 2 | 2 | 2 | 10 |
| Q8 | retrieval + system boundary | 2 | 2 | 2 | 2 | 2 | 10 |

## Findings — three rules-v4 target behaviors landed

1. **Q7: FIRST FULL-CREDIT CONFLICT SURFACING (was 0-for-6 across all prior runs).**
   The answer contains an explicit "⚠️ Documented Conflict" section quoting and
   citing both readings (DXCBDA2R BRE = WEB vs UIMB0440 BRE = SIM 926 automated
   phone for Operator 9000 + Terminal '7777'), states "the documentation does not
   resolve which label is correct... This needs SME confirmation," and draws the
   practical conclusion that IVR cannot be reliably distinguished from web in the
   data today. The system-evolution hypothesis it offers is labeled as speculation,
   not used to adjudicate. Gap-honesty 2/2 for the first time on this question type.
   Caveat: the same run's v3-Q6 stayed silent-merge, so surfacing still depends on
   the question asking how to tell the channels apart.
2. **Q6: the hedged-attribution pull did NOT recur** (it had appeared in all 3 prior
   sightings of this bait: LOFBSBLD on 08-05, LOF7SBLD on 08-07 morning). This run
   states cleanly that the program, the code-7 response, and the code list are not
   in the linked spaces, presents VERISB/LOF7SBLD/LOF8SBLD only as documented
   adjacent context with an explicit "neither is documented as producing" the
   message, and recommends a source grep instead of naming a most-likely candidate.
3. **Q1: the new KB-bounded impact-analysis SCOPE clause is quoted almost verbatim**
   ("per the grounding rules this is bounded by KB coverage. Dynamically called
   programs, CICS online transactions, and DEMANDed jobs may also access it").

## Docks (all retrieval-shaped, none rules-v4 regressions)

- Q1 (9): the D2PAD140/D2PAD168 rows in the SG01-readers table blur the DB2 table
  vs the DABSSG01 VSAM cluster distinction the key calls out.
- Q2 (9): no false absences this run (morning's L2NHD001-undocumented did not
  recur), but the pipeline walked is the L2NHD011 → UIMB0134 → ZULDNHR* → ZLPDN1R*
  → DXCBNHR1 refund-oriented slice; the UIMB0147 letters leg and
  L2NHD001/L2NHD003/DXNHCM18 were missed.
- Q5 (9): core retest anchors held (VERIS, '00000110', UIMV_SSN_VALIDITY,
  UIMV_SSN_RETIRED, circuit breaker, results-landing), ICON/UIQ correctly bounded,
  but no JCL job named and UIMB0004 unretrieved again (4th consecutive miss of that
  specific member; inserts attributed to UIMB0025/0072, both grounded).

## Quadruple-rerun summary (rules-v4 regression, 2026-08-07 afternoon)

| Bank | This run | Morning (internet-off) | 08-05 post-fix |
|------|----------|------------------------|----------------|
| v1 | 80 | 79 | 80 |
| v2 | 75 | 75 | 80 |
| v3 | 72 | 77 | 73 |
| v4 | 77 | 77 | 78 |
| **Total** | **304** | **308** | **311** |

Verdict: **rules v4 are safe to keep.** No over-refusal (v1 = 80/80, verified
formulas still stated as confirmed), and the three behaviors rules v4 targeted all
improved (own-prior-output self-correction on v3-Q2, first conflict-surfacing 10 on
v4-Q7, hedged-attribution pull gone on v4-Q6). The 304-vs-308 delta sits entirely on
known-fragile pre-existing behaviors (v3-Q5 screens bait half-sprung after bouncing
in the morning; v2-Q6 CWE-Saturday failed identically in both runs). Run time ~44 min
for all four banks (13:54–14:40).
