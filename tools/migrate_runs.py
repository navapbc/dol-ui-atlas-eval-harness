"""Rebuild run records and the rollup from the legacy audit material.

    python tools/migrate_runs.py --source <quick_chat_audits dir>

Never writes to --source.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from atlas_eval.migrate.runs import migrate_runs
from atlas_eval.runs import regenerate_rollup


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--runs", default="data/runs")
    ap.add_argument("--rollup", default="data/scores.csv")
    ap.add_argument("--scored-by", default="legacy-audit")
    ap.add_argument("--confirmed-by", default=None,
                    help="name of the human who reviewed these scores, if known")
    args = ap.parse_args()

    ids = migrate_runs(Path(args.source), Path(args.runs),
                       args.scored_by, args.confirmed_by)
    for run_id in ids:
        print(f"wrote {run_id}")
    n = regenerate_rollup(Path(args.runs), Path(args.rollup))
    print(f"\n{len(ids)} run(s) migrated; rollup regenerated from {n} complete run(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
