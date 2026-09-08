"""Offline tests for LLM-as-judge scoring. No Bedrock call is made."""

from __future__ import annotations

import csv

import pytest

from atlas_eval.judge import (
    DIMENSIONS,
    PROMPT_VERSION,
    RUBRIC_ENTRY_COLUMNS,
    BedrockJudge,
    JudgeError,
    build_prompt,
    fill_export_csv,
    format_report,
    judge_run,
    parse_judgment,
)
from atlas_eval.models import Question, Stance

GOOD = ('{"citations": 2, "correctness": 1, "gap_honesty": 2, '
        '"scope_discipline": 2, "clarity": 1, "notes": "missed the gate", '
        '"ground_truth_concern": ""}')


def _question(qid: str = "v7-Q1", **kw) -> Question:
    data = dict(
        id=qid,
        text="how does the certification gate work?",
        type="retrieval",
        expected_stance=Stance.ANSWER,
        ground_truth="DXCBD50A checks 019 then 007.",
    )
    data.update(kw)
    return Question(**data)


class _StubClient:
    """Records prompts and replays canned replies."""

    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.prompts: list[str] = []
        self.systems: list[str] = []

    def converse(self, **kwargs):
        self.prompts.append(kwargs["messages"][0]["content"][0]["text"])
        self.systems.append(kwargs["system"][0]["text"])
        reply = self.replies.pop(0) if self.replies else GOOD
        return {"output": {"message": {"content": [{"text": reply}]}}}


class TestBlinding:
    def test_prompt_never_names_the_system_under_test(self):
        prompt = build_prompt(_question(), "DXCBD50A applies 019 then 007.")
        lowered = prompt.lower()
        for leak in ("loops", "quick", "bedrock", "run_id", "transport", "backend"):
            assert leak not in lowered, f"prompt leaked {leak!r}"

    def test_prompt_carries_the_criteria_the_judge_needs(self):
        question = _question(
            partial_credit="credit naming the sequence",
            checks={"required_all": ["DXCBD50A"], "forbidden": ["DXCD9999"]},
        )
        prompt = build_prompt(question, "an answer")
        assert "how does the certification gate work?" in prompt
        assert "DXCBD50A checks 019 then 007." in prompt
        assert "credit naming the sequence" in prompt
        assert "MUST BE PRESENT" in prompt
        assert "MUST NOT BE PRESENT" in prompt
        assert "an answer" in prompt

    def test_the_key_is_labelled_as_possibly_wrong(self):
        # v7-Q2's key is QUICK's own output and conflates two files. A judge
        # told to trust it would mark a correct answer wrong.
        assert "may itself be wrong" in build_prompt(_question(), "a")


class TestParsing:
    def test_parses_a_clean_object(self):
        judgment = parse_judgment("q1", GOOD, "m@v1")
        assert judgment.rubric.citations == 2
        assert judgment.rubric.correctness == 1
        assert judgment.total == 8
        assert judgment.rubric.scored_by == "m@v1"

    def test_parses_a_fenced_or_prose_wrapped_object(self):
        wrapped = f"Here is my assessment:\n```json\n{GOOD}\n```\nHope that helps."
        assert parse_judgment("q1", wrapped, "m@v1").rubric.citations == 2

    def test_no_json_at_all_is_an_error(self):
        with pytest.raises(JudgeError, match="no JSON object"):
            parse_judgment("q1", "I would rather not score this.", "m@v1")

    def test_a_missing_dimension_is_an_error(self):
        partial = '{"citations": 2, "correctness": 1, "gap_honesty": 2, "clarity": 1}'
        with pytest.raises(JudgeError, match="omitted scope_discipline"):
            parse_judgment("q1", partial, "m@v1")

    @pytest.mark.parametrize("bad", ["3", "-1"])
    def test_out_of_range_is_an_error_not_a_clamp(self, bad):
        # A clamped score is indistinguishable from a real one afterwards.
        raw = GOOD.replace('"citations": 2', f'"citations": {bad}')
        with pytest.raises(JudgeError, match="out of range"):
            parse_judgment("q1", raw, "m@v1")

    @pytest.mark.parametrize("bad", ['"2"', "1.5", "true", "null"])
    def test_non_integer_scores_are_an_error(self, bad):
        raw = GOOD.replace('"citations": 2', f'"citations": {bad}')
        with pytest.raises(JudgeError, match="must be an integer|omitted"):
            parse_judgment("q1", raw, "m@v1")

    def test_a_key_dispute_is_captured_separately_from_notes(self):
        raw = GOOD.replace('"ground_truth_concern": ""',
                           '"ground_truth_concern": "key conflates PAYVSAM and PAYUPD4F"')
        judgment = parse_judgment("q1", raw, "m@v1")
        assert judgment.ground_truth_concern == "key conflates PAYVSAM and PAYUPD4F"
        assert judgment.rubric.notes == "missed the gate"


class TestJudging:
    def test_scored_by_records_model_and_prompt_version(self):
        judge = BedrockJudge("anthropic.claude-opus-5", client=_StubClient([]))
        assert judge.scored_by == f"anthropic.claude-opus-5@{PROMPT_VERSION}"

    def test_retries_a_malformed_reply_then_succeeds(self):
        client = _StubClient(["not json", GOOD])
        judge = BedrockJudge("m", client=client, max_attempts=2)
        assert judge.judge_one(_question(), "answer").total == 8
        assert len(client.prompts) == 2

    def test_gives_up_after_max_attempts(self):
        client = _StubClient(["nope", "still nope"])
        judge = BedrockJudge("m", client=client, max_attempts=2)
        with pytest.raises(JudgeError):
            judge.judge_one(_question(), "answer")

    def test_one_bad_reply_does_not_discard_the_batch(self):
        # Judging fifty questions costs real money; losing all of it to one
        # malformed object is worse than a report naming what is missing.
        client = _StubClient(["bad", "bad", GOOD])
        judge = BedrockJudge("m", client=client, max_attempts=2)
        report = judge_run(judge, [_question("q1"), _question("q2")],
                           {"q1": "a", "q2": "b"})
        assert len(report.judgments) == 1
        assert len(report.skipped) == 1

    def test_strict_aborts_instead(self):
        judge = BedrockJudge("m", client=_StubClient(["bad", "bad"]), max_attempts=2)
        with pytest.raises(JudgeError):
            judge_run(judge, [_question("q1")], {"q1": "a"}, strict=True)

    def test_a_question_with_no_answer_is_skipped_not_scored(self):
        judge = BedrockJudge("m", client=_StubClient([]))
        report = judge_run(judge, [_question("q1")], {})
        assert report.judgments == []
        assert "no answer in run" in report.skipped[0]

    def test_report_states_the_scores_are_machine_drafted(self):
        judge = BedrockJudge("m", client=_StubClient([]))
        report = judge_run(judge, [_question("q1")], {"q1": "a"})
        text = format_report(report, [_question("q1")])
        assert "machine-drafted" in text
        assert "no question's verification status changed" in text


class TestFillingTheExport:
    def _draft(self, tmp_path, ids=("q1", "q2")):
        path = tmp_path / "rubric.csv"
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(RUBRIC_ENTRY_COLUMNS),
                                    lineterminator="\n")
            writer.writeheader()
            for qid in ids:
                row = dict.fromkeys(RUBRIC_ENTRY_COLUMNS, "")
                row["question_id"] = qid
                row["type"] = "retrieval"
                row["verification_status"] = "unverified"
                row["deterministic_pass"] = "True"
                writer.writerow(row)
        return path

    def _report(self, ids=("q1",), concern=""):
        judge = BedrockJudge("m", client=_StubClient([]))
        raw = GOOD
        if concern:
            raw = GOOD.replace('"ground_truth_concern": ""',
                               f'"ground_truth_concern": "{concern}"')
        client = _StubClient([raw] * len(ids))
        judge = BedrockJudge("m", client=client)
        return judge_run(judge, [_question(i) for i in ids],
                         {i: "answer" for i in ids})

    def test_preserves_column_order_exactly(self, tmp_path):
        # rubric_entry.py warns the first fourteen columns are read
        # positionally by an external chart.
        draft = self._draft(tmp_path)
        out = tmp_path / "judged.csv"
        fill_export_csv(draft, out, self._report())
        with out.open(encoding="utf-8", newline="") as fh:
            assert tuple(csv.DictReader(fh).fieldnames) == RUBRIC_ENTRY_COLUMNS

    def test_fills_scored_rows_and_leaves_others_visibly_empty(self, tmp_path):
        draft = self._draft(tmp_path, ids=("q1", "q2"))
        out = tmp_path / "judged.csv"
        assert fill_export_csv(draft, out, self._report(ids=("q1",))) == 1
        with out.open(encoding="utf-8", newline="") as fh:
            rows = {r["question_id"]: r for r in csv.DictReader(fh)}
        assert rows["q1"]["citations"] == "2"
        assert rows["q1"]["scored_by"].endswith(PROMPT_VERSION)
        assert all(rows["q2"][d] == "" for d in DIMENSIONS)
        assert rows["q2"]["scored_by"] == ""

    def test_a_disputed_key_is_findable_in_notes(self, tmp_path):
        draft = self._draft(tmp_path, ids=("q1",))
        out = tmp_path / "judged.csv"
        fill_export_csv(draft, out, self._report(ids=("q1",), concern="conflates two files"))
        with out.open(encoding="utf-8", newline="") as fh:
            row = next(csv.DictReader(fh))
        assert row["notes"].startswith("KEY-DISPUTE: conflates two files")

    def test_never_writes_over_scores_csv(self, tmp_path):
        draft = self._draft(tmp_path)
        with pytest.raises(JudgeError, match="refusing to write judge output"):
            fill_export_csv(draft, tmp_path / "scores.csv", self._report())

    def test_rejects_a_csv_that_is_not_a_rubric_export(self, tmp_path):
        wrong = tmp_path / "wrong.csv"
        wrong.write_text("question_id,score\nq1,5\n", encoding="utf-8")
        with pytest.raises(JudgeError, match="not a rubric export"):
            fill_export_csv(wrong, tmp_path / "out.csv", self._report())

    def test_a_judge_never_writes_a_verification_status(self, tmp_path):
        draft = self._draft(tmp_path, ids=("q1",))
        out = tmp_path / "judged.csv"
        fill_export_csv(draft, out, self._report(ids=("q1",)))
        with out.open(encoding="utf-8", newline="") as fh:
            assert next(csv.DictReader(fh))["verification_status"] == "unverified"
