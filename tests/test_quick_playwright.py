from datetime import datetime

import pytest

from atlas_eval.adapters import quick_dom as qd
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
    """Minimal stand-in for a Playwright Locator.

    `nth()` returning `self` unconditionally (the pre-fix shape) makes every
    element indistinguishable from every other: a test can assert that
    SOMETHING was read, but never that the RIGHT element was read, which is
    exactly why the citation-bleed bug (every answer got every citation on
    the whole page) went uncaught. Turns (SEL_AI_TURN) and citations
    (SEL_CITATION) are the two selectors this suite needs to tell apart by
    index, so `nth()` on those tracks a real index instead of collapsing
    back to the same object; `.locator()` lets a turn-scoped locator narrow
    further to just that turn's own citations, mirroring how the real
    Playwright API scopes a query to inside another locator's element.
    """

    def __init__(self, page, selector, turn_index=None, citation_index=None):
        self._page = page
        self._sel = selector
        self._turn_index = turn_index
        self._citation_index = citation_index

    @property
    def first(self):
        return self

    def count(self):
        if self._sel == qd.SEL_CITATION and self._turn_index is not None:
            return len(self._page.citations_by_turn.get(self._turn_index, []))
        return self._page.counts.get(self._sel, 0)

    def fill(self, text):
        self._page.filled.append((self._sel, text))

    def press(self, key):
        self._page.pressed.append((self._sel, key))
        self._page.on_submit()

    def get_attribute(self, name):
        if (self._sel == qd.SEL_CITATION and self._turn_index is not None
                and self._citation_index is not None):
            labels = self._page.citations_by_turn.get(self._turn_index, [])
            return labels[self._citation_index] if self._citation_index < len(labels) else None
        return self._page.attrs.get((self._sel, name))

    def inner_text(self):
        return self._page.texts.get(self._sel, "")

    def all_inner_texts(self):
        return self._page.lists.get(self._sel, [])

    def nth(self, i):
        if self._sel == qd.SEL_AI_TURN:
            return FakeLocator(self._page, self._sel, turn_index=i)
        if self._sel == qd.SEL_CITATION and self._turn_index is not None:
            return FakeLocator(self._page, self._sel, turn_index=self._turn_index,
                               citation_index=i)
        return self

    def locator(self, selector):
        # Scoped to inside a specific turn: return citations for that turn
        # only, never the whole page's.
        if self._sel == qd.SEL_AI_TURN and self._turn_index is not None:
            return FakeLocator(self._page, selector, turn_index=self._turn_index)
        return self._page.locator(selector)


class FakePage:
    """Minimal stand-in exposing the slice of the Playwright API used here."""

    def __init__(self, url="https://q/sn/account/njuimod/start/agents"):
        self.url = url
        self.counts, self.attrs, self.texts, self.lists = {}, {}, {}, {}
        self.filled, self.pressed = [], []
        self.citations_by_turn: dict[int, list[str]] = {}
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


def _wired_page_with_baseline(baseline: int):
    """A page that starts a run with `baseline` prior answers already on the
    thread, then completes one NEW answer per submitted question.

    Models a resumed conversation over a persistent profile: the footer count
    and turn list are non-zero before the first question in this run is ever
    asked.
    """
    from atlas_eval.adapters import quick_dom as qd
    page = FakePage()
    page.counts[qd.SEL_INPUT] = 1
    page.counts[qd.SEL_AI_FOOTER] = baseline
    page.counts[qd.SEL_THREAD] = 1
    page.attrs[(qd.SEL_THREAD, "data-conversation-id")] = "conv-1"
    prior = [f"prior answer {k}" for k in range(1, baseline + 1)]
    page.lists[qd.SEL_AI_TURN] = list(prior)
    page.lists[qd.SEL_STATUS] = ["New message from Engineering Onboarding Specialist"]
    page.lists[qd.SEL_USER_TURN] = []

    def on_submit():
        total_footers = page.counts[qd.SEL_AI_FOOTER] + 1
        page.counts[qd.SEL_AI_FOOTER] = total_footers
        new_count = total_footers - baseline
        page.lists[qd.SEL_AI_TURN] = prior + [f"new answer {k}" for k in range(1, new_count + 1)]
    page.on_submit = on_submit
    return page


def _wired_page_with_unequal_baselines(footers: int, turns: int):
    """Baselines captured while the page is mid-stream: a prior answer's turn
    has already rendered but its footer has not (or vice versa), so the two
    baseline counts genuinely differ at the moment ask() would capture them.

    Exists so a regression that swaps which baseline feeds the wait versus
    which feeds the indexing is detectable: with the earlier fixtures
    (baseline_footers == baseline_turns always), such a swap is invisible --
    the two numbers are interchangeable when equal.
    """
    page = FakePage()
    page.counts[qd.SEL_INPUT] = 1
    page.counts[qd.SEL_AI_FOOTER] = footers
    page.counts[qd.SEL_THREAD] = 1
    page.attrs[(qd.SEL_THREAD, "data-conversation-id")] = "conv-1"
    page.lists[qd.SEL_AI_TURN] = [f"prior answer {k}" for k in range(1, turns + 1)]
    page.lists[qd.SEL_STATUS] = ["New message from Engineering Onboarding Specialist"]
    page.lists[qd.SEL_USER_TURN] = []
    return page


def test_ask_refuses_to_baseline_against_a_not_yet_settled_page(monkeypatch):
    """A mid-stream prior answer renders its turn before its footer (or the
    reverse); baselining against that moment would reintroduce the shifted
    pairing the baselining commit exists to prevent, so ask() must refuse
    rather than baseline against unsettled counts.
    """
    import atlas_eval.adapters.quick_playwright as qp
    monkeypatch.setattr(qp.time, "sleep", lambda _ms: None)  # never actually wait

    page = _wired_page_with_unequal_baselines(footers=1, turns=2)
    backend = QuickPlaywrightBackend(agent="engineering_onboarding_specialist",
                                     url="https://q", snapshot_data={}, page=page)
    result = backend.ask([_q("v3-Q1")])

    assert result.complete is False
    assert result.responses == []
    failure = (result.failure or "").lower()
    assert "settl" in failure or "baseline" in failure, (
        f"expected a settledness/baseline failure, got: {result.failure!r}"
    )


def test_ask_returns_new_answers_not_stale_ones_when_the_thread_has_prior_turns(monkeypatch):
    """The Critical: a resumed thread with prior answers must not satisfy the
    wait instantly and must not pair questions with pre-existing answers.

    `on_submit` is a no-op here (the answer is not ready the instant Enter is
    pressed), so the only way `ask()` can finish is by actually polling
    (calling `sleep`) until the baselined footer count is reached. If the
    unfixed code ran, `wait_for_answer` would already see the 2 prior footers
    as satisfying `expected_count=1`/`2` and return without ever sleeping, and
    the responses would come back as the prior answers rather than the new
    ones.
    """
    import atlas_eval.adapters.quick_playwright as qp
    from atlas_eval.adapters import quick_dom as qd

    page = _wired_page_with_baseline(baseline=2)
    page.on_submit = lambda: None  # nothing completes until a poll tick

    sleep_calls = []

    def fake_sleep(ms):
        sleep_calls.append(ms)
        total_footers = page.counts[qd.SEL_AI_FOOTER] + 1
        page.counts[qd.SEL_AI_FOOTER] = total_footers
        new_count = total_footers - 2
        page.lists[qd.SEL_AI_TURN] = (
            ["prior answer 1", "prior answer 2"]
            + [f"new answer {k}" for k in range(1, new_count + 1)]
        )

    monkeypatch.setattr(qp.time, "sleep", fake_sleep)

    # Agent matches the wired page's status banner ("Engineering Onboarding
    # Specialist"); this test is about baselining, not agent matching.
    backend = qp.QuickPlaywrightBackend(agent="engineering_onboarding_specialist",
                                        url="https://q", snapshot_data={}, page=page)
    result = backend.ask([_q("v3-Q1"), _q("v3-Q2", after="v3-Q1")])

    assert result.complete is True, result.failure
    assert len(sleep_calls) >= 2, (
        "ask() must actually wait for each new answer rather than being "
        "satisfied instantly by pre-existing footers"
    )
    assert [r.answer for r in result.responses] == ["new answer 1", "new answer 2"], (
        "must return the NEW answers, never the 2 prior ones already on the thread"
    )


def test_ask_with_a_single_prior_answer_returns_the_new_one():
    page = _wired_page_with_baseline(baseline=1)
    backend = QuickPlaywrightBackend(agent="engineering_onboarding_specialist",
                                     url="https://q", snapshot_data={}, page=page)
    result = backend.ask([_q("v3-Q1")])
    assert result.complete is True, result.failure
    assert result.responses[0].answer == "new answer 1"


def test_ask_aborts_when_turns_and_footers_fall_out_of_lockstep():
    from atlas_eval.adapters import quick_dom as qd
    page = _wired_page(2)
    original = page.on_submit

    def spurious():
        original()
        # An extra turn renders (e.g. an error bubble or a stray quick-starter
        # chip) without a matching footer.
        page.lists[qd.SEL_AI_TURN] = page.lists[qd.SEL_AI_TURN] + ["stray turn"]
    page.on_submit = spurious

    backend = QuickPlaywrightBackend(agent="a", url="https://q", snapshot_data={}, page=page)
    result = backend.ask([_q("v3-Q1")])

    assert result.complete is False
    assert "PARSE_FAILED" in result.failure
    assert "2 new agent turns" in result.failure
    assert "1 new completed-answer footers" in result.failure


def test_ask_scopes_citations_to_each_answers_own_turn_not_the_whole_page():
    """Reproduces the finding: citation_labels(page) read every citation on
    the whole page, so answer 2 inherited answer 1's citation(s) too.
    Each turn here carries a DISTINCT, disjoint set of citation labels, so a
    regression that reads page-wide (or that reads the wrong turn) is caught
    -- a bug that merely duplicated shared labels across turns would not be.
    """
    page = _wired_page(2)
    page.citations_by_turn = {0: ["Citation A1"], 1: ["Citation B1", "Citation B2"]}

    backend = QuickPlaywrightBackend(agent="engineering_onboarding_specialist",
                                     url="https://q", snapshot_data={}, page=page)
    result = backend.ask([_q("v3-Q1"), _q("v3-Q2", after="v3-Q1")])

    assert result.complete is True, result.failure
    assert result.responses[0].citations == ["Citation A1"]
    assert result.responses[1].citations == ["Citation B1", "Citation B2"]


def test_ask_catches_a_native_playwright_exception_and_keeps_partial_answers():
    """Reproduces the finding: ask() only caught TransportError, so a
    Playwright-native exception (a real TimeoutError from fill()'s
    auto-wait, routinely raised while a prior answer is still streaming)
    propagated out of ask() and out of run_bank, losing the whole run --
    including every answer already collected -- to a traceback instead of a
    written, diagnosable incomplete run.
    """
    page = _wired_page(2)
    original = page.on_submit
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] == 2:
            raise TimeoutError("Timeout 30000ms exceeded waiting for locator "
                               "to be visible and enabled")
        original()
    page.on_submit = flaky

    backend = QuickPlaywrightBackend(agent="engineering_onboarding_specialist",
                                     url="https://q", snapshot_data={}, page=page)
    result = backend.ask([_q("v3-Q1"), _q("v3-Q2", after="v3-Q1")])

    assert result.complete is False
    assert result.failure is not None and "Timeout" in result.failure
    assert [r.question_id for r in result.responses] == ["v3-Q1"], (
        "the answer already collected before the exception must survive in "
        "the partial result, not be discarded along with the traceback"
    )


def test_ask_does_not_swallow_keyboard_interrupt_or_system_exit():
    for exc_type in (KeyboardInterrupt, SystemExit):
        page = _wired_page(1)

        def boom():
            raise exc_type()
        page.on_submit = boom

        backend = QuickPlaywrightBackend(agent="a", url="https://q", snapshot_data={}, page=page)
        with pytest.raises(exc_type):
            backend.ask([_q("v3-Q1")])


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

    backend = QuickPlaywrightBackend(agent="engineering_onboarding_specialist",
                                     url="https://q", snapshot_data={}, page=page)
    result = backend.ask([_q("v3-Q1"), _q("v3-Q2")])
    assert result.complete is False
    assert "AUTH_REQUIRED" in result.failure
    assert [r.question_id for r in result.responses] == ["v3-Q1"]


def test_ask_aborts_if_the_conversation_changes_after_the_first_question():
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


def test_ask_does_not_abort_when_the_banner_names_the_expected_agent_as_a_display_name():
    """Bank slug vs. UI display name: engineering_onboarding_specialist should
    match "Engineering Onboarding Specialist" without tripping the check."""
    page = _wired_page(2)  # SEL_STATUS already carries the display-name banner
    backend = QuickPlaywrightBackend(agent="engineering_onboarding_specialist",
                                     url="https://q", snapshot_data={}, page=page)
    result = backend.ask([_q("v3-Q1"), _q("v3-Q2", after="v3-Q1")])
    assert result.complete is True, result.failure
    assert len(result.responses) == 2


def test_ask_aborts_after_the_first_question_when_the_banner_names_a_different_agent():
    from atlas_eval.adapters import quick_dom as qd
    page = _wired_page(2)
    page.lists[qd.SEL_STATUS] = ["New message from Some Other Agent"]

    backend = QuickPlaywrightBackend(agent="engineering_onboarding_specialist",
                                     url="https://q", snapshot_data={}, page=page)
    result = backend.ask([_q("v3-Q1"), _q("v3-Q2", after="v3-Q1")])

    assert result.complete is False
    assert "AGENT_MISMATCH" in result.failure
    assert "engineering_onboarding_specialist" in result.failure
    assert "Some Other Agent" in result.failure
    # aborted after Q1, not before it: the first (real) answer is retained.
    assert [r.question_id for r in result.responses] == ["v3-Q1"]
    assert result.responses[0].answer == "answer 1"


def test_ask_does_not_abort_when_no_completion_banner_is_present(recwarn):
    from atlas_eval.adapters import quick_dom as qd
    page = _wired_page(2)
    page.lists[qd.SEL_STATUS] = []  # no banner rendered at all

    backend = QuickPlaywrightBackend(agent="engineering_onboarding_specialist",
                                     url="https://q", snapshot_data={}, page=page)
    result = backend.ask([_q("v3-Q1"), _q("v3-Q2", after="v3-Q1")])

    assert result.complete is True, result.failure
    assert len(result.responses) == 2
    assert any("banner" in str(w.message).lower() for w in recwarn.list), (
        "a missing banner must not fail closed, but its absence must be "
        "surfaced (e.g. via a warning), not silent"
    )


def test_ask_skips_the_agent_check_when_no_agent_is_expected():
    from atlas_eval.adapters import quick_dom as qd
    page = _wired_page(2)
    page.lists[qd.SEL_STATUS] = ["New message from Some Other Agent"]

    # Mirrors the CLI passing `args.agent_name or ""` when nothing was given.
    backend = QuickPlaywrightBackend(agent="", url="https://q", snapshot_data={}, page=page)
    result = backend.ask([_q("v3-Q1"), _q("v3-Q2", after="v3-Q1")])

    assert result.complete is True, result.failure
    assert len(result.responses) == 2


def test_snapshot_includes_the_model_chip_read_from_the_page_after_asking():
    """Reproduces the finding: transcript.py reads snapshot["model_chip"], but
    snapshot.capture() never emits it and neither backend ever called
    qd.model_chip(page) to put it there -- so the recon note's "worth
    capturing" field was dead outside of tests. The Playwright backend has a
    page, so it is the one that should read the chip.
    """
    page = _wired_page(2)
    page.counts[qd.SEL_MODEL_CHIP] = 1
    page.texts[qd.SEL_MODEL_CHIP] = "Advanced"

    backend = QuickPlaywrightBackend(agent="engineering_onboarding_specialist",
                                     url="https://q",
                                     snapshot_data={"agent": {"AgentId": "x"}}, page=page)
    result = backend.ask([_q("v3-Q1"), _q("v3-Q2", after="v3-Q1")])
    assert result.complete is True, result.failure

    snap = backend.snapshot()
    assert snap["model_chip"] == "Advanced"
    assert snap["agent"]["AgentId"] == "x", "the AWS-sourced snapshot data must survive"


def test_snapshot_omits_the_model_chip_key_when_the_page_never_shows_one():
    page = _wired_page(2)  # no SEL_MODEL_CHIP registered at all
    backend = QuickPlaywrightBackend(agent="engineering_onboarding_specialist",
                                     url="https://q", snapshot_data={}, page=page)
    backend.ask([_q("v3-Q1"), _q("v3-Q2", after="v3-Q1")])
    assert "model_chip" not in backend.snapshot()


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
