#!/usr/bin/env bash
# Capture S3-vs-local byte identity for the Daily CA-7 package.
# Output is the artifact the 2802 second-reviewer AC needs.
# ETag == MD5 holds only for single-part uploads; this package averages
# ~37 KB/object, so all objects should be single-part. Multipart ETags
# carry a "-N" suffix and are reported separately rather than compared.
set -euo pipefail

MIRROR="$HOME/projects/aws_transform_output/quick_space_ca7_daily_s3/s3"
BUCKET="dol-dev2-transform-poc"
PREFIX="quick-loops/kb_CA7_daily/"
OUT="$(dirname "$0")/$(date +%Y-%m-%d)_s3_etag_verification.txt"

{
  echo "S3 vs local verification"
  echo "date:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "mirror: $MIRROR"
  echo "target: s3://$BUCKET/$PREFIX"
  echo "caller: $(aws sts get-caller-identity --query Arn --output text)"
  echo

  aws s3api list-objects-v2 --bucket "$BUCKET" --prefix "$PREFIX" \
    --query 'Contents[?Size>`0`].[Key,ETag,Size]' --output text \
  | sed "s|^$PREFIX||" | tr -d '"' | sort > /tmp/s3_objs.tsv

  ( cd "$MIRROR" && find . -type f ! -name .DS_Store | sed 's|^\./||' | sort \
    | while read -r f; do
        printf '%s\t%s\t%s\n' "$f" "$(md5 -q "$f")" "$(stat -f%z "$f")"
      done ) > /tmp/local_objs.tsv

  echo "objects in S3:    $(wc -l < /tmp/s3_objs.tsv)"
  echo "objects local:    $(wc -l < /tmp/local_objs.tsv)"
  echo "multipart ETags:  $(grep -c -- '-[0-9]*$' /tmp/s3_objs.tsv || true)"
  echo
  echo "--- in S3, not local ---"
  comm -23 <(cut -f1 /tmp/s3_objs.tsv) <(cut -f1 /tmp/local_objs.tsv)
  echo "--- local, not in S3 ---"
  comm -13 <(cut -f1 /tmp/s3_objs.tsv) <(cut -f1 /tmp/local_objs.tsv)
  echo "--- checksum mismatches (key: s3_etag local_md5) ---"
  join -t$'\t' /tmp/s3_objs.tsv /tmp/local_objs.tsv \
    | awk -F'\t' '$2 != $4 {print $1": s3="$2" local="$4}'
  echo "--- end ---"
} | tee "$OUT"

echo
echo "captured: $OUT"
