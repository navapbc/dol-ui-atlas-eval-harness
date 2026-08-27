from pathlib import Path

import pytest

from atlas_eval.adapters import quick_dom as qd

FIXTURE = Path("tests/fixtures/quick/sanitized_conversation_complete.html")


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
    src = open(qd.__file__).read()
    # aria-busy was absent at every capture point; base-ui ids churned 16/55
    # within a single session. Either would produce silent, intermittent failure.
    assert "aria-busy" not in src
    assert "base-ui" not in src


def test_module_never_imports_the_scorer():
    src = open(qd.__file__).read()
    assert "scoring" not in src
