from datetime import datetime
from pathlib import Path

import pytest

from atlas_eval.adapters.base import AskResult, Response
from atlas_eval.dataset import compute_question_sha256, load_bank
from atlas_eval.orchestrate import OrchestrationError, run_bank
from atlas_eval.runs import read_run

BANK = """version: v3
agent: engineering_onboarding_specialist
corpus: quick_space_ca7_daily_s3
questions:
  - id: v3-Q1
    text: Describe the Accelerated Collection Process.
    type: retrieval
    expected_stance: answer
    ground_truth: ACP is the Accelerated Collection Process.
    checks:
      required_all: [ACP]
      forbidden: [ETA-227]
      expect_citations: [UIMB0730]
  - id: v3-Q2
    after: v3-Q1
    text: What does ACP stand for?
    type: acronym_check
    expected_stance: answer
    ground_truth: Accelerated Collection Process.
    checks:
      required_any: ["Accelerated Collection Process"]
"""


def _bank_file(tmp_path, frozen=False):
    path = tmp_path / "v3.yaml"
    path.write_text(BANK)
    if frozen:
        bank = load_bank(path)
        path.write_text(
            BANK.replace("version: v3",
                         f"version: v3\nfrozen_on: 2026-08-03\n"
                         f"question_sha256: {compute_question_sha256(bank)}")
        )
    return path


class StubBackend:
    name, transport = "quick", "stub"

    def __init__(self, answers, complete=True, failure=None, conversation="conv-1"):
        self._answers, self._complete = answers, complete
        self._failure, self._conversation = failure, conversation
        self.asked: list[str] = []

    def snapshot(self):
        return {"model_chip": "Advanced"}

    def ask(self, questions):
        self.asked = [q.id for q in questions]
        return AskResult(
            responses=[Response(question_id=q.id, answer=self._answers[q.id],
                                asked_at=datetime(2026, 8, 27, 9, 0))
                       for q in questions if q.id in self._answers],
            conversation_id=self._conversation,
            complete=self._complete, failure=self._failure,
        )


GOOD = {"v3-Q1": "The ACP is documented in UIMB0730.",
        "v3-Q2": "It stands for Accelerated Collection Process."}


def test_happy_path_writes_a_complete_run(tmp_path):
    backend = StubBackend(GOOD)
    run_dir = run_bank(_bank_file(tmp_path), backend, tmp_path / "runs",
                       now=datetime(2026, 8, 27, 9, 30))
    meta, responses, rows = read_run(run_dir)
    assert meta.status.value == "complete"
    assert meta.bank_version == "v3"
    assert meta.transport == "stub"
    assert meta.conversation_id == "conv-1"
    assert list(responses) == ["v3-Q1", "v3-Q2"]
    assert len(rows) == 2
    for name in ("run.yaml", "responses.yaml", "transcript.md", "snapshot.json", "scores.csv"):
        assert (run_dir / name).exists(), name


def test_questions_are_asked_in_resolved_run_order(tmp_path):
    backend = StubBackend(GOOD)
    run_bank(_bank_file(tmp_path), backend, tmp_path / "runs",
             now=datetime(2026, 8, 27, 9, 30))
    assert backend.asked == ["v3-Q1", "v3-Q2"]


def test_deterministic_scores_are_computed_and_recorded(tmp_path):
    run_dir = run_bank(_bank_file(tmp_path), StubBackend(GOOD), tmp_path / "runs",
                       now=datetime(2026, 8, 27, 9, 30))
    text = (run_dir / "scores.csv").read_text()
    assert "deterministic_pass" in text
    assert "True" in text


def test_a_wrong_answer_records_a_failing_deterministic_result(tmp_path):
    bad = dict(GOOD, **{"v3-Q1": "This is the ETA-227 reporting process."})
    run_dir = run_bank(_bank_file(tmp_path), StubBackend(bad), tmp_path / "runs",
                       now=datetime(2026, 8, 27, 9, 30))
    import csv
    rows = {r["question_id"]: r for r in csv.DictReader((run_dir / "scores.csv").open())}
    assert rows["v3-Q1"]["deterministic_pass"] == "False"
    assert "ETA-227" in rows["v3-Q1"]["present_forbidden"]


def test_rubric_cells_are_left_empty_for_a_human(tmp_path):
    run_dir = run_bank(_bank_file(tmp_path), StubBackend(GOOD), tmp_path / "runs",
                       now=datetime(2026, 8, 27, 9, 30))
    import csv
    for row in csv.DictReader((run_dir / "scores.csv").open()):
        for dim in ("citations", "correctness", "gap_honesty", "scope_discipline", "clarity"):
            assert row[dim] == "", f"{dim} must be blank, not zero"
        assert row["total"] == ""
        assert row["confirmed_by"] == ""
        assert row["scored_by"] == "harness-deterministic"


def test_incomplete_ask_still_writes_a_run_marked_incomplete(tmp_path):
    partial = {"v3-Q1": GOOD["v3-Q1"]}
    run_dir = run_bank(_bank_file(tmp_path),
                       StubBackend(partial, complete=False,
                                   failure="TIMEOUT: only 1 of 2 answers completed"),
                       tmp_path / "runs", now=datetime(2026, 8, 27, 9, 30))
    meta, responses, rows = read_run(run_dir)
    assert meta.status.value == "incomplete"
    assert list(responses) == ["v3-Q1"]
    assert len(rows) == 1
    assert "TIMEOUT" in (run_dir / "transcript.md").read_text()


def test_frozen_bank_with_edited_text_is_refused_before_asking(tmp_path):
    path = _bank_file(tmp_path, frozen=True)
    path.write_text(path.read_text().replace("What does ACP stand for?",
                                             "What does ACP mean?"))
    backend = StubBackend(GOOD)
    with pytest.raises(OrchestrationError) as exc:
        run_bank(path, backend, tmp_path / "runs", now=datetime(2026, 8, 27, 9, 30))
    assert "question_sha256" in str(exc.value)
    assert backend.asked == [], "must not ask anything against a mismatched bank"


def test_frozen_bank_with_matching_hash_runs(tmp_path):
    run_dir = run_bank(_bank_file(tmp_path, frozen=True), StubBackend(GOOD),
                       tmp_path / "runs", now=datetime(2026, 8, 27, 9, 30))
    assert read_run(run_dir)[0].status.value == "complete"


def test_unfrozen_bank_records_the_computed_hash(tmp_path):
    path = _bank_file(tmp_path)
    run_dir = run_bank(path, StubBackend(GOOD), tmp_path / "runs",
                       now=datetime(2026, 8, 27, 9, 30))
    assert read_run(run_dir)[0].question_sha256 == compute_question_sha256(load_bank(path))


def test_orchestrator_never_writes_a_rubric_value(tmp_path):
    import atlas_eval.orchestrate as mod
    src = open(mod.__file__).read()
    for dim in ("citations=", "correctness=", "gap_honesty=", "scope_discipline=", "clarity="):
        assert dim not in src, f"orchestrator must not set {dim}"
