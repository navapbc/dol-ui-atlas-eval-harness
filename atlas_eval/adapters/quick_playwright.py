"""The Playwright transport: drive the Quick chat UI deterministically.

Chosen over an LLM agent clicking through the UI because an agent makes unlogged
judgement calls every run (which element, whether streaming finished, whether to
retry) and those calls move scores without appearing in the record. A script
makes the same calls every time, and breaks loudly when the UI changes.

Selectors and the completion signal come from docs/recon/2026-08-27-quick-chat-dom.md,
verified against the live agent. Completion is positive: one message footer per
COMPLETED answer, so we wait for that count to reach the number asked.

Authentication is never automated. The operator signs in once into a persistent
profile; this module only detects that it has been bounced to a login page and
aborts the run.
"""

from __future__ import annotations

import time
import warnings
from datetime import datetime
from pathlib import Path

from atlas_eval.adapters import quick_dom as qd
from atlas_eval.adapters.base import AskResult, Response, TransportError
from atlas_eval.models import Question

DEFAULT_PROFILE_DIR = Path(".auth/quick-profile")

# The captured real answer was ~4.8k characters over several paragraphs, tables
# and code blocks. Five minutes is generous rather than tight, because a false
# timeout discards a whole run.
ANSWER_TIMEOUT_MS = 300_000
POLL_INTERVAL_MS = 1_000


def _guard_auth(page) -> None:
    if qd.is_auth_redirect(page.url):
        raise TransportError(
            "AUTH_REQUIRED",
            f"bounced to a login page ({page.url[:120]}); sign in to the persistent "
            "profile and re-run. This transport never fills in or submits a login form.",
        )


def wait_for_answer(
    page,
    expected_count: int,
    timeout_ms: int = ANSWER_TIMEOUT_MS,
    poll_ms: int = POLL_INTERVAL_MS,
    sleep=None,
) -> None:
    """Block until `expected_count` completed-answer footers exist on the page.

    The footer element renders once per completed answer, which is a positive
    signal: it cannot confuse "finished" with "never started", which is exactly
    what waiting for a stop control to vanish would do.

    `expected_count` is a raw footer count, not a "how many have I asked"
    count. Callers resuming a thread with prior turns already on the page
    must add their own baseline footer count before calling this, or the
    wait is satisfied instantly by footers that predate this run. See
    `QuickPlaywrightBackend.ask` for that baselining.
    """
    rest = sleep if sleep is not None else (lambda ms: time.sleep(ms / 1000))
    waited = 0
    while True:
        _guard_auth(page)
        if qd.completed_answer_count(page) >= expected_count:
            return
        if waited >= timeout_ms:
            raise TransportError(
                "TIMEOUT",
                f"only {qd.completed_answer_count(page)} of {expected_count} answers "
                f"completed within {timeout_ms // 1000}s",
            )
        rest(poll_ms)
        waited += poll_ms


def _normalize_agent_name(name: str) -> str:
    """Fold a bank slug and a UI display name onto the same shape.

    The bank's `agent` field is a slug (`engineering_onboarding_specialist`);
    the completion banner shows a display name (`Engineering Onboarding
    Specialist`). Case, and underscore-vs-space, are the only differences
    between those two forms for a legitimate match, so both are collapsed
    away before comparing.
    """
    return " ".join(name.replace("_", " ").split()).lower()


def submit_question(page, text: str) -> None:
    _guard_auth(page)
    box = page.locator(qd.SEL_INPUT)
    if box.count() == 0:
        raise TransportError(
            "SELECTOR_MISSING",
            f"message input {qd.SEL_INPUT} not found; the Quick UI may have changed. "
            "Recapture fixtures with tools/recon_quick_dom.py, or use the paste transport.",
        )
    box.fill(text)
    box.press("Enter")


class QuickPlaywrightBackend:
    """Ask a whole bank in one Quick conversation."""

    name = "quick"
    transport = "playwright"

    def __init__(
        self,
        agent: str,
        url: str,
        snapshot_data: dict,
        profile_dir: Path = DEFAULT_PROFILE_DIR,
        page=None,
    ) -> None:
        self.agent = agent
        self.url = url
        self.profile_dir = profile_dir
        self._snapshot = snapshot_data
        self._page = page  # injected in tests; a live page in real runs

    def snapshot(self) -> dict:
        return self._snapshot

    def _check_agent(self, page) -> None:
        """Confirm the completion banner named the agent under test.

        Called once, right after the first answer completes: the banner only
        renders once a message has been answered, and checking here aborts
        before the rest of the bank is wasted on a run that can never be
        scored correctly. Quick opens with a default agent already active,
        has no per-agent URL, and never puts the agent id in the DOM, so this
        banner text is the only in-page confirmation of which agent answered.
        """
        if not self.agent:
            return  # no expected agent to check against (args.agent_name or "")
        observed = qd.agent_from_status(page)
        if observed is None:
            # The banner is a UI affordance, not guaranteed on every page. Its
            # absence must not fail the run closed, but it must not be silent
            # either: a warning surfaces in test output and in any run of the
            # CLI (Python prints warnings to stderr by default), without
            # touching AskResult / the run record.
            warnings.warn(
                "no completion banner found on the page; could not confirm "
                f"that {self.agent!r} was the agent that answered. Proceeding "
                "without agent-identity confirmation for this run.",
                stacklevel=2,
            )
            return
        if _normalize_agent_name(observed) != _normalize_agent_name(self.agent):
            raise TransportError(
                "AGENT_MISMATCH",
                f"expected agent {self.agent!r} to answer but the completion "
                f"banner named {observed!r}; the run may have executed "
                "against the wrong agent and must not be scored",
            )

    def ask(self, questions: list[Question]) -> AskResult:
        page = self._page
        if page is None:
            raise TransportError(
                "SELECTOR_MISSING",
                "no page supplied; open a persistent context and pass page=",
            )

        responses: list[Response] = []
        conversation = qd.conversation_id(page)

        # The persistent profile means the landing URL can open on a thread
        # that already holds prior turns (the recon note records the default
        # agent already active). If we asked for raw footer/turn counts, the
        # very first wait would be satisfied instantly by pre-existing footers,
        # and we'd pair the new question with someone else's old answer while
        # still reporting complete=True. So every count below is taken
        # relative to a baseline captured here, before the first question is
        # asked. Do not "simplify" this back to raw indices.
        baseline_footers = qd.completed_answer_count(page)
        baseline_turns = len(qd.answer_texts(page))

        try:
            _guard_auth(page)
            for index, question in enumerate(questions, 1):
                submit_question(page, question.text)
                wait_for_answer(page, expected_count=baseline_footers + index)

                current = qd.conversation_id(page)
                if conversation is None:
                    conversation = current
                elif current != conversation:
                    raise TransportError(
                        "CONVERSATION_LOST",
                        f"conversation changed from {conversation} to {current} before "
                        f"{question.id}; `after` dependencies are void once the thread "
                        "changes, so the run cannot continue",
                    )

                answers = qd.answer_texts(page)
                new_turns = len(answers) - baseline_turns
                new_footers = qd.completed_answer_count(page) - baseline_footers
                if new_turns < index:
                    raise TransportError(
                        "PARSE_FAILED",
                        f"{index} new answers completed but only {new_turns} new agent "
                        f"turns are readable for {question.id}",
                    )
                if new_turns != new_footers:
                    raise TransportError(
                        "PARSE_FAILED",
                        f"turn/footer mismatch for {question.id}: {new_turns} new agent "
                        f"turns but {new_footers} new completed-answer footers since the "
                        "baseline; the two DOM queries have fallen out of lockstep "
                        "(a stray turn or footer, such as an error bubble or a quick-"
                        "starter chip, would shift every later pairing without this check)",
                    )
                responses.append(Response(
                    question_id=question.id,
                    answer=answers[baseline_turns + index - 1],
                    asked_at=datetime.now(),
                    citations=qd.citation_labels(page),
                ))

                if index == 1:
                    # Only the first answer triggers the banner check: it
                    # cannot be checked any earlier (no banner exists until an
                    # answer has completed), and checking here aborts before
                    # the remaining questions in the bank are wasted on a run
                    # against the wrong agent. The first answer is already
                    # appended above, so an abort here still keeps it in the
                    # partial result.
                    self._check_agent(page)
        except TransportError as err:
            return AskResult(
                responses=responses, conversation_id=conversation,
                complete=False, failure=str(err),
            )

        return AskResult(responses=responses, conversation_id=conversation, complete=True)
