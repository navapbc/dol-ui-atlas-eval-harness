"""Run a whole audit matrix (banks x agents) through the playwright transport,
one `atlas-eval run` per cell, continuing past any cell that fails.

Each cell is a separate `atlas-eval run` subprocess, so every bank gets its own
fresh browser context and a brand-new Quick conversation -- no context bleed
from one bank into the next, exactly like running the CLI by hand. The signed-in
profile is reused, so there is no re-login between cells.

The point of this wrapper over a shell `for` loop is resilience: one bank that
times out, loses its session, or hits the wrong agent must NOT abort the other
thirteen. Every cell's outcome is recorded and printed at the end, and a
non-complete cell is left for a targeted re-run.

    .venv/bin/python tools/run_matrix.py \\
      --url "https://us-east-1.quicksight.aws.amazon.com/sn/account/njuimod/start/home" \\
      --account-id 298632317228 \\
      --agents "Engineering Onboarding Specialist:093ac4e3-0712-481e-af95-9ddc5e4fc734" \\
      --banks v1,v2,v3,v4,v5,v6,v7

Run one agent's chunk at a time (session-expiry hedge) by passing a single
--agents entry, as above; pass both (comma-separated) for the full matrix.
"""

from __future__ import annotations

import argparse
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Job:
    agent_name: str
    agent_id: str
    bank: str          # short label, e.g. "v3"
    bank_path: str     # e.g. "data/banks/v3.yaml"


@dataclass
class Result:
    job: Job
    status: str        # "complete" | "failed" | "timeout" | "error"
    detail: str = ""
    run_id: str | None = None
    seconds: float = 0.0


def build_jobs(agents: list[tuple[str, str]], banks: list[str],
               banks_dir: str = "data/banks") -> list[Job]:
    """Cartesian product, agent-outer so one agent's whole set finishes before
    the next begins -- if the session lapses mid-matrix, the completed agent's
    chunk is whole rather than every agent half-done."""
    jobs = []
    for name, agent_id in agents:
        for bank in banks:
            jobs.append(Job(name, agent_id, bank, f"{banks_dir}/{bank}.yaml"))
    return jobs


def run_matrix(jobs: list[Job], run_one, log=print) -> list[Result]:
    """Run every job, never raising: a run_one that raises is captured as an
    'error' Result and the loop moves on, so a single bad cell cannot abort the
    matrix."""
    results: list[Result] = []
    for i, job in enumerate(jobs, 1):
        head = f"[{i}/{len(jobs)}] {job.agent_name} x {job.bank}"
        log(f"{head}: starting")
        try:
            result = run_one(job)
        except Exception as err:  # noqa: BLE001 -- resilience is the whole point
            result = Result(job, "error", f"{type(err).__name__}: {err}")
        results.append(result)
        log(f"{head}: {result.status}"
            + (f" ({result.detail})" if result.detail else ""))
    return results


def default_run_one(job: Job, *, url: str, account_id: str, runs_dir: str,
                    tab: str, profile_dir: str, timeout_s: float,
                    runner=subprocess.run, clock=time.monotonic) -> Result:
    """Run one cell as an `atlas-eval run` subprocess and classify the outcome
    from its exit code and last line of output."""
    cmd = [
        "atlas-eval", "run",
        "--bank", job.bank_path,
        "--transport", "playwright",
        "--url", url,
        "--agent-name", job.agent_name,
        "--agent-id", job.agent_id,
        "--agent-tab", tab,
        "--account-id", account_id,
        "--runs", runs_dir,
        "--profile-dir", profile_dir,
    ]
    start = clock()
    try:
        proc = runner(cmd, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return Result(job, "timeout",
                      f"exceeded {int(timeout_s)}s", seconds=clock() - start)
    seconds = clock() - start
    out = (proc.stdout or "") + (proc.stderr or "")
    lines = [ln for ln in out.splitlines() if ln.strip()]
    if proc.returncode == 0:
        # First line is "<run_id>: complete"; the detail line has the score.
        run_id = lines[0].split(":", 1)[0].strip() if lines else None
        detail = next((ln.strip() for ln in lines
                       if "deterministic_pass" in ln), "")
        return Result(job, "complete", detail, run_id=run_id, seconds=seconds)
    return Result(job, "failed",
                  lines[-1] if lines else f"exit {proc.returncode}",
                  seconds=seconds)


def summarize(results: list[Result]) -> str:
    counts: dict[str, int] = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    order = ["complete", "failed", "timeout", "error"]
    tally = "  ".join(f"{k}={counts[k]}" for k in order if k in counts)
    rows = [f"  {r.status:9} {r.job.agent_name} x {r.job.bank}"
            + (f"  {r.run_id}" if r.run_id else "")
            + (f"  ({r.detail})" if r.detail and r.status != "complete" else "")
            for r in results]
    return f"matrix: {len(results)} cell(s) -- {tally}\n" + "\n".join(rows)


def _parse_agents(raw: str) -> list[tuple[str, str]]:
    agents = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if ":" not in entry:
            raise SystemExit(f"error: --agents entry {entry!r} must be "
                             "'Display Name:agent-id'")
        name, agent_id = entry.rsplit(":", 1)
        agents.append((name.strip(), agent_id.strip()))
    return agents


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--account-id", required=True)
    ap.add_argument("--agents", required=True,
                    help="comma-separated 'Display Name:agent-id' entries")
    ap.add_argument("--banks", default="v1,v2,v3,v4,v5,v6,v7")
    ap.add_argument("--banks-dir", default="data/banks")
    ap.add_argument("--runs", default="data/runs")
    ap.add_argument("--tab", default="Favorites")
    ap.add_argument("--profile-dir", default=".auth/quick-profile")
    ap.add_argument("--per-bank-timeout", type=float, default=1800.0,
                    help="seconds before a single cell is killed (default 1800)")
    ap.add_argument("--dry-run", action="store_true",
                    help="list the cells that would run, then exit")
    args = ap.parse_args()

    agents = _parse_agents(args.agents)
    banks = [b.strip() for b in args.banks.split(",") if b.strip()]
    jobs = build_jobs(agents, banks, args.banks_dir)

    if args.dry_run:
        print(f"{len(jobs)} cell(s):")
        for j in jobs:
            print(f"  {j.agent_name} x {j.bank}  ({j.bank_path})")
        return 0

    def run_one(job: Job) -> Result:
        return default_run_one(
            job, url=args.url, account_id=args.account_id, runs_dir=args.runs,
            tab=args.tab, profile_dir=args.profile_dir,
            timeout_s=args.per_bank_timeout,
        )

    results = run_matrix(jobs, run_one)
    summary = summarize(results)
    print("\n" + summary)

    stamp = time.strftime("%Y-%m-%d_%H%M")
    log_path = Path(args.runs) / f"_matrix_{stamp}.log"
    log_path.write_text(summary + "\n")
    print(f"\nlog: {log_path}")

    # Non-zero exit if any cell did not complete, so a caller (or the operator)
    # notices without reading the whole table.
    return 0 if all(r.status == "complete" for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
