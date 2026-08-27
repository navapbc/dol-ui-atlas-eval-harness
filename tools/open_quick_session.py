"""Open a headed browser against the persistent profile so you can sign in once.

Authentication is a deliberate human step, kept out of the run path: the harness
never submits credentials. Sign in here, close the window, and later runs reuse
the profile until the session expires.

    .venv/bin/python tools/open_quick_session.py \\
      --url "https://us-east-1.quicksight.aws.amazon.com/sn/account/njuimod/start/agents"
"""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


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
        ctx.close()
    print("Session stored. Runs can now use --transport playwright.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
