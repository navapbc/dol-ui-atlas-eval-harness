# DRAFT — 2802 reconciliation comment (not posted, pending review)

Contains no program identifiers, member names, source content, or
restricted values; member-level detail stays in the restricted audit
folder at `one_offs/2026-08-24_2802_reconciliation.md`.

---

## Reconciliation evidence — Daily CA-7 knowledge package (2026-08-24)

Recording the completeness check behind the checked ACs above, which
until now had no evidence on this ticket. Method: the package's own
`manifest.csv` index (4,977 rows, `name,type,s3_key`) reconciled against
the filesystem of the sync root, plus re-validation of both Phase 0
snapshots. Member-level detail is in the restricted evaluation folder;
this comment records counts and digests only.

Package provenance: module cut `LOOPS_ca7_reachable_daily_v2`, BRE run
`bre_output_20260707_185313`, synced to the bucket prefix the Quick space
reads. Note that module-cut name is unrelated to the `kb_CA7_daily_v2`
bucket prefix discussed under #2829 — two different "v2"s, and this one
belongs to the *current* corpus.

### Completeness check

| Check | Result |
|---|---|
| Indexed objects present on disk | 4,977 / 4,977 — zero missing |
| Objects on disk | 4,980 |
| On disk but not in the index | 3 |

The three unindexed objects are accounted for: two are the documentation
files added in the 2026-08-12 push (job purpose index, terminology
glossary), and one was a stray macOS `.DS_Store` in the sync root. No
duplicates, no failed or truncated documents, no orphaned index rows.

The `.DS_Store` was confirmed absent from the bucket and deleted locally
on 2026-08-24, so the sync root is now 4,979 files and matches S3 exactly.

`manifest.csv` was not regenerated after the 08-12 push, so the index no
longer describes the uploaded set. `README_S3_UPLOAD.md` is stale for the
same reason (still states 4,977 files).

### S3 verification (captured 2026-08-24)

| Check | Result |
|---|---|
| Keys matched | 4,979 / 4,979 |
| ETag vs local MD5 mismatches | 0 |
| Size mismatches | 0 |
| Total bytes, both sides | 184,464,736 |
| Multipart ETags | 0 (all single-part, so ETag == MD5 is valid) |

The local mirror and the bucket prefix the space reads are byte-identical.
Output is captured in the restricted evaluation folder. This supersedes
the previously unartifacted MD5/ETag assertion in the source matrix.

S3 upload timestamps independently corroborate the corpus history: 4,977
objects dated 2026-07-24 and exactly 3 dated 2026-08-12, matching the
three-file push described in the leakage review on #2803.

### Snapshot identity

| | | | |
|---|---|---|---|
| Snapshot | `daily-ca7-bre-2026-08-19` | `daily-ca7-bre-2026-08-21` | `daily-ca7-bre-2026-08-24` |
| Generated (UTC) | 2026-08-19T21:35:10Z | 2026-08-21T15:48:24Z | 2026-08-24T18:31:06Z |
| `corpus_manifest_sha256` | `450983fb…50e2b7fc` | `d856d669…5cc42c45` | `9eb8aa8d…87eea12d` |
| Objects / bytes | 4,978 / 184,346,817 | 4,980 / 184,470,884 | 4,979 / 184,464,736 |
| Count gate armed | no | no | **yes** |

All three re-validated 2026-08-24: manifest payload hash and all output
hashes intact. Tool v0.1.2, package `a52de2d0…e9236f`, detectors
`phase0-detectors-v2`. The 08-24 snapshot is the first byte-identical to
S3 and the first taken with `--expected-files` / `--expected-bytes`
engaged. Snapshots are referenced by label and digest throughout; the
C0/C1/C2 corpus-state letters used in #2801 are avoided here because the
two schemes disagree on what C1 means. Snapshots are metadata-only and remain
`BLOCKED_FOR_PUBLICATION`; they establish file accountability and byte
identity, nothing about content correctness.

### Three findings that revise the ACs above

**1. AC 3 unchecked — identified gaps were never corrected.** Two JCL members still have no BRE job doc; this is the
Transform folder-misclassification gap already noted in the package
README, and the raw JCL is present while the business-rule document is
absent. Separately, three BRE COBOL documents have no corresponding
source member in the cut, which is a module-boundary question and was
not previously recorded. Load-module aliasing is the likely explanation
but is unverified. The stray `.DS_Store` has been corrected (verified
absent from the bucket, deleted locally 2026-08-24), but the two BRE
coverage gaps remain, and the AC reads "identified **and corrected**."

Both gaps are recorded here as accepted limitations of the v1 baseline
rather than scheduled work. #2829 ships a v2 cut with 1:1 BRE coverage
and missing/no-BRE registers, so fixing them in v1 may be moot. Resolution
defers to #2829's outcome: if the specialist stays on v1, a fix ticket
gets filed then; if it switches to v2, this AC closes as superseded.

**2. AC 4 holds going forward but not retroactively.** The overview
document in the local mirror was still the pre-push version at the 08-19
snapshot and only became the revised version by 08-21, so the mirror
lagged the space by roughly nine days. The 08-21 snapshot is therefore
the first byte-level record of the content that the 2026-08-12 runs were scored
against, and its binding to those run rows is by inference rather than
contemporaneous capture. The corpus-state labels in the source matrix are
correct; the run-to-digest attribution for the backfilled runs in
 #2801 is reconstructed, consistent with the caveat already recorded
there. Both snapshots also ran with `expected_file_count` and
`expected_byte_count` unset, so the tool's fail-closed count gate was
never armed — arming it would have caught the lag at capture time.
Adopting `--expected-files` / `--expected-bytes` from here on.

**3. Phase 0 independently corroborates the leakage review.** Six of the
seven documentation objects classify as `unknown_quarantined`, including
both 08-12 additions, which the leakage review on #2803 already
recommends excluding from the OKF bundle input. Two mechanisms, same
conclusion. Also worth flagging for coverage: 201 of 303 copybooks are
unrecognized by the current detectors. That is a detector-coverage gap
rather than a corpus gap, but the copybooks should not be leaned on for
answer grading until it is closed.

### Still open on this ticket

- **Before/after focused Daily CA-7 benchmark — recommend marking
  superseded, not satisfied.** It can no longer be run cleanly: the AC 3
  corrections were never made and the 08-12 content push is already in
  place, so a before/after would confound the sync correction with the
  push. #2829 runs a corpus-vs-corpus A/B across two specialists, which is
  a different experiment and does not substitute for this control. Marking
  it superseded keeps the record honest; leaving it open implies the
  control is still coming.
- **Score changes recorded in the tracker.** Moot if the above is
  superseded; otherwise blocked on it.
- **Second-reviewer verification — Morgan Robertson.** The S3 side now has
  captured output (above), so the evidence is reviewable. The KB ingestion
  assertion (`734a4dbd` confirmed synced) remains operator-attested
  without a console export and is the one item still lacking an artifact.

### Prefix-collision incident, 2026-08-24 — resolved

The sibling prefix `kb_CA7_daily_v2` (3,956 objects, uploaded 17:26 UTC
2026-08-24 for #2829) collided with this space's include path, which was
written as `quick-loops/kb_CA7_daily` with no trailing slash. The
connector matched it as a literal prefix, so a forced sync began ingesting
the v2 corpus into the v1 space.

This is the "duplicate, stale, or failed documents" class AC 3 covers,
found live rather than by the reconciliation:

- The two corpora share 2,939 relative paths and differ in content at
  **every one**, so v2 documents land under v1 document names. Document
  count alone cannot detect this.
- The sync was stopped, the include path replaced with three explicit
  prefixes (`/bre`, `/docs`, `/source` — a trailing slash could not be
  saved in the console), and the space resynced. Verified 2026-08-24:
  those three prefixes cover 2,335 + 7 + 2,637 = 4,979 objects, every v1
  object, and match nothing under `kb_CA7_daily_v2`.
- Repair confirmed by content probe, not by count: the agent was asked the
  v5-Q4 week-ending-date question and cited the revised overview's
  "derived, not enforced" section, which exists only in the v1 copy.

Two consequences to carry forward. Any run between the first forced sync
and the verified repair is unsafe to compare and #2801 needs a boundary
marker. And #2829's constraint that v1 "stays untouched" needs this
disclosed: v1 was contaminated and repaired, not untouched.

**Maintenance risk introduced by the fix:** because the include list now
enumerates subdirectories, any new top-level folder added under
`kb_CA7_daily/` will be silently excluded until added. Recorded in the
source matrix.

`kb_CA7_daily_v2` still has no Phase 0 snapshot, no source-matrix row, and
no approval for this use. Those are prerequisites for #2829 rather than
findings against this ticket.

Reconciliation by: M. Angeli, 2026-08-24; second reviewer Morgan
Robertson (#2829 assignee). Reproduction steps and
member-level findings in the restricted evaluation folder.
