from datetime import datetime

import pytest

from atlas_eval.adapters.base import TransportError
from atlas_eval.adapters.quick_playwright import (
    QuickPlaywrightBackend, submit_question, wait_for_answer,
)
from atlas_eval.models import Question, QuestionType, Stance
from tests.adapter_conformance import assert_backend_conformance


def _q(qid, text="question text", after=None):
    return Question(id=qid, text=text, type=QuestionType.RETRIEVAL,
                    expected_stance=Stance.ANSWER, ground_truth="gt", after=after)


class FakeLocator:
    def __init__(self, page, selector):
        self._page, self._sel = page, selector

    @property
    def first(self):
        return self

    def count(self):
        return self._page.counts.get(self._sel, 0)

    def fill(self, text):
        self._page.filled.append((self._sel, text))

    def press(self, key):
        self._page.pressed.append((self._sel, key))
        self._page.on_submit()

    def get_attribute(self, name):
        return self._page.attrs.get((self._sel, name))

    def inner_text(self):
        return self._page.texts.get(self._sel, "")

    def all_inner_texts(self):
        return self._page.lists.get(self._sel, [])

    def nth(self, i):
        return self


class FakePage:
    """Minimal stand-in exposing the slice of the Playwright API used here."""

    def __init__(self, url="https://q/sn/account/njuimod/start/agents"):
        self.url = url
        self.counts, self.attrs, self.texts, self.lists = {}, {}, {}, {}
        self.filled, self.pressed = [], []
        self.on_submit = lambda: None

    def locator(self, selector):
        return FakeLocator(self, selector)


def test_wait_for_answer_returns_once_the_footer_count_is_reached():
    from atlas_eval.adapters import quick_dom as qd
    page = FakePage()
    page.counts[qd.SEL_AI_FOOTER] = 0
    ticks = []

    def sleep(_ms):
        ticks.append(1)
        page.counts[qd.SEL_AI_FOOTER] = len(ticks)  # one answer completes per tick

    wait_for_answer(page, expected_count=2, sleep=sleep)
    assert page.counts[qd.SEL_AI_FOOTER] == 2


def test_wait_for_answer_times_out_with_a_transport_error():
    from atlas_eval.adapters import quick_dom as qd
    page = FakePage()
    page.counts[qd.SEL_AI_FOOTER] = 0
    with pytest.raises(TransportError) as exc:
        wait_for_answer(page, expected_count=1, timeout_ms=3_000, poll_ms=1_000,
                        sleep=lambda _ms: None)
    assert exc.value.code == "TIMEOUT"
    assert "1" in exc.value.detail


def test_wait_for_answer_aborts_on_an_auth_redirect_mid_wait():
    from atlas_eval.adapters import quick_dom as qd
    page = FakePage()
    page.counts[qd.SEL_AI_FOOTER] = 0

    def sleep(_ms):
        page.url = "https://q/sn/account/njuimod/start/home?redirect_uri=x&isauthcode=true"

    with pytest.raises(TransportError) as exc:
        wait_for_answer(page, expected_count=1, sleep=sleep)
    assert exc.value.code == "AUTH_REQUIRED"


def test_submit_question_fills_the_input_and_presses_enter():
    from atlas_eval.adapters import quick_dom as qd
    page = FakePage()
    page.counts[qd.SEL_INPUT] = 1
    submit_question(page, "what does DXCBD87E do?")
    assert page.filled == [(qd.SEL_INPUT, "what does DXCBD87E do?")]
    assert page.pressed == [(qd.SEL_INPUT, "Enter")]


def test_submit_question_raises_when_the_input_is_absent():
    page = FakePage()  # no input registered
    with pytest.raises(TransportError) as exc:
        submit_question(page, "anything")
    assert exc.value.code == "SELECTOR_MISSING"


def _wired_page(n_questions):
    """A page that completes one answer per submitted question."""
    from atlas_eval.adapters import quick_dom as qd
    page = FakePage()
    page.counts[qd.SEL_INPUT] = 1
    page.counts[qd.SEL_AI_FOOTER] = 0
    page.counts[qd.SEL_THREAD] = 1
    page.attrs[(qd.SEL_THREAD, "data-conversation-id")] = "conv-1"
    page.lists[qd.SEL_AI_TURN] = []
    page.lists[qd.SEL_STATUS] = ["New message from Engineering Onboarding Specialist"]
    page.lists[qd.SEL_USER_TURN] = []

    def on_submit():
        i = page.counts[qd.SEL_AI_FOOTER] + 1
        page.counts[qd.SEL_AI_FOOTER] = i
        page.lists[qd.SEL_AI_TURN] = [f"answer {k}" for k in range(1, i + 1)]
    page.on_submit = on_submit
    return page


def test_ask_walks_the_bank_in_order_and_pairs_answers():
    page = _wired_page(2)
    backend = QuickPlaywrightBackend(agent="engineering_onboarding_specialist",
                                     url="https://q", snapshot_data={}, page=page)
    result = backend.ask([_q("v3-Q1"), _q("v3-Q2", after="v3-Q1")])
    assert result.complete is True
    assert [r.question_id for r in result.responses] == ["v3-Q1", "v3-Q2"]
    assert result.responses[0].answer == "answer 1"
    assert result.responses[1].answer == "answer 2"
    assert result.conversation_id == "conv-1"


def test_ask_marks_incomplete_on_a_transport_error_and_keeps_prior_answers():
    from atlas_eval.adapters import quick_dom as qd
    page = _wired_page(2)
    calls = {"n": 0}
    original = page.on_submit

    def flaky():
        calls["n"] += 1
        if calls["n"] == 2:
            page.url = "https://q/start/home?redirect_uri=x"
            return
        original()
    page.on_submit = flaky

    backend = QuickPlaywrightBackend(agent="a", url="https://q", snapshot_data={}, page=page)
    result = backend.ask([_q("v3-Q1"), _q("v3-Q2")])
    assert result.complete is False
    assert "AUTH_REQUIRED" in result.failure
    assert [r.question_id for r in result.responses] == ["v3-Q1"]


def test_ask_aborts_if_the_conversation_changes_midway():
    from atlas_eval.adapters import quick_dom as qd
    page = _wired_page(2)
    original = page.on_submit
    state = {"n": 0}

    def switching():
        state["n"] += 1
        original()
        if state["n"] == 1:
            page.attrs[(qd.SEL_THREAD, "data-conversation-id")] = "conv-2"
    page.on_submit = switching

    backend = QuickPlaywrightBackend(agent="a", url="https://q", snapshot_data={}, page=page)
    result = backend.ask([_q("v3-Q1"), _q("v3-Q2", after="v3-Q1")])
    assert result.complete is False
    assert "CONVERSATION_LOST" in result.failure


def test_ask_refuses_before_asking_when_already_on_an_auth_redirect():
    page = _wired_page(1)
    page.url = "https://q/sn/account/njuimod/start/home?redirect_uri=x&isauthcode=true"
    backend = QuickPlaywrightBackend(agent="a", url="https://q", snapshot_data={}, page=page)
    result = backend.ask([_q("v3-Q1")])
    assert result.complete is False
    assert "AUTH_REQUIRED" in result.failure
    assert result.responses == []
    assert page.filled == [], "must not type into a login page"


def test_backend_conforms_to_the_backend_protocol():
    page = _wired_page(2)
    backend = QuickPlaywrightBackend(agent="engineering_onboarding_specialist",
                                     url="https://q", snapshot_data={}, page=page)
    assert_backend_conformance(backend, [_q("v3-Q1"), _q("v3-Q2", after="v3-Q1")])


def test_backend_identity_and_no_scoring_import():
    backend = QuickPlaywrightBackend(agent="a", url="https://q", snapshot_data={"k": 1},
                                     page=FakePage())
    assert (backend.name, backend.transport) == ("quick", "playwright")
    assert backend.snapshot() == {"k": 1}
    import atlas_eval.adapters.quick_playwright as mod
    src = open(mod.__file__).read()
    assert "scoring" not in src
    # Never handle credentials.
    for banned in ("password", "fill_password", "credential"):
        assert banned not in src.lower(), banned
