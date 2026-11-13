"""Offline tests for the LOOPS KB adapter.

None of these reach AWS. The served pipeline is replaced with a stub so the
adapter's own contract -- ordering, citation splitting, error classification
and the store-isolation guard -- is tested without a credential or a charge.
"""

from __future__ import annotations

from datetime import datetime
import pytest

from atlas_eval.adapters.base import AskResult, TransportError
from atlas_eval.adapters.loops_kb import (
    LoopsKbBackend,
    _classify,
    load_served_module,
    split_answer_and_citations,
)
from atlas_eval.models import Question, Stance
from tests.adapter_conformance import assert_backend_conformance


def _question(qid: str, text: str = "how does the gate work?") -> Question:
    return Question(
        id=qid,
        text=text,
        type="retrieval",
        expected_stance=Stance.ANSWER,
        ground_truth="unverified placeholder",
    )


class _StubBackend(LoopsKbBackend):
    """A backend whose served module and tool call are both stubbed."""

    def __init__(self, answers: dict[str, str] | None = None, raises: Exception | None = None):
        super().__init__(eval_db="/tmp/never-written.sqlite3")
        self._answers = answers or {}
        self._raises = raises
        self.asked: list[str] = []

    def _ensure_loaded(self):
        self._module = object()
        self._ask = self._fake_ask
        return self._module

    def _fake_ask(self, question: str, num_results: int) -> str:
        self.asked.append(question)
        if self._raises is not None:
            raise self._raises
        return self._answers.get(question, "stub answer\n\nSources:\n[1] s3://b/p/FAKE.md")

    def snapshot(self) -> dict:
        return {"backend": self.name, "stub": True}


class TestCitationSplitting:
    def test_separates_answer_from_source_footer(self):
        raw = "The gate is in DXCBD50A.\n\nSources:\n[1] s3://b/p/DXCBD50A.md\n[2] s3://b/p/DXNHCM04.md"
        answer, citations = split_answer_and_citations(raw)
        assert answer == "The gate is in DXCBD50A."
        assert citations == ["DXCBD50A.md", "DXNHCM04.md"]

    def test_answer_without_footer_is_returned_whole(self):
        answer, citations = split_answer_and_citations("no sources at all")
        assert answer == "no sources at all"
        assert citations == []

    def test_the_no_sources_sentinel_is_an_ordinary_answer(self):
        # An empty retrieval is behaviour worth scoring, especially on a gap
        # probe. It must not be mistaken for a transport failure.
        answer, citations = split_answer_and_citations(
            "No relevant sources found in the knowledge base."
        )
        assert answer == "No relevant sources found in the knowledge base."
        assert citations == []

    def test_a_footer_shaped_line_inside_the_answer_does_not_split_early(self):
        # rfind, not find: an answer that quotes the word Sources keeps its
        # real footer as the delimiter.
        raw = "See Sources:\nnot a footer\n\nSources:\n[1] s3://b/p/REAL.md"
        answer, citations = split_answer_and_citations(raw)
        assert "not a footer" in answer
        assert citations == ["REAL.md"]

    def test_malformed_footer_lines_are_skipped_not_fatal(self):
        raw = "answer\n\nSources:\n[1] s3://b/p/A.md\ngarbage line\n[2]\n[3] s3://b/p/B.md"
        _, citations = split_answer_and_citations(raw)
        assert citations == ["A.md", "B.md"]


class TestErrorClassification:
    @pytest.mark.parametrize(
        "message",
        [
            "ExpiredToken: the security token included in the request is expired",
            "Token has expired and refresh failed",
            "Unable to locate credentials",
            "NoCredentialsError",
        ],
    )
    def test_credential_failures_are_auth_required(self, message):
        code, _ = _classify(RuntimeError(message))
        assert code == "AUTH_REQUIRED"

    def test_timeouts_are_timeout(self):
        code, _ = _classify(RuntimeError("Read timeout on endpoint URL"))
        assert code == "TIMEOUT"

    def test_anything_else_falls_back_to_parse_failed(self):
        code, _ = _classify(ValueError("chunk fusion produced nothing sensible"))
        assert code == "PARSE_FAILED"

    def test_the_code_is_one_the_transport_error_accepts(self):
        for error in (RuntimeError("ExpiredToken"), RuntimeError("timed out"), ValueError("x")):
            code, detail = _classify(error)
            TransportError(code, detail)  # raises ValueError on an unknown code


class TestAsk:
    def test_asks_every_question_in_the_order_given(self):
        backend = _StubBackend()
        questions = [_question("q1", "first"), _question("q2", "second"), _question("q3", "third")]
        result = backend.ask(questions)
        assert backend.asked == ["first", "second", "third"]
        assert [r.question_id for r in result.responses] == ["q1", "q2", "q3"]
        assert result.complete is True
        assert result.failure is None

    def test_reports_no_conversation_id(self):
        # Structural, not a bug: each ask is an independent call. A reviewer
        # comparing an `after` question against a conversational backend needs
        # to see this.
        result = _StubBackend().ask([_question("q1")])
        assert result.conversation_id is None

    def test_a_credential_failure_stops_the_run_instead_of_recording_a_blank(self):
        backend = _StubBackend(raises=RuntimeError("ExpiredToken: token has expired"))
        with pytest.raises(TransportError) as caught:
            backend.ask([_question("q1")])
        assert caught.value.code == "AUTH_REQUIRED"
        assert "q1" in caught.value.detail

    def test_conforms_to_the_backend_contract(self):
        assert_backend_conformance(_StubBackend(), [_question("q1"), _question("q2")])


class TestStoreIsolation:
    def test_a_missing_served_module_is_a_transport_error(self, tmp_path):
        with pytest.raises(TransportError) as caught:
            load_served_module(tmp_path / "nonexistent-repo", tmp_path / "eval.sqlite3")
        assert caught.value.code == "PARSE_FAILED"

    def test_a_module_that_ignores_the_override_is_refused(self, tmp_path):
        # The whole point of the override is keeping benchmark rows out of the
        # runtime history. A module that ignores it must fail loudly rather
        # than quietly write 250 rows into production.
        tools = tmp_path / "tools"
        tools.mkdir()
        (tools / "loops_kb_mcp.py").write_text("DB_PATH = '/somewhere/else.sqlite3'\n")
        with pytest.raises(TransportError) as caught:
            load_served_module(tmp_path, tmp_path / "eval.sqlite3")
        assert caught.value.code == "PARSE_FAILED"
        assert "LOOPS_KB_DB" in caught.value.detail

    def test_the_override_is_not_leaked_into_the_ambient_environment(self, tmp_path, monkeypatch):
        monkeypatch.delenv("LOOPS_KB_DB", raising=False)
        tools = tmp_path / "tools"
        tools.mkdir()
        (tools / "loops_kb_mcp.py").write_text(
            "import os\nDB_PATH = os.environ['LOOPS_KB_DB']\n"
        )
        load_served_module(tmp_path, tmp_path / "eval.sqlite3")
        import os

        assert "LOOPS_KB_DB" not in os.environ


def test_response_timestamps_are_real_datetimes():
    result = _StubBackend().ask([_question("q1")])
    assert isinstance(result.responses[0].asked_at, datetime)
    assert isinstance(result, AskResult)


class TestScoredTextIncludesTheFooter:
    def test_the_answer_retains_the_sources_footer(self):
        # scoring.score_answer substring-matches expect_citations against the
        # answer text, not Response.citations. Stripping the footer scored this
        # transport differently from every stored Quick run.
        backend = _StubBackend(
            answers={"q": "body text\n\nSources:\n[1] s3://b/p/DXCBD50A.md"}
        )
        result = backend.ask([_question("q1", "q")])
        answer = result.responses[0].answer
        assert "Sources:" in answer
        assert "DXCBD50A.md" in answer

    def test_citations_are_still_available_separately(self):
        backend = _StubBackend(
            answers={"q": "body\n\nSources:\n[1] s3://b/p/A.md\n[2] s3://b/p/A.md"}
        )
        result = backend.ask([_question("q1", "q")])
        # A document repeats once per admitted chunk; that is the honest count.
        assert result.responses[0].citations == ["A.md", "A.md"]
