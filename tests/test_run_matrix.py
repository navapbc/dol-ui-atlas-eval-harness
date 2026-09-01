import subprocess

from tools.run_matrix import (
    Job, Result, build_jobs, default_run_one, run_matrix, summarize,
)

_A1 = ("Engineering Onboarding Specialist", "id-v1")
_A2 = ("Engineering Onboarding Specialist (v2)", "id-v2")


def test_build_jobs_is_agent_outer_bank_inner():
    jobs = build_jobs([_A1, _A2], ["v1", "v2", "v3"])
    # All of agent 1's banks come before any of agent 2's.
    assert [(j.agent_id, j.bank) for j in jobs] == [
        ("id-v1", "v1"), ("id-v1", "v2"), ("id-v1", "v3"),
        ("id-v2", "v1"), ("id-v2", "v2"), ("id-v2", "v3"),
    ]
    assert jobs[0].bank_path == "data/banks/v1.yaml"


def test_run_matrix_runs_every_job_in_order():
    jobs = build_jobs([_A1], ["v1", "v2"])
    seen = []
    run_matrix(jobs, lambda j: seen.append(j.bank) or Result(j, "complete"),
               log=lambda *_: None)
    assert seen == ["v1", "v2"]


def test_run_matrix_continues_past_a_raising_job():
    jobs = build_jobs([_A1], ["v1", "v2", "v3"])

    def run_one(job):
        if job.bank == "v2":
            raise RuntimeError("boom")
        return Result(job, "complete")

    results = run_matrix(jobs, run_one, log=lambda *_: None)
    assert [r.status for r in results] == ["complete", "error", "complete"]
    assert "boom" in results[1].detail  # the failure is captured, not lost


def test_run_matrix_continues_past_a_failed_job():
    jobs = build_jobs([_A1], ["v1", "v2"])
    results = run_matrix(
        jobs,
        lambda j: Result(j, "failed" if j.bank == "v1" else "complete"),
        log=lambda *_: None,
    )
    assert [r.status for r in results] == ["failed", "complete"]


class _Proc:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def _job():
    return Job("Engineering Onboarding Specialist", "id-v1", "v7",
               "data/banks/v7.yaml")


def _run_one(proc_or_exc, times=(0.0, 12.5)):
    """default_run_one with an injected runner and a two-tick clock."""
    ticks = iter(times)

    def runner(cmd, **kwargs):
        if isinstance(proc_or_exc, Exception):
            raise proc_or_exc
        runner.cmd = cmd
        return proc_or_exc
    return default_run_one(
        _job(), url="u", account_id="acct", runs_dir="data/runs",
        tab="Favorites", profile_dir=".auth/quick-profile", timeout_s=60,
        runner=runner, clock=lambda: next(ticks),
    ), runner


def test_default_run_one_classifies_a_clean_run_as_complete():
    out = ("2026-09-01_1136_quick_playwright_v7: complete\n"
           "  answers: 2   scored rows: 2   deterministic_pass: 0/2\n"
           "  written to data/runs/2026-09-01_1136_quick_playwright_v7\n")
    result, runner = _run_one(_Proc(0, stdout=out))
    assert result.status == "complete"
    assert result.run_id == "2026-09-01_1136_quick_playwright_v7"
    assert "deterministic_pass: 0/2" in result.detail
    assert result.seconds == 12.5
    # The bank and agent made it onto the command line.
    assert "--agent-id" in runner.cmd and "id-v1" in runner.cmd
    assert "data/banks/v7.yaml" in runner.cmd


def test_default_run_one_classifies_a_nonzero_exit_as_failed():
    result, _ = _run_one(_Proc(2, stderr="error: AUTH_REQUIRED: bounced to login"))
    assert result.status == "failed"
    assert "AUTH_REQUIRED" in result.detail


def test_default_run_one_classifies_a_timeout():
    result, _ = _run_one(subprocess.TimeoutExpired(cmd="x", timeout=60))
    assert result.status == "timeout"
    assert "60" in result.detail


def test_summarize_tallies_and_lists_every_cell():
    jobs = build_jobs([_A1], ["v1", "v2"])
    results = [
        Result(jobs[0], "complete", "deterministic_pass: 2/2", run_id="run-a"),
        Result(jobs[1], "failed", "AUTH_REQUIRED"),
    ]
    text = summarize(results)
    assert "2 cell(s)" in text
    assert "complete=1" in text and "failed=1" in text
    assert "run-a" in text
    assert "AUTH_REQUIRED" in text  # failure detail shown
