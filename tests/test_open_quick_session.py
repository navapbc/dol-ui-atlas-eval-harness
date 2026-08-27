from tools.open_quick_session import READY_MESSAGE, check_session_ready


class _FakeLocator:
    def __init__(self, present: bool) -> None:
        self._present = present

    def count(self) -> int:
        return 1 if self._present else 0


class _FakePage:
    def __init__(self, url: str, input_present: bool) -> None:
        self.url = url
        self._input_present = input_present

    def locator(self, selector: str) -> _FakeLocator:
        return _FakeLocator(self._input_present)


READY_URL = "https://us-east-1.quicksight.aws.amazon.com/sn/account/njuimod/start/agents"
AUTH_URL = "https://example.com/start/home?redirect_uri=foo&isauthcode=true"


def test_reports_ready_when_signed_in_and_input_present():
    ready, message = check_session_ready(_FakePage(READY_URL, input_present=True))
    assert ready is True
    assert message == READY_MESSAGE


def test_reports_failure_when_page_still_looks_like_auth_redirect():
    ready, message = check_session_ready(_FakePage(AUTH_URL, input_present=False))
    assert ready is False
    assert "login" in message.lower()


def test_reports_failure_when_chat_input_is_missing_even_off_the_auth_url():
    ready, message = check_session_ready(_FakePage(READY_URL, input_present=False))
    assert ready is False
    assert "chat input" in message.lower()
