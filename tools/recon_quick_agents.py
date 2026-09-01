"""Reconnaissance spike: capture the Quick *agents picker* DOM.

The chat-DOM recon (tools/recon_quick_dom.py) captured the chat page with the
default agent already active. It never captured the picker you use to CHOOSE an
agent, so the transport cannot yet select v1 vs v2 -- it only confirms which
agent answered, after the fact. This spike captures the picker so a
`select_agent(page, name)` can be written against a real fixture, not a guess.

Runs against the persistent profile you already signed into with
tools/open_quick_session.py. It never touches credentials. If the profile has
no live session it will land on a login hop and the capture will just show that;
sign in again and re-run.

    .venv/bin/python tools/recon_quick_agents.py \\
      --url "https://us-east-1.quicksight.aws.amazon.com/sn/account/njuimod/start/agents"

Writes into tests/fixtures/quick/:
    agents_picker.html             full DOM of the picker page
    agents_picker.selectors.json   clickable-element inventory (text + testids)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from atlas_eval.adapters import quick_dom as qd

FIXTURES = Path("tests/fixtures/quick")

# Inventory every element a human could click to pick an agent, with enough
# identifying context (text, testid, role, href) to design a name-based
# selector afterwards. Kept deliberately broad: we do not yet know whether an
# agent renders as a card, a link, a listitem, or a button.
PROBE_JS = """
() => {
  const desc = (el) => ({
    tag: el.tagName.toLowerCase(),
    testid: el.getAttribute('data-testid'),
    role: el.getAttribute('role'),
    label: el.getAttribute('aria-label'),
    href: el.getAttribute('href'),
    id: el.id || null,
    text: (el.innerText || '').trim().slice(0, 80),
  });
  const sel = 'a,button,[role="button"],[role="option"],[role="listitem"],'
            + '[data-testid*="agent"],[class*="agent" i],[class*="card" i]';
  const out = [];
  document.querySelectorAll(sel).forEach(el => {
    const d = desc(el);
    // Drop chrome with no text and no agent-ish testid -- noise for this spike.
    if (d.text || (d.testid && d.testid.toLowerCase().includes('agent'))) {
      out.push(d);
    }
  });
  return out;
}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--profile-dir", default=".auth/quick-profile")
    ap.add_argument("--settle-ms", type=int, default=6000,
                    help="how long to let the SPA render before capturing")
    ap.add_argument("--tab", default=None,
                    help="click this selector tab (e.g. Favorites) after "
                         "opening the dropdown, before capturing")
    args = ap.parse_args()

    FIXTURES.mkdir(parents=True, exist_ok=True)
    profile = Path(args.profile_dir)

    # The agent list only exists in the DOM once the selector dropdown is
    # opened; the footer button that opens it shows the currently active agent.
    sel_open = '[data-testid="qbiz-component-agent-selector-footer-button"]'

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(profile), headless=False)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(args.url)
            page.wait_for_timeout(args.settle_ms)

            if qd.is_auth_redirect(page.url):
                print(f"error: landed on a login hop ({page.url[:120]}); "
                      "sign in with tools/open_quick_session.py and re-run.")
                return 1

            # Open the agent-selector dropdown so its list of agents (the
            # Favorites tab) renders into the DOM before we capture. Best
            # effort: if the button isn't found, capture the page as-is so the
            # inventory still shows what selectors DO exist.
            opener = page.locator(sel_open)
            if opener.count():
                opener.first.click()
                page.wait_for_timeout(1500)
                print(f"opened agent selector via {sel_open}")
            else:
                print(f"warning: {sel_open} not found; capturing without "
                      "opening the dropdown")

            if args.tab:
                tab = page.get_by_role("tab", name=args.tab, exact=True)
                if tab.count():
                    tab.first.click()
                    page.wait_for_timeout(1500)
                    print(f"clicked tab {args.tab!r}")
                else:
                    print(f"warning: tab {args.tab!r} not found")

            # Every agent card's title, so the exact display names are on record
            # for an exact-text selector (v1's name is a prefix of v2's, so the
            # match must be exact).
            cards = page.locator('[data-testid="qbiz-components-agent-card"]')
            print(f"agent cards on this tab: {cards.count()}")
            for i in range(cards.count()):
                title = cards.nth(i).locator("p").first
                if title.count():
                    print(f"  card[{i}] title: {title.inner_text().strip()!r}")

            html = page.content()
            (FIXTURES / "agents_picker.html").write_text(html)

            inventory = page.evaluate(PROBE_JS)
            (FIXTURES / "agents_picker.selectors.json").write_text(
                json.dumps(inventory, indent=2)
            )

            print(f"final URL: {page.url}")
            print(f"captured {len(inventory)} clickable element(s) to "
                  f"{FIXTURES / 'agents_picker.selectors.json'}")
            # Surface the likely agent rows immediately so the operator (or the
            # next automated step) can eyeball that the names are present.
            for d in inventory:
                if d["text"] and "onboarding" in d["text"].lower():
                    print(f"  candidate: testid={d['testid']!r} role={d['role']!r} "
                          f"text={d['text']!r}")
        finally:
            ctx.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
