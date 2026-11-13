"""Tests for the per-question explanation view. It joins, it never scores."""

from __future__ import annotations

import csv

import pytest

from atlas_eval.explain import DIMENSIONS, QuestionView, format_views, load_judged


def _view(**kw) -> QuestionView:
    data = dict(
        id="q1", type="retrieval", expected_stance="answer", verification="unverified",
        text="how does it work?", answer="an answer", deterministic_pass=True,
        citation_recall="1.0",
    )
    data.update(kw)
    return QuestionView(**data)


class TestDisagreement:
    def test_pass_with_a_low_judge_score_is_flagged_as_over_crediting(self):
        v = _view(deterministic_pass=True, judge_scores=dict.fromkeys(DIMENSIONS, 1))
        v.judge_scores["citations"] = 0
        assert "over-crediting" in v.disagreement

    def test_fail_with_a_high_judge_score_is_flagged_as_wrong_evidence(self):
        v = _view(deterministic_pass=False, judge_scores=dict.fromkeys(DIMENSIONS, 2))
        assert "demanding the wrong evidence" in v.disagreement

    def test_agreement_is_not_flagged(self):
        agree_pass = _view(deterministic_pass=True,
                           judge_scores=dict.fromkeys(DIMENSIONS, 2))
        agree_fail = _view(deterministic_pass=False,
                           judge_scores=dict.fromkeys(DIMENSIONS, 0))
        assert agree_pass.disagreement == ""
        assert agree_fail.disagreement == ""

    def test_no_judge_means_no_disagreement_claim(self):
        # Nothing to disagree with. It must not read as agreement either.
        assert _view(judge_scores={}).disagreement == ""

    def test_unknown_deterministic_result_is_not_a_disagreement(self):
        v = _view(deterministic_pass=None, judge_scores=dict.fromkeys(DIMENSIONS, 2))
        assert v.disagreement == ""


class TestFormatting:
    def test_shows_which_required_terms_were_missing(self):
        v = _view(required_all=["DXCBD50A", "019", "007"], missing_required=["019"],
                  deterministic_pass=False)
        text = format_views("run-1", [v])
        assert "`DXCBD50A` ok" in text
        assert "`019` MISS" in text
        assert "`007` ok" in text

    def test_shows_citation_recall_alongside_the_expected_citations(self):
        v = _view(expect_citations=["A", "B"], missing_citations=["B"],
                  citation_recall="0.5", deterministic_pass=False)
        text = format_views("run-1", [v])
        assert "`A` ok" in text and "`B` MISS" in text
        assert "recall 0.5" in text

    def test_only_disagreements_hides_the_agreeing_questions(self):
        agree = _view(id="q1", judge_scores=dict.fromkeys(DIMENSIONS, 2))
        conflict = _view(id="q2", deterministic_pass=False,
                         judge_scores=dict.fromkeys(DIMENSIONS, 2))
        text = format_views("run-1", [agree, conflict], only="disagreements")
        assert "## q2" in text
        assert "## q1" not in text
        assert "showing: disagreements (1 of 2)" in text

    def test_headline_counts_both_measures(self):
        views = [_view(id="q1", judge_scores=dict.fromkeys(DIMENSIONS, 2)),
                 _view(id="q2", deterministic_pass=False,
                       judge_scores=dict.fromkeys(DIMENSIONS, 1))]
        text = format_views("run-1", views)
        assert "deterministic 1/2" in text
        assert "judge 15/20" in text

    def test_says_when_the_judge_has_not_run(self):
        text = format_views("run-1", [_view(judge_scores={})])
        assert "judge not run" in text

    def test_a_missing_answer_is_stated_not_blank(self):
        text = format_views("run-1", [_view(answer="")])
        assert "(no answer recorded)" in text

    def test_the_excerpt_is_truncated_with_a_marker(self):
        text = format_views("run-1", [_view(answer="x" * 900)], excerpt=100)
        assert "…" in text
        assert "x" * 101 not in text


class TestJudgedCsv:
    def test_loads_a_judged_csv_by_question_id(self, tmp_path):
        path = tmp_path / "j.csv"
        with path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["question_id", "citations", "notes"])
            w.writeheader()
            w.writerow({"question_id": "q1", "citations": "2", "notes": "fine"})
        assert load_judged(path)["q1"]["citations"] == "2"
