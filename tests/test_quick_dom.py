import ast
from pathlib import Path

import pytest

from atlas_eval.adapters import quick_dom as qd

FIXTURE = Path("tests/fixtures/quick/sanitized_conversation_complete.html")
THIS_FILE = Path(__file__)


@pytest.fixture(scope="module")
def page():
    """The committed fixture, loaded the ONLY way that works.

    java_script_enabled=False is mandatory: the real page is a React SPA and its
    own scripts wipe the captured markup on re-mount, after which every selector
    returns empty and the tests pass for the wrong reason.
    """
    pw = pytest.importorskip("playwright.sync_api")
    with pw.sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(java_script_enabled=False)
        pg = ctx.new_page()
        pg.goto("file://" + str(FIXTURE.resolve()))
        yield pg
        browser.close()


def test_page_fixture_disables_javascript():
    """Guard against silently dropping java_script_enabled=False.

    Why not a direct before/after divergence test on the fixture: the
    committed sanitized fixture has had every <script> tag stripped (confirmed:
    it contains zero <script> elements), so loading it with JavaScript enabled
    produces byte-identical extraction results to loading it disabled in this
    headless file:// context -- there is nothing left to re-mount and wipe the
    markup. That wipe is real (it happened during recon against the live,
    unsanitized capture, which does carry scripts), but it cannot be
    reproduced against the fixture actually committed to this repo without
    fabricating a passing test around behavior this suite cannot observe.

    So this test pins the actual code instead of the symptom: it parses this
    test file's AST, finds the `page` fixture, and fails if its
    browser.new_context(...) call ever stops passing
    java_script_enabled=False. If you are reading this because it just failed:
    you (or a refactor) removed that flag. Put it back. Without it, the real
    (unsanitized) capture's own React scripts re-mount and wipe the DOM you
    just loaded, every quick_dom selector then finds nothing, and every other
    test in this file passes for the wrong reason -- silently, since an empty
    result and a "correct" one look the same to a naive assertion.
    """
    tree = ast.parse(THIS_FILE.read_text())
    page_fn = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "page"
    )
    new_context_calls = [
        node
        for node in ast.walk(page_fn)
        if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "new_context"
    ]
    assert new_context_calls, "page fixture no longer calls browser.new_context(...) at all"

    for call in new_context_calls:
        for kw in call.keywords:
            if kw.arg == "java_script_enabled":
                assert isinstance(kw.value, ast.Constant) and kw.value.value is False, (
                    "page fixture's new_context() passes java_script_enabled="
                    f"{ast.dump(kw.value)!r}, not False -- the real capture is a "
                    "React SPA whose own scripts re-mount and wipe the captured "
                    "markup once JS is allowed to run, which turns every "
                    "quick_dom selector into a silent empty result"
                )
                return

    pytest.fail(
        "page fixture's new_context() no longer passes java_script_enabled=False "
        "at all -- the real capture is a React SPA whose own scripts re-mount "
        "and wipe the captured markup once JS is allowed to run, which turns "
        "every quick_dom selector into a silent empty result and every test in "
        "this file into a false positive"
    )


def test_fixture_exists_and_is_sanitized():
    text = FIXTURE.read_text()
    assert "arn:aws" not in text
    assert "dol.nj.gov" not in text
    assert "SANITIZED" in text


def test_completed_answer_count_matches_the_footers(page):
    # One footer renders per COMPLETED answer. The fixture holds two.
    assert qd.completed_answer_count(page) == 2


def test_conversation_id_is_read_from_the_thread_container(page):
    assert qd.conversation_id(page) == "00000000-0000-4000-8000-000000000000"


def test_model_chip(page):
    assert qd.model_chip(page) == "Advanced"


def test_agent_name_from_the_status_announcement(page):
    assert qd.agent_from_status(page) == "Engineering Onboarding Specialist"


def test_answer_and_question_texts_pair_up(page):
    answers, questions = qd.answer_texts(page), qd.question_texts(page)
    assert len(answers) == len(questions) == 2
    assert "L204DF2" in questions[0]


def test_answer_text_is_whole_not_truncated(page):
    answer = qd.answer_texts(page)[0]
    assert len(answer) > 4000, "the real answer is ~4.8k chars"
    # Terms that live inside markdown tables must survive extraction, because
    # the deterministic scorer matches against exactly this string.
    for term in ("BNKFLMOD", "BNKFLDTE", "BANKMTCH", "CHECKS.ISSUED", "ACC2528"):
        assert term.lower() in answer.lower(), term


def test_citation_labels(page):
    labels = qd.citation_labels(page)
    assert labels and all(l.startswith("Citation") for l in labels)


def test_auth_redirect_detection():
    assert qd.is_auth_redirect(
        "https://us-east-1.quicksight.aws.amazon.com/sn/account/njuimod/start/home"
        "?redirect_uri=https%3A%2F%2F...%26isauthcode%3Dtrue"
    )
    assert qd.is_auth_redirect("https://x/start/home?redirect_uri=y")
    assert not qd.is_auth_redirect(
        "https://us-east-1.quicksight.aws.amazon.com/sn/account/njuimod/start/agents"
    )


def test_selectors_avoid_the_ruled_out_mechanisms():
    # aria-busy was absent at every capture point; base-ui ids churned 16/55
    # within a single session. Either would produce silent, intermittent failure.
    # Scoped to the SEL_* constants themselves (the actual selectors used at
    # runtime), not the whole module source -- a whole-file scan also trips on
    # comments/docstrings that merely explain the exclusion, like this one.
    selectors = {k: v for k, v in vars(qd).items() if k.startswith("SEL_")}
    assert selectors, "expected at least one SEL_* constant in quick_dom"
    for name, value in selectors.items():
        assert "aria-busy" not in value, f"{name} = {value!r} uses the ruled-out aria-busy attribute"
        assert "base-ui" not in value, f"{name} = {value!r} uses the ruled-out base-ui id shape"


def test_module_never_imports_the_scorer():
    src = open(qd.__file__).read()
    assert "scoring" not in src
