import csv
from datetime import datetime

from atlas_eval.cli import main
from atlas_eval.models import Checks, Question, QuestionType, Stance
from atlas_eval.runs import ROLLUP_COLUMNS, RunMeta, RunStatus, ScoreRow, write_run
from atlas_eval.rubric_entry import (
    RUBRIC_ENTRY_COLUMNS, export_rubric, import_rubric,
)
from atlas_eval.scoring import Rubric, score_answer


def _meta(**over):
    base = dict(
        run_id="2026-08-27_0900_quick_paste_v3", backend="quick", transport="paste",
        bank_version="v3", question_sha256="a" * 64,
        agent="Engineering Onboarding Specialist",
        agent_id="093ac4e3-0712-481e-af95-9ddc5e4fc734",
        conversation_id="e33bea76-a1f6-4c78-8c1d-9d735e3dfb82",
        started_at=datetime(2026, 8, 27, 9, 0),
        finished_at=datetime(2026, 8, 27, 9, 0),
        harness_git_sha=None, status=RunStatus.COMPLETE,
    )
    base.update(over)
    return RunMeta(**base)


def _row(qid="v3-Q1", answer="ACP does the work", rubric=None, **over):
    q = Question(id=qid, text="t", type=QuestionType.RETRIEVAL,
                 expected_stance=Stance.ANSWER, ground_truth="gt",
                 checks=Checks(required_all=["ACP"]))
    base = dict(
        question_id=qid, type=QuestionType.RETRIEVAL.value, verification_status="unverified",
        rubric=rubric if rubric is not None else Rubric(),
        deterministic=score_answer(q, answer),
    )
    base.update(over)
    return ScoreRow(**base)


def _run_dir(tmp_path, rows=None, meta=None):
    runs = tmp_path / "runs"
    rows = rows if rows is not None else [_row("v3-Q1"), _row("v3-Q2")]
    return write_run(runs, meta or _meta(), {r.question_id: "answer" for r in rows},
                      "# transcript\n", {}, rows)


def _write_entry_csv(path, rows):
    """rows: list of dicts keyed by a subset of RUBRIC_ENTRY_COLUMNS."""
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=RUBRIC_ENTRY_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in RUBRIC_ENTRY_COLUMNS})


# --- export ------------------------------------------------------------

def test_export_writes_one_row_per_question_with_blank_rubric_cells(tmp_path):
    run_dir = _run_dir(tmp_path)
    out = tmp_path / "rubric.csv"
    result = export_rubric(run_dir, out, tmp_path / "banks")
    assert result.exported == 2

    with out.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert tuple(reader.fieldnames) == RUBRIC_ENTRY_COLUMNS
        rows = list(reader)
    assert [r["question_id"] for r in rows] == ["v3-Q1", "v3-Q2"]
    for r in rows:
        for dim in ("citations", "correctness", "gap_honesty", "scope_discipline", "clarity"):
            assert r[dim] == ""
        assert r["notes"] == ""
        assert r["scored_by"] == ""


def test_export_carries_type_verification_status_and_deterministic_pass(tmp_path):
    run_dir = _run_dir(tmp_path, rows=[_row("v3-Q1", answer="totally unrelated answer")])
    out = tmp_path / "rubric.csv"
    export_rubric(run_dir, out, tmp_path / "banks")
    with out.open(newline="", encoding="utf-8") as fh:
        row = next(csv.DictReader(fh))
    assert row["type"] == "retrieval"
    assert row["verification_status"] == "unverified"
    assert row["deterministic_pass"] == "False"


def test_export_never_duplicates_question_text_ground_truth_or_answer(tmp_path):
    run_dir = _run_dir(tmp_path)
    out = tmp_path / "rubric.csv"
    export_rubric(run_dir, out, tmp_path / "banks")
    text = out.read_text(encoding="utf-8")
    assert "ACP does the work" not in text
    assert "gt" not in text.split("\n")[0].split(",") and "ground_truth" not in text


def test_export_reports_transcript_and_bank_paths(tmp_path):
    run_dir = _run_dir(tmp_path)
    out = tmp_path / "rubric.csv"
    result = export_rubric(run_dir, out, tmp_path / "banks")
    assert result.transcript_path == run_dir / "transcript.md"
    assert result.bank_path == tmp_path / "banks" / "v3.yaml"


# --- import: validation --------------------------------------------------

def test_dimension_out_of_range_is_rejected_naming_the_row(tmp_path):
    run_dir = _run_dir(tmp_path)
    csv_path = tmp_path / "entry.csv"
    _write_entry_csv(csv_path, [{
        "question_id": "v3-Q1", "citations": "3", "correctness": "1",
        "gap_honesty": "1", "scope_discipline": "1", "clarity": "1",
        "scored_by": "claude-opus-5",
    }])
    report = import_rubric(csv_path, run_dir)
    assert not report.ok
    assert any("v3-Q1" in e and "citations" in e for e in report.errors)


def test_non_numeric_dimension_is_rejected(tmp_path):
    run_dir = _run_dir(tmp_path)
    csv_path = tmp_path / "entry.csv"
    _write_entry_csv(csv_path, [{
        "question_id": "v3-Q1", "citations": "high", "correctness": "1",
        "gap_honesty": "1", "scope_discipline": "1", "clarity": "1",
        "scored_by": "claude-opus-5",
    }])
    report = import_rubric(csv_path, run_dir)
    assert not report.ok
    assert any("v3-Q1" in e and "high" in e for e in report.errors)


def test_partial_row_is_rejected_naming_the_row(tmp_path):
    run_dir = _run_dir(tmp_path)
    csv_path = tmp_path / "entry.csv"
    _write_entry_csv(csv_path, [{
        "question_id": "v3-Q1", "citations": "2", "correctness": "2",
        "scored_by": "claude-opus-5",
        # gap_honesty, scope_discipline, clarity left blank
    }])
    report = import_rubric(csv_path, run_dir)
    assert not report.ok
    assert any("v3-Q1" in e for e in report.errors)
    before = (run_dir / "scores.csv").read_text()
    # abort must write nothing
    assert (run_dir / "scores.csv").read_text() == before


def test_blank_row_is_skipped_not_zeroed(tmp_path):
    run_dir = _run_dir(tmp_path)
    csv_path = tmp_path / "entry.csv"
    _write_entry_csv(csv_path, [
        {"question_id": "v3-Q1"},
        {"question_id": "v3-Q2"},
    ])
    report = import_rubric(csv_path, run_dir)
    assert report.ok
    assert report.changes == []
    assert report.unchanged == 2
    with (run_dir / "scores.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        assert row["citations"] == "", "blank must stay blank, not become 0"
        assert row["total"] == ""


def test_scored_by_from_csv_column(tmp_path):
    run_dir = _run_dir(tmp_path)
    csv_path = tmp_path / "entry.csv"
    _write_entry_csv(csv_path, [{
        "question_id": "v3-Q1", "citations": "2", "correctness": "2",
        "gap_honesty": "2", "scope_discipline": "2", "clarity": "2",
        "scored_by": "claude-opus-5",
    }])
    report = import_rubric(csv_path, run_dir)
    assert report.ok
    assert report.changes[0].rubric.scored_by == "claude-opus-5"


def test_scored_by_falls_back_to_flag_when_csv_column_blank(tmp_path):
    run_dir = _run_dir(tmp_path)
    csv_path = tmp_path / "entry.csv"
    _write_entry_csv(csv_path, [{
        "question_id": "v3-Q1", "citations": "2", "correctness": "2",
        "gap_honesty": "2", "scope_discipline": "2", "clarity": "2",
    }])
    report = import_rubric(csv_path, run_dir, scored_by="Priya")
    assert report.ok
    assert report.changes[0].rubric.scored_by == "Priya"


def test_missing_scored_by_entirely_is_rejected(tmp_path):
    run_dir = _run_dir(tmp_path)
    csv_path = tmp_path / "entry.csv"
    _write_entry_csv(csv_path, [{
        "question_id": "v3-Q1", "citations": "2", "correctness": "2",
        "gap_honesty": "2", "scope_discipline": "2", "clarity": "2",
    }])
    report = import_rubric(csv_path, run_dir)
    assert not report.ok
    assert any("v3-Q1" in e and "scored_by" in e for e in report.errors)


def test_confirmed_by_never_comes_from_the_csv(tmp_path):
    run_dir = _run_dir(tmp_path)
    csv_path = tmp_path / "entry.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        fieldnames = list(RUBRIC_ENTRY_COLUMNS) + ["confirmed_by"]
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerow({
            "question_id": "v3-Q1", "citations": "2", "correctness": "2",
            "gap_honesty": "2", "scope_discipline": "2", "clarity": "2",
            "scored_by": "claude-opus-5", "confirmed_by": "Sneaky",
            "type": "", "verification_status": "", "deterministic_pass": "", "notes": "",
        })
    report = import_rubric(csv_path, run_dir)
    assert report.ok
    assert report.changes[0].rubric.confirmed_by is None


def test_confirmed_by_is_set_only_from_the_flag(tmp_path):
    run_dir = _run_dir(tmp_path)
    csv_path = tmp_path / "entry.csv"
    _write_entry_csv(csv_path, [{
        "question_id": "v3-Q1", "citations": "2", "correctness": "2",
        "gap_honesty": "2", "scope_discipline": "2", "clarity": "2",
        "scored_by": "claude-opus-5",
    }])
    report = import_rubric(csv_path, run_dir, confirmed_by="Michael")
    assert report.ok
    assert report.changes[0].rubric.confirmed_by == "Michael"


def test_unknown_question_id_aborts_naming_it(tmp_path):
    run_dir = _run_dir(tmp_path)
    csv_path = tmp_path / "entry.csv"
    _write_entry_csv(csv_path, [{
        "question_id": "v3-Q1", "citations": "2", "correctness": "2",
        "gap_honesty": "2", "scope_discipline": "2", "clarity": "2",
        "scored_by": "claude-opus-5",
    }, {
        "question_id": "v9-Q9-nowhere", "citations": "2", "correctness": "2",
        "gap_honesty": "2", "scope_discipline": "2", "clarity": "2",
        "scored_by": "claude-opus-5",
    }])
    report = import_rubric(csv_path, run_dir)
    assert not report.ok
    assert any("v9-Q9-nowhere" in e for e in report.errors)


def test_abort_wholesale_leaves_scores_csv_untouched(tmp_path):
    run_dir = _run_dir(tmp_path)
    before = (run_dir / "scores.csv").read_text()
    csv_path = tmp_path / "entry.csv"
    _write_entry_csv(csv_path, [{
        # good row
        "question_id": "v3-Q1", "citations": "2", "correctness": "2",
        "gap_honesty": "2", "scope_discipline": "2", "clarity": "2",
        "scored_by": "claude-opus-5",
    }, {
        # bad row: out of range
        "question_id": "v3-Q2", "citations": "9", "correctness": "2",
        "gap_honesty": "2", "scope_discipline": "2", "clarity": "2",
        "scored_by": "claude-opus-5",
    }])
    report = import_rubric(csv_path, run_dir)
    assert not report.ok
    assert (run_dir / "scores.csv").read_text() == before


def test_duplicate_id_in_sheet_aborts(tmp_path):
    run_dir = _run_dir(tmp_path)
    csv_path = tmp_path / "entry.csv"
    _write_entry_csv(csv_path, [{
        "question_id": "v3-Q1", "citations": "2", "correctness": "2",
        "gap_honesty": "2", "scope_discipline": "2", "clarity": "2",
        "scored_by": "claude-opus-5",
    }, {
        "question_id": "v3-Q1", "citations": "1", "correctness": "1",
        "gap_honesty": "1", "scope_discipline": "1", "clarity": "1",
        "scored_by": "claude-opus-5",
    }])
    report = import_rubric(csv_path, run_dir)
    assert not report.ok
    assert any("v3-Q1" in e and "duplicate" in e.lower() for e in report.errors)


# --- import: writing ------------------------------------------------------

def test_full_row_writes_scores_and_total_preserving_column_order(tmp_path):
    run_dir = _run_dir(tmp_path)
    csv_path = tmp_path / "entry.csv"
    _write_entry_csv(csv_path, [{
        "question_id": "v3-Q1", "citations": "2", "correctness": "1",
        "gap_honesty": "1", "scope_discipline": "2", "clarity": "2",
        "notes": "solid answer", "scored_by": "claude-opus-5",
    }])
    report = import_rubric(csv_path, run_dir)
    assert report.ok
    assert len(report.changes) == 1
    assert report.changes[0].rubric.total == 8

    with (run_dir / "scores.csv").open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert tuple(reader.fieldnames) == ROLLUP_COLUMNS
        rows = {r["question_id"]: r for r in reader}
    assert rows["v3-Q1"]["citations"] == "2"
    assert rows["v3-Q1"]["total"] == "8"
    assert rows["v3-Q1"]["notes"] == "solid answer"
    assert rows["v3-Q1"]["scored_by"] == "claude-opus-5"
    # untouched row keeps its blank rubric cells
    assert rows["v3-Q2"]["citations"] == ""
    assert rows["v3-Q2"]["total"] == ""


def test_dry_run_reports_but_writes_nothing(tmp_path):
    run_dir = _run_dir(tmp_path)
    before = (run_dir / "scores.csv").read_text()
    csv_path = tmp_path / "entry.csv"
    _write_entry_csv(csv_path, [{
        "question_id": "v3-Q1", "citations": "2", "correctness": "2",
        "gap_honesty": "2", "scope_discipline": "2", "clarity": "2",
        "scored_by": "claude-opus-5",
    }])
    report = import_rubric(csv_path, run_dir, dry_run=True)
    assert report.ok
    assert len(report.changes) == 1
    assert (run_dir / "scores.csv").read_text() == before


def test_clean_round_trip_is_byte_identical(tmp_path):
    run_dir = _run_dir(tmp_path)
    before = (run_dir / "scores.csv").read_text()
    csv_path = tmp_path / "entry.csv"
    export_rubric(run_dir, csv_path, tmp_path / "banks")

    report = import_rubric(csv_path, run_dir)
    assert report.ok
    assert report.changes == []
    assert (run_dir / "scores.csv").read_text() == before


def test_reimport_of_unchanged_scores_is_a_noop(tmp_path):
    run_dir = _run_dir(tmp_path)
    csv_path = tmp_path / "entry.csv"
    _write_entry_csv(csv_path, [{
        "question_id": "v3-Q1", "citations": "2", "correctness": "2",
        "gap_honesty": "2", "scope_discipline": "2", "clarity": "2",
        "scored_by": "claude-opus-5",
    }])
    import_rubric(csv_path, run_dir)
    after_first = (run_dir / "scores.csv").read_text()

    report = import_rubric(csv_path, run_dir)
    assert report.ok
    assert report.changes == []
    assert report.unchanged == 1  # v3-Q1's values match what is already on disk
    assert (run_dir / "scores.csv").read_text() == after_first


# --- CLI wiring ------------------------------------------------------------

def test_cli_rubric_export_writes_file_and_prints_paths(tmp_path, capsys):
    run_dir = _run_dir(tmp_path)
    out = tmp_path / "rubric.csv"
    exit_code = main(["rubric", "export", "--run", str(run_dir), "-o", str(out),
                      "--banks", str(tmp_path / "banks")])
    assert exit_code == 0
    assert out.exists()
    text = capsys.readouterr().out
    assert "transcript.md" in text
    assert "v3.yaml" in text


def test_cli_rubric_import_applies_scores(tmp_path, capsys):
    run_dir = _run_dir(tmp_path)
    csv_path = tmp_path / "entry.csv"
    _write_entry_csv(csv_path, [{
        "question_id": "v3-Q1", "citations": "2", "correctness": "2",
        "gap_honesty": "2", "scope_discipline": "2", "clarity": "2",
    }])
    exit_code = main(["rubric", "import", str(csv_path), "--run", str(run_dir),
                      "--scored-by", "claude-opus-5"])
    assert exit_code == 0
    with (run_dir / "scores.csv").open(newline="", encoding="utf-8") as fh:
        rows = {r["question_id"]: r for r in csv.DictReader(fh)}
    assert rows["v3-Q1"]["total"] == "10"
    assert rows["v3-Q1"]["scored_by"] == "claude-opus-5"
    out_text = capsys.readouterr().out
    assert "rollup" in out_text.lower()


def test_cli_rubric_import_dry_run_writes_nothing(tmp_path, capsys):
    run_dir = _run_dir(tmp_path)
    before = (run_dir / "scores.csv").read_text()
    csv_path = tmp_path / "entry.csv"
    _write_entry_csv(csv_path, [{
        "question_id": "v3-Q1", "citations": "2", "correctness": "2",
        "gap_honesty": "2", "scope_discipline": "2", "clarity": "2",
        "scored_by": "claude-opus-5",
    }])
    exit_code = main(["rubric", "import", str(csv_path), "--run", str(run_dir), "--dry-run"])
    assert exit_code == 0
    assert (run_dir / "scores.csv").read_text() == before


def test_cli_rubric_import_aborts_on_error_and_exits_nonzero(tmp_path, capsys):
    run_dir = _run_dir(tmp_path)
    csv_path = tmp_path / "entry.csv"
    _write_entry_csv(csv_path, [{
        "question_id": "v3-Q1", "citations": "9", "correctness": "2",
        "gap_honesty": "2", "scope_discipline": "2", "clarity": "2",
        "scored_by": "claude-opus-5",
    }])
    exit_code = main(["rubric", "import", str(csv_path), "--run", str(run_dir)])
    assert exit_code == 1
    assert "error" in capsys.readouterr().out.lower()
