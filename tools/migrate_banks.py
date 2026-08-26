"""Convert the legacy Markdown bank and answer keys into skeleton bank YAML.

    python tools/migrate_banks.py --source <quick_chat_audits dir> --out data/banks

Emits one vN.yaml per version with `checks` empty, plus each answer key's
non-ground-truth sections to reference/answer_key_notes/. Never writes to
--source. Existing bank files are not overwritten unless --force is given.

Source-shape note: v1-v5 each have a `vN_answer_key.md` with per-question
ground truth. v6 has no answer key file — its section already lives inside
question_bank.md (not a separate table to merge in), and its ground truth is
the bank table's own "Expected behavior" column, which for v6 is written as
full prose rather than shorthand. `v6_draft.md` supplies no additional
ground-truth blocks; it is preserved to answer_key_notes/v6.md as reference
(freeze status, adjudication log) via the same notes path used for the other
versions' non-ground-truth sections.

Two v6 questions (v6-Q9, v6-Q10) carry a "Ground truth in vN_answer_key.md
§RESERVE: ..." pointer instead of prose, because they were revived from an
earlier version's cut RESERVE block. `build_bank` resolves these against the
pre-read `reserve_sources` map (every version's raw answer-key/draft
Markdown, keyed by filename) and moves the original pointer sentence into
`provenance` so the trail back to the source RESERVE block stays visible.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ruamel.yaml import YAML

from atlas_eval.migrate.banks import (
    build_bank, parse_answer_key, parse_answer_key_notes, parse_question_bank,
)

AGENT = "engineering_onboarding_specialist"
CORPUS = "quick_space_ca7_daily_s3"

_yaml = YAML(typ="rt")
_yaml.default_flow_style = False
_yaml.width = 100


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--out", default="data/banks")
    ap.add_argument("--notes-out", default="reference/answer_key_notes")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    src, out = Path(args.source), Path(args.out)
    notes_out = Path(args.notes_out)
    out.mkdir(parents=True, exist_ok=True)
    notes_out.mkdir(parents=True, exist_ok=True)

    versions = parse_question_bank((src / "question_bank.md").read_text(encoding="utf-8"))

    # Pre-read every version's raw answer-key/draft Markdown, keyed by
    # filename, so pointer resolution (e.g. v6's "Ground truth in
    # v3_answer_key.md §RESERVE: ..." referencing v3's file) can look up any
    # version's RESERVE block regardless of processing order.
    reserve_sources: dict[str, str] = {}
    for version in versions:
        for candidate in (src / f"{version}_answer_key.md", src / f"{version}_draft.md"):
            if candidate.exists():
                reserve_sources[candidate.name] = candidate.read_text(encoding="utf-8")

    written = 0
    for version, rows in sorted(versions.items()):
        key_path = src / f"{version}_answer_key.md"
        draft_path = src / f"{version}_draft.md"

        if key_path.exists():
            source_md = reserve_sources[key_path.name]
            source_name = key_path.name
            ground = parse_answer_key(source_md)
        elif draft_path.exists():
            source_md = reserve_sources[draft_path.name]
            source_name = draft_path.name
            ground = parse_answer_key(source_md)
            if not ground:
                # No per-question ### ground-truth blocks in the draft (v6's
                # shape): the bank table's own expected-behavior column is
                # already full prose, so use it directly rather than
                # inventing a block that isn't there.
                ground = {r["id"]: r["expected_behavior"] for r in rows}
        else:
            source_md, source_name, ground = None, None, {}

        if source_md is not None:
            notes = parse_answer_key_notes(source_md)
            (notes_out / f"{version}.md").write_text(notes, encoding="utf-8")

        target = out / f"{version}.yaml"
        if target.exists() and not args.force:
            print(f"skip {target} (exists; use --force to overwrite)")
            continue

        sourcing = f"Migrated from {source_name}." if source_name else None
        bank = build_bank(version, rows, ground, AGENT, CORPUS, sourcing=sourcing,
                          reserve_sources=reserve_sources)
        with target.open("w", encoding="utf-8") as fh:
            _yaml.dump(json.loads(bank.model_dump_json(exclude_none=False)), fh)
        print(f"wrote {target} ({len(bank.questions)} questions, checks empty)")
        written += 1

    print(f"\n{written} bank file(s) written. Fill `checks` by hand next.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
