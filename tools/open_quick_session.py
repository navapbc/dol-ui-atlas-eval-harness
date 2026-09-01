"""Open a headed browser against the persistent profile so you can sign in once.

Authentication is a deliberate human step, kept out of the run path: the harness
never submits credentials. Sign in here, close the window, and later runs reuse
the profile until the session expires.

The window is a blank browser with none of your existing logins, so start from
the AWS access portal (Identity Center), pick the dev account (298632317228),
open Quick, then click into an agent so the chat input is showing before you
press Enter -- the readiness check looks for that input, so stopping on the
agents *picker* page reports "chat input not found" even though the session did
save.

    .venv/bin/python tools/open_quick_session.py \\
      --url "https://njoitaws.awsapps.com/start/#/?tab=accounts"

The --url is only where login STARTS; only the page you end on is checked. The
Quick agents landing page, for reference, is:
    https://us-east-1.quicksight.aws.amazon.com/sn/account/njuimod/start/agents
"""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

from atlas_eval.adapters import quick_dom as qd

READY_MESSAGE = "Session stored. Runs can now use --transport playwright."


def check_session_ready(page) -> tuple[bool, str]:
    """Whether the page a human just signed in on looks usable for a run.

    Takes a page-like object (anything with `.url` and `.locator(selector)`)
    so this can be exercised without a browser. Only inspects the page the
    human already navigated by hand: it never types credentials and never
    automates a login form.
    """
    if qd.is_auth_redirect(page.url):
        return False, (
            f"still looks like a login page ({page.url[:120]}); sign in fully, "
            "then re-run this script before using --transport playwright."
        )
    if page.locator(qd.SEL_INPUT).count() == 0:
        return False, (
            "chat input not found on the final page; open the agent chat (and "
            "sign in if you were bounced back to it), then re-run this script."
        )
    return True, READY_MESSAGE


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--profile-dir", default=".auth/quick-profile")
    args = ap.parse_args()

    profile = Path(args.profile_dir)
    profile.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(profile), headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(args.url)
        print(f"Profile: {profile}")
        print("Sign in, open the agent, then press Enter here to save and close.")
        input("> ")
        print(f"  final URL: {page.url}")
        ready, message = check_session_ready(page)
        ctx.close()

    if not ready:
        print(f"error: {message}")
        return 1
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
