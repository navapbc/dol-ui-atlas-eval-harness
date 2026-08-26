# Daily CA-7 knowledge package reconciliation — 2026-08-24

Restricted record for issue 2802. Contains program/JCL member names;
identifier-class sign-off is still pending in the source matrix, so the
GitHub comment cites counts only and points here.

Performed by: M. Angeli. Method: manifest.csv index vs. filesystem, plus
re-validation of both Phase 0 snapshots.

## Inputs

| Item | Value |
|---|---|
| Mirror root | `~/projects/aws_transform_output/quick_space_ca7_daily_s3/` |
| Sync root | `s3/` (uploaded via `aws s3 sync s3/ s3://<bucket>/<prefix>/ --delete`) |
| Authoritative index | `manifest.csv`, 4,977 data rows, `name,type,s3_key` (CRLF) |
| Build provenance | module cut `modules/LOOPS_ca7_reachable_daily_v2/`, BRE run `bre_output_20260707_185313` |
| S3 target | `dol-dev2-transform-poc/quick-loops/kb_CA7_daily` |

## Index vs. filesystem

| Check | Result |
|---|---|
| manifest rows present on disk | 4,977 / 4,977 — zero missing |
| files on disk | 4,980 |
| on disk but not indexed | 3 (below) |

Unindexed objects:

1. `docs/05_job_purpose_index.md` — added in the 2026-08-12 push
2. `docs/06_terminology_glossary.md` — added in the 2026-08-12 push
3. `.DS_Store` (sync root) — macOS artifact, not a corpus document

`.DS_Store` sits inside the `s3/` sync root, so `aws s3 sync` has been
uploading it. Assume it is present in the bucket and ingested by the
Quick space as a document until checked. Remediation: delete it, add
`--exclude ".DS_Store"` to the sync, re-snapshot.

The two new docs were never added to `manifest.csv`, so the index no
longer describes the uploaded set. Either regenerate it or add the rows.

## Prefix counts (disk, excluding .DS_Store)

| Prefix | Files | README table |
|---|--:|--:|
| `docs/` | 7 | 5 |
| `source/jcl/` | 1,864 | 1,864 |
| `source/cobol/` | 470 | 470 |
| `source/copybooks/` | 303 | 303 |
| `bre/cobol/` | 473 | 473 |
| `bre/jcl/` | 1,862 | 1,862 |

`README_S3_UPLOAD.md` still states "Contents (4,977 files)" and `docs/` = 5.
Stale since the 08-12 push.

## BRE coverage asymmetries

**JCL members with no BRE job doc (2)** — matches the known gap in
`README_S3_UPLOAD.md` (Transform misclassified them as folders). Raw JCL
is present in `source/jcl/`; the business-rule doc is absent.

- `D2PAD146`
- `D2PAD152`

**BRE COBOL docs with no source member (3)** — not previously recorded.
Transform produced business rules for three programs whose COBOL is not
in the reachable-daily cut.

- `UIMB0012`
- `UIMB0014`
- `UIMB0134`

Hypothesis: load-module aliasing, as with `UIMI0754` / `UIMB0754` noted
in the source matrix. Unverified. Either the module boundary is drawn
wrong or the BRE run covered more than the cut; both matter for the
comparison corpus.

## Quarantined objects (C2: 222)

| Prefix | Count | Of total in prefix |
|---|--:|--:|
| `source/copybooks/` | 201 | 303 |
| `bre/jcl/` | 14 | 1,862 |
| `docs/` | 6 | 7 |
| `.DS_Store` | 1 | — |

`unknown_quarantined` means Phase 0 did not positively recognize the
shape; it is not a finding of bad content. Two observations:

- 201 of 303 copybooks unrecognized is a detector-coverage gap, not a
  corpus gap. Worth a detector pass before the copybooks are relied on.
- The 6 quarantined `docs/` objects include both 08-12 additions. The
  leakage review already recommends excluding those from the OKF bundle
  input, so Phase 0 and the leakage review agree independently.

Quarantined `bre/jcl` objects (14), all small:

`D2FLD635` `D2PAD503` `D2PAD608` `D2PAD635` `L205DY` `L206DL` `L214DE`
`L215DZ` `L216DZ` `L217DZ` `L2DEMAIL` `L2FITD02` `ZUMD1QU1` `ZUMD2QU1`

## Snapshot identity and re-validation

Both snapshots re-validated 2026-08-24 with `summarize`; exit 0, manifest
payload hash and all three output hashes intact.

| | C1 | C2 |
|---|---|---|
| Snapshot label | `daily-ca7-bre-2026-08-19` | `daily-ca7-bre-2026-08-21` |
| Generated (UTC) | 2026-08-19T21:35:10Z | 2026-08-21T15:48:24Z |
| `corpus_manifest_sha256` | `450983fb…50e2b7fc` | `d856d669…5cc42c45` |
| Objects | 4,978 | 4,980 |
| Bytes | 184,346,817 | 184,470,884 |
| `unknown_quarantined` | 220 | 222 |
| `expected_file_count` | null | null |
| `expected_byte_count` | null | null |

Tool identity, both: v0.1.2, package `a52de2d0…e9236f`, detectors
`phase0-detectors-v2`. Other content classes identical across C1/C2
(`raw_source` 2,118, `derived_rule_candidate` 2,031,
`mixed_source_analysis` 609). Detector totals identical across C1/C2 in
every category.

## Mirror lag — affects run attribution

The overview doc changed between the two snapshots:

| Snapshot | `content_sha256` | Bytes |
|---|---|--:|
| C1 (08-19) | `a71b12e174d77a71…` | 4,487 |
| C2 (08-21) | `1438ae52d4279605…` | 6,125 |

The revision was pushed to the Quick space on 2026-08-12, but the local
mirror still held the pre-push version on 08-19 and only carried the
revised one by 08-21. The 4,487 B version matches the archived copy at
`persona_inventory/00_ca7_daily_overview.2026-07-24.md`.

Consequences:

1. The mirror lagged the space by roughly nine days.
2. C2 is the first byte-level record of the content that runs 22-28
   (2026-08-12) were scored against. Its binding to those rows is by
   inference, not contemporaneous capture. The C1/C2 content labels in
   the source matrix are correct; the run-to-digest attribution for
   runs 1-28 is reconstructed.
3. Both snapshots ran with `expected_file_count` and `expected_byte_count`
   null, so the fail-closed count gate was never armed. Arming it would
   have caught the lag at capture time. Use `--expected-files` /
   `--expected-bytes` from here on.

## Not verified

Two claims in `docs/source-matrix.md:37` have no artifact in the repo or
this folder:

- "Mirror verified byte-identical to S3 via MD5/ETag 2026-08-21"
- "Quick KB ingestion `734a4dbd` confirmed synced 2026-08-20"

Both are operator-attested. Re-run and capture output before a second
reviewer signs off; #2802's open AC is exactly that verification.

## Reproduce

```bash
cd ~/projects/aws_transform_output/quick_space_ca7_daily_s3
tail -n +2 manifest.csv | tr -d '\r' | awk -F, '{print $NF}' | sort > /tmp/idx.txt
(cd s3 && find . -type f | sed 's|^\./||' | sort) > /tmp/disk.txt
comm -23 /tmp/idx.txt /tmp/disk.txt   # indexed, absent from disk
comm -13 /tmp/idx.txt /tmp/disk.txt   # on disk, unindexed
```

Note the CRLF strip: without `tr -d '\r'` every row mismatches and the
check silently reports total divergence rather than a real delta.
