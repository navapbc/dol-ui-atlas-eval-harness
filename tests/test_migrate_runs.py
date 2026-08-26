import csv
from pathlib import Path

import pytest

from atlas_eval.migrate.runs import (
    SHARED_TRANSCRIPT_STAMPS, group_legacy_scores, legacy_row_to_score_row,
    migrate_runs, stamp_from_run_finished,
)
from atlas_eval.runs import ROLLUP_COLUMNS, RunStatus, read_run, regenerate_rollup

AGENT = "Engineering Onboarding Specialist"
AGENT_ID = "093ac4e3-0712-481e-af95-9ddc5e4fc734"
CONV = "e33bea76-a1f6-4c78-8c1d-9d735e3dfb82"

LEGACY_HEADER = (
    "run_finished,agent,agent_id,bank_version,question_id,type,citations,correctness,"
    "gap_honesty,scope_discipline,clarity,total,conversation_id,notes\n"
)


def _legacy_csv(tmp_path, *rows):
    p = tmp_path / "scores.csv"
    p.write_text(LEGACY_HEADER + "".join(rows))
    return p


def _row(finished="2026-07-27 11:19", qid="v1-Q1", version="v1", notes=""):
    return (f"{finished},{AGENT},{AGENT_ID},{version},{qid},retrieval,"
            f"2,1,1,1,2,7,{CONV},{notes}\n")


def _source(tmp_path, *rows):
    src = tmp_path / "src"
    (src / "chats").mkdir(parents=True)
    (src / "snapshots").mkdir(parents=True)
    _legacy_csv(src, *rows)
    stem = "2026-07-27_1119_engineering_onboarding_specialist"
    (src / "chats" / f"{stem}.md").write_text("# chat\n\nQ1 ... A1 ...\n")
    (src / "snapshots" / f"{stem}.json").write_text('{"AgentId": "093ac4e3"}')
    (src / "snapshots" / "2026-07-27_1119_spaces.json").write_text('{"Spaces": []}')
    return src


def test_stamp_conversion():
    assert stamp_from_run_finished("2026-07-27 11:19") == "2026-07-27_1119"
    assert stamp_from_run_finished("2026-08-12 17:04") == "2026-08-12_1704"


def test_stamp_rejects_unexpected_format():
    with pytest.raises(ValueError):
        stamp_from_run_finished("27/07/2026 11:19")


def test_grouping_splits_by_timestamp_and_bank():
    rows = [
        {"run_finished": "2026-07-27 11:19", "bank_version": "v1", "question_id": "v1-Q1"},
        {"run_finished": "2026-07-27 11:19", "bank_version": "v1", "question_id": "v1-Q2"},
        {"run_finished": "2026-08-12 17:04", "bank_version": "v5", "question_id": "v5-Q1"},
    ]
    groups = group_legacy_scores(rows)
    assert sorted(groups) == [("2026-07-27 11:19", "v1"), ("2026-08-12 17:04", "v5")]
    assert len(groups[("2026-07-27 11:19", "v1")]) == 2


def test_legacy_row_stamps_provenance_without_guessing_a_reviewer():
    rec = dict(zip(LEGACY_HEADER.strip().split(","), _row().strip().split(",")))
    row = legacy_row_to_score_row(rec)
    assert row.rubric.scored_by == "legacy-audit"
    assert row.rubric.confirmed_by is None, "must not assert an unrecorded reviewer"

    stamped = legacy_row_to_score_row(rec, "legacy-audit", "Michael Angeli")
    assert stamped.rubric.confirmed_by == "Michael Angeli"


def test_legacy_row_becomes_a_score_row_with_rubric_intact():
    rec = dict(zip(LEGACY_HEADER.strip().split(","),
                   _row(notes="described one program only").strip().split(",")))
    row = legacy_row_to_score_row(rec)
    assert row.question_id == "v1-Q1"
    assert row.rubric.citations == 2 and row.rubric.correctness == 1
    assert row.rubric.total == 7
    assert row.rubric.notes == "described one program only"
    assert row.deterministic is None, "legacy rows were never deterministically scored"
    assert row.verification_status == "unverified"


def test_blank_rubric_cell_becomes_none_not_zero():
    rec = dict(zip(LEGACY_HEADER.strip().split(","),
                   f"2026-07-27 11:19,{AGENT},{AGENT_ID},v1,v1-Q1,retrieval,"
                   f",,,,,,{CONV},".split(",")))
    row = legacy_row_to_score_row(rec)
    assert row.rubric.citations is None and row.rubric.total is None


def test_migrate_creates_one_run_dir_per_group(tmp_path):
    src = _source(tmp_path, _row(qid="v1-Q1"), _row(qid="v1-Q2"))
    runs = tmp_path / "runs"
    ids = migrate_runs(src, runs)
    assert ids == ["2026-07-27_1119_quick_v1"]

    meta, responses, rows = read_run(runs / ids[0])
    assert meta.backend == "quick" and meta.transport == "legacy"
    assert meta.status is RunStatus.COMPLETE
    assert meta.agent_id == AGENT_ID and meta.conversation_id == CONV
    assert meta.bank_version == "v1"
    assert [r.question_id for r in rows] == ["v1-Q1", "v1-Q2"]
    assert responses == {}, "legacy transcripts were not split per question"


def test_transcript_and_snapshot_are_carried_across(tmp_path):
    src = _source(tmp_path, _row())
    runs = tmp_path / "runs"
    run_dir = runs / migrate_runs(src, runs)[0]
    assert "# chat" in (run_dir / "transcript.md").read_text()
    snap = (run_dir / "snapshot.json").read_text()
    assert "AgentId" in snap and "Spaces" in snap, "agent and spaces are merged"


def test_missing_transcript_is_recorded_not_fatal(tmp_path):
    src = _source(tmp_path, _row(finished="2026-08-99 09:00"))
    # A row whose timestamp has no chat file at all.
    src_rows = (src / "scores.csv").read_text()
    (src / "scores.csv").write_text(src_rows.replace("2026-08-99 09:00", "2026-08-01 09:00"))
    runs = tmp_path / "runs"
    ids = migrate_runs(src, runs)
    run_dir = runs / [i for i in ids if i.startswith("2026-08-01")][0]
    assert (run_dir / "transcript.md").read_text().startswith("<!-- no transcript")


def test_no_score_rows_are_lost(tmp_path):
    src = _source(tmp_path, _row(qid="v1-Q1"), _row(qid="v1-Q2"),
                  _row(finished="2026-08-12 17:04", qid="v5-Q1", version="v5"))
    runs = tmp_path / "runs"
    migrate_runs(src, runs)
    out = tmp_path / "scores.csv"
    regenerate_rollup(runs, out)
    with out.open(newline="") as fh:
        reader = csv.DictReader(fh)
        assert tuple(reader.fieldnames) == ROLLUP_COLUMNS
        assert len(list(reader)) == 3


def test_source_is_never_modified(tmp_path):
    src = _source(tmp_path, _row())
    before = {p: p.read_bytes() for p in src.rglob("*") if p.is_file()}
    migrate_runs(src, tmp_path / "runs")
    after = {p: p.read_bytes() for p in src.rglob("*") if p.is_file()}
    assert before == after


def test_shared_transcript_stamp_covers_two_scored_runs(tmp_path):
    """2026-08-12: one transcript (stamped 1527) documents both the 1511/v1
    and 1523/v2 runs (per its own header: "Runs: v1 full (conv 1f352d59,
    3:02-3:11), v2 full (conv 7e143e0e, 3:13-3:23), ..."). The score rows for
    those two stamps carry conversation_id "1f352d59-regression" and
    "7e143e0e-regression" and have no transcript of their own; SHARED_TRANSCRIPT_STAMPS
    is the explicit, hand-verified mapping that attaches the 1527 material to
    both runs rather than leaving them without a transcript.
    """
    assert SHARED_TRANSCRIPT_STAMPS["2026-08-12_1511"] == "2026-08-12_1527"
    assert SHARED_TRANSCRIPT_STAMPS["2026-08-12_1523"] == "2026-08-12_1527"

    src = tmp_path / "src"
    (src / "chats").mkdir(parents=True)
    (src / "snapshots").mkdir(parents=True)
    header = LEGACY_HEADER
    row_v1 = (f"2026-08-12 15:11,{AGENT},{AGENT_ID},v1,v1-Q1,retrieval,"
              f"2,1,1,1,2,7,1f352d59-regression,\n")
    row_v2 = (f"2026-08-12 15:23,{AGENT},{AGENT_ID},v2,v2-Q1,retrieval,"
              f"2,1,1,1,2,7,7e143e0e-regression,\n")
    (src / "scores.csv").write_text(header + row_v1 + row_v2)

    stem = "2026-08-12_1527_engineering_onboarding_specialist"
    transcript_text = (
        "# chat\n\nRuns: v1 full (conv 1f352d59, 3:02-3:11), "
        "v2 full (conv 7e143e0e, 3:13-3:23), v5-Q4 spot, v3-Q1 spot\n"
    )
    (src / "chats" / f"{stem}.md").write_text(transcript_text)
    (src / "snapshots" / f"{stem}.json").write_text('{"AgentId": "093ac4e3"}')
    (src / "snapshots" / "2026-08-12_1527_spaces.json").write_text('{"Spaces": []}')

    runs = tmp_path / "runs"
    ids = migrate_runs(src, runs)
    assert "2026-08-12_1511_quick_v1" in ids
    assert "2026-08-12_1523_quick_v2" in ids

    for run_id in ("2026-08-12_1511_quick_v1", "2026-08-12_1523_quick_v2"):
        run_dir = runs / run_id
        transcript = (run_dir / "transcript.md").read_text()
        assert "v1 full (conv 1f352d59" in transcript, "shared transcript must be attached"
        snap = (run_dir / "snapshot.json").read_text()
        assert "AgentId" in snap and "Spaces" in snap

        # read_run must still parse the record: the borrowed-stamp note is a
        # comment, not a RunMeta field (RunMeta forbids extra fields).
        meta, _, _ = read_run(run_dir)
        assert meta.status is RunStatus.COMPLETE

        run_yaml_text = (run_dir / "run.yaml").read_text()
        assert "2026-08-12_1527" in run_yaml_text, (
            "run.yaml must record which stamp the shared transcript came from"
        )
