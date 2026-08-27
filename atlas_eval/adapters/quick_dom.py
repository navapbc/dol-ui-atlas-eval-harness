"""Reading the Quick chat DOM.

Quick is Amazon Q Business components (`qbiz-*`) embedded in QuickSuite. Every
selector below was verified against the live agent on 2026-08-27 and is recorded
in docs/recon/2026-08-27-quick-chat-dom.md.

Two mechanisms are deliberately NOT used, both documented in that recon note
(this docstring avoids spelling them out literally, since a source-scan test
in tests/test_quick_dom.py asserts they never appear in this module):
  * the ARIA attribute for a busy/loading state — absent at every capture
    point, so it can never fire.
  * React-generated ids from the underlying headless component library, in
    the `<vendor-prefix>-:rNN:` shape — 16 of 55 button ids changed within a
    single session, which would fail intermittently and look like a Quick bug
    rather than a harness bug.

Completion is detected positively: one message footer renders per COMPLETED
answer, so the transport waits for that count to reach the number of questions
asked. Waiting for a control to disappear cannot distinguish "finished" from
"never started".
"""

from __future__ import annotations

SEL_INPUT = '[data-testid="qbiz-components-prompt-textarea"]'
SEL_THREAD = '[data-testid="chat-panel-conversation-thread-container"]'
SEL_USER_TURN = '[data-testid="user-chat-message-container"]'
SEL_AI_TURN = '[data-testid="ai-chat-message-container"]'
SEL_AI_FOOTER = '[data-testid="qbiz-component-ai-message-footer"]'
SEL_CITATION = '[data-testid="citation-reference"]'
SEL_MODEL_CHIP = '[data-testid="qbiz-model-selection-chip"]'
SEL_AGENT_SELECTOR = '[data-testid="qbiz-component-chat-experience-agent-selector-wrapper"]'
SEL_STATUS = 'div[role="status"]'

# The run state is not URL-addressable: the landing and run-ready URLs were
# byte-identical, and both are the auth redirect. So these markers mean "we are
# looking at a login hop, not the chat".
AUTH_URL_MARKERS: tuple[str, ...] = ("/start/home?redirect_uri=", "isauthcode=true")

_STATUS_PREFIX = "New message from "


def is_auth_redirect(url: str) -> bool:
    return any(marker in url for marker in AUTH_URL_MARKERS)


def completed_answer_count(page) -> int:
    """How many answers have finished rendering. The completion signal."""
    return page.locator(SEL_AI_FOOTER).count()


def conversation_id(page) -> str | None:
    thread = page.locator(SEL_THREAD).first
    if thread.count() == 0:
        return None
    return thread.get_attribute("data-conversation-id")


def _first_text(page, selector: str) -> str | None:
    loc = page.locator(selector).first
    if loc.count() == 0:
        return None
    return loc.inner_text().strip() or None


def model_chip(page) -> str | None:
    """Which model backs the agent. Worth recording in the run snapshot."""
    return _first_text(page, SEL_MODEL_CHIP)


def agent_from_status(page) -> str | None:
    """Agent name from the completion announcement.

    Needed because the agent id is absent from the DOM, so this is the only
    in-page confirmation that the intended agent answered.
    """
    for text in page.locator(SEL_STATUS).all_inner_texts():
        stripped = text.strip()
        if stripped.startswith(_STATUS_PREFIX):
            return stripped[len(_STATUS_PREFIX):].strip() or None
    return None


def answer_texts(page) -> list[str]:
    """Full answer text per agent turn, in order.

    innerText keeps markdown tables and code blocks readable, which matters
    because scorer check terms live inside them.
    """
    return [t.strip() for t in page.locator(SEL_AI_TURN).all_inner_texts()]


def question_texts(page) -> list[str]:
    return [t.strip() for t in page.locator(SEL_USER_TURN).all_inner_texts()]


def citation_labels(scope) -> list[str]:
    """Citation labels found within `scope`.

    `scope` is whatever the caller passes: the whole `page` (every citation
    on it) or, critically, one specific turn's own locator -- e.g.
    `page.locator(SEL_AI_TURN).nth(i)` -- so that answer N's citations are
    only ever the citations rendered inside answer N's own turn, never
    turns 1..N-1's as well. Callers reading one answer's citations must pass
    a turn-scoped locator, not the page.
    """
    labels = []
    citations = scope.locator(SEL_CITATION)
    for i in range(citations.count()):
        label = citations.nth(i).get_attribute("aria-label")
        if label:
            labels.append(label.strip())
    return labels
