import csv
from datetime import datetime

import pytest

from atlas_eval.cli import main
from atlas_eval.models import Checks, Question, QuestionType, Stance
from atlas_eval.runs import (
    ROLLUP_COLUMNS, RunMeta, RunStatus, ScoreRow, make_run_id, read_run,
    regenerate_rollup, write_run,
)
from atlas_eval.scoring import Rubric, score_answer

LEGACY = (
    "run_finished", "agent", "agent_id", "bank_version", "question_id", "type",
    "citations", "correctness", "gap_honesty", "scope_discipline", "clarity",
    "total", "conversation_id", "notes",
)


def _meta(**over):
    base = dict(
        run_id="2026-07-27_1119_quick_v1", backend="quick", transport="paste",
        bank_version="v1", question_sha256="a" * 64,
        agent="Engineering Onboarding Specialist",
        agent_id="093ac4e3-0712-481e-af95-9ddc5e4fc734",
        conversation_id="e33bea76-a1f6-4c78-8c1d-9d735e3dfb82",
        started_at=datetime(2026, 7, 27, 11, 19),
        finished_at=datetime(2026, 7, 27, 11, 19),
        harness_git_sha=None, status=RunStatus.COMPLETE,
    )
    base.update(over)
    return RunMeta(**base)


def _row(qid="v1-Q1", **over):
    q = Question(id=qid, text="t", type=QuestionType.RETRIEVAL,
                 expected_stance=Stance.ANSWER, ground_truth="gt",
                 checks=Checks(required_all=["DXCBDA2R"]))
    base = dict(
        question_id=qid, type=QuestionType.RETRIEVAL, verification_status="unverified",
        rubric=Rubric(citations=2, correctness=1, gap_honesty=1,
                      scope_discipline=1, clarity=2, notes="described one program only"),
        deterministic=score_answer(q, "DXCBDA2R does the work"),
    )
    base.update(over)
    return ScoreRow(**base)


def test_rollup_starts_with_the_exact_legacy_columns():
    assert ROLLUP_COLUMNS[: len(LEGACY)] == LEGACY
    assert len(ROLLUP_COLUMNS) > len(LEGACY), "new columns must append, not replace"


def test_make_run_id_matches_the_legacy_timestamp_shape():
    assert make_run_id(datetime(2026, 8, 12, 17, 4), "quick", "v5") == (
        "2026-08-12_1704_quick_v5"
    )


def test_write_then_read_round_trips(tmp_path):
    meta, rows = _meta(), [_row("v1-Q1"), _row("v1-Q2")]
    responses = {"v1-Q1": "DXCBDA2R does the work", "v1-Q2": "second answer"}
    run_dir = write_run(tmp_path, meta, responses, "# transcript\n", {"agent": {}}, rows)

    assert {p.name for p in run_dir.iterdir()} == {
        "run.yaml", "responses.yaml", "transcript.md", "snapshot.json", "scores.csv",
    }
    got_meta, got_responses, got_rows = read_run(run_dir)
    assert got_meta.run_id == meta.run_id
    assert got_meta.status is RunStatus.COMPLETE
    assert got_responses == responses
    assert [r.question_id for r in got_rows] == ["v1-Q1", "v1-Q2"]
    assert got_rows[0].rubric.total == 7


def test_responses_preserve_asked_order(tmp_path):
    meta = _meta()
    responses = {"v1-Q3": "third", "v1-Q1": "first", "v1-Q2": "second"}
    run_dir = write_run(tmp_path, meta, responses, "t", {}, [])
    _, got, _ = read_run(run_dir)
    assert list(got.keys()) == ["v1-Q3", "v1-Q1", "v1-Q2"]


def test_incomplete_run_is_recorded_as_incomplete(tmp_path):
    meta = _meta(status=RunStatus.INCOMPLETE, finished_at=None)
    run_dir = write_run(tmp_path, meta, {"v1-Q1": "partial"}, "t", {}, [_row()])
    got_meta, _, _ = read_run(run_dir)
    assert got_meta.status is RunStatus.INCOMPLETE
    assert got_meta.finished_at is None


def test_rollup_includes_complete_runs_and_excludes_incomplete(tmp_path):
    runs = tmp_path / "runs"
    write_run(runs, _meta(run_id="2026-07-27_1119_quick_v1"),
              {"v1-Q1": "a"}, "t", {}, [_row("v1-Q1")])
    write_run(runs, _meta(run_id="2026-08-01_0900_quick_v1",
                          status=RunStatus.INCOMPLETE, finished_at=None),
              {"v1-Q1": "a"}, "t", {}, [_row("v1-Q1")])

    out = tmp_path / "scores.csv"
    n = regenerate_rollup(runs, out)
    assert n == 1

    with out.open(newline="") as fh:
        reader = csv.DictReader(fh)
        assert tuple(reader.fieldnames) == ROLLUP_COLUMNS
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["run_finished"] == "2026-07-27 11:19"
    assert rows[0]["question_id"] == "v1-Q1"
    assert rows[0]["total"] == "7"
    assert rows[0]["deterministic_pass"] == "True"
    assert rows[0]["notes"] == "described one program only"


def test_rollup_is_sorted_and_regeneration_is_idempotent(tmp_path):
    runs = tmp_path / "runs"
    for rid, when in (("2026-08-12_1704_quick_v5", datetime(2026, 8, 12, 17, 4)),
                      ("2026-07-27_1119_quick_v1", datetime(2026, 7, 27, 11, 19))):
        write_run(runs, _meta(run_id=rid, finished_at=when), {"v1-Q1": "a"}, "t", {},
                  [_row("v1-Q1")])
    out = tmp_path / "scores.csv"
    regenerate_rollup(runs, out)
    first = out.read_text()
    regenerate_rollup(runs, out)
    assert out.read_text() == first

    with out.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert [r["run_finished"] for r in rows] == ["2026-07-27 11:19", "2026-08-12 17:04"]


def test_rollup_carries_scoring_provenance(tmp_path):
    runs = tmp_path / "runs"
    rubric = Rubric(citations=2, correctness=2, gap_honesty=2, scope_discipline=2,
                    clarity=2, scored_by="claude-opus-5", confirmed_by="Michael")
    write_run(runs, _meta(), {"v1-Q1": "a"}, "t", {}, [_row("v1-Q1", rubric=rubric)])
    out = tmp_path / "scores.csv"
    regenerate_rollup(runs, out)
    with out.open(newline="") as fh:
        row = next(csv.DictReader(fh))
    assert row["scored_by"] == "claude-opus-5"
    assert row["confirmed_by"] == "Michael"


def test_provenance_survives_write_then_read(tmp_path):
    rubric = Rubric(citations=1, correctness=1, gap_honesty=1, scope_discipline=1,
                    clarity=1, scored_by="claude-opus-5")
    run_dir = write_run(tmp_path, _meta(), {"v1-Q1": "a"}, "t", {},
                        [_row("v1-Q1", rubric=rubric)])
    _, _, rows = read_run(run_dir)
    assert rows[0].rubric.scored_by == "claude-opus-5"
    assert rows[0].rubric.confirmed_by is None
    assert rows[0].rubric.is_confirmed is False


def test_run_finished_tracks_finished_at_not_run_id(tmp_path):
    runs = tmp_path / "runs"
    meta = _meta(run_id="2026-01-01_0000_quick_v1",
                 finished_at=datetime(2026, 7, 27, 11, 19))
    write_run(runs, meta, {"v1-Q1": "a"}, "t", {}, [_row("v1-Q1")])
    out = tmp_path / "scores.csv"
    regenerate_rollup(runs, out)
    with out.open(newline="") as fh:
        row = next(csv.DictReader(fh))
    assert row["run_finished"] == "2026-07-27 11:19"


def test_complete_run_with_no_finished_at_writes_empty_cell(tmp_path):
    runs = tmp_path / "runs"
    meta = _meta(status=RunStatus.COMPLETE, finished_at=None)
    run_dir = write_run(runs, meta, {"v1-Q1": "a"}, "t", {}, [_row("v1-Q1")])
    with (run_dir / "scores.csv").open(newline="") as fh:
        row = next(csv.DictReader(fh))
    assert row["run_finished"] == ""


def test_unscored_rubric_writes_empty_cells_not_zeros(tmp_path):
    runs = tmp_path / "runs"
    write_run(runs, _meta(), {"v1-Q1": "a"},
              "t", {}, [_row("v1-Q1", rubric=Rubric())])
    out = tmp_path / "scores.csv"
    regenerate_rollup(runs, out)
    with out.open(newline="") as fh:
        row = next(csv.DictReader(fh))
    assert row["citations"] == "" and row["total"] == ""


def test_cli_rollup_writes_the_rollup_file(tmp_path):
    runs = tmp_path / "runs"
    write_run(runs, _meta(), {"v1-Q1": "a"}, "t", {}, [_row("v1-Q1")])
    out = tmp_path / "scores.csv"

    exit_code = main(["rollup", "--runs", str(runs), "--out", str(out)])

    assert exit_code == 0
    with out.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 1
    assert rows[0]["question_id"] == "v1-Q1"


def test_cli_rollup_check_passes_when_up_to_date(tmp_path, capsys):
    runs = tmp_path / "runs"
    write_run(runs, _meta(), {"v1-Q1": "a"}, "t", {}, [_row("v1-Q1")])
    out = tmp_path / "scores.csv"
    regenerate_rollup(runs, out)
    before = out.read_text()

    exit_code = main(["rollup", "--runs", str(runs), "--out", str(out), "--check"])

    assert exit_code == 0
    assert "up to date" in capsys.readouterr().out
    assert out.read_text() == before, "--check must not rewrite the file"


def test_cli_rollup_check_fails_and_reports_the_diff_when_stale(tmp_path, capsys):
    runs = tmp_path / "runs"
    write_run(runs, _meta(), {"v1-Q1": "a"}, "t", {}, [_row("v1-Q1")])
    out = tmp_path / "scores.csv"
    regenerate_rollup(runs, out)
    stale = out.read_text()

    # A second, later run lands after the committed rollup was generated.
    write_run(runs, _meta(run_id="2026-08-01_0900_quick_v1",
                          finished_at=datetime(2026, 8, 1, 9, 0)),
              {"v1-Q1": "b"}, "t", {}, [_row("v1-Q1")])

    exit_code = main(["rollup", "--runs", str(runs), "--out", str(out), "--check"])

    assert exit_code == 1
    out_text = capsys.readouterr().out
    assert "out of date" in out_text
    assert "2026-08-01" in out_text, "the diff must show what changed"
    assert out.read_text() == stale, "--check must not rewrite the committed file"
