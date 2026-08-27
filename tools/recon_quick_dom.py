"""Reconnaissance spike: capture the Quick chat DOM so the transport can be
written against real fixtures instead of guesses.

Runs headed. You log in through Identity Center yourself; this script never
touches credentials and never types into a password field. It waits for you to
drive the conversation, then dumps the DOM and a candidate-selector report.

    .venv/bin/python tools/recon_quick_dom.py --url <quick-chat-url>

Deliverables it writes into tests/fixtures/quick/:
    <name>.landing.json/html        the page as the URL leaves it (default agent open)
    <name>.selectors_before.json   control inventory while idle
    <name>.selectors_after.json    control inventory once an answer finished
    <name>.html                     full DOM of the finished conversation

The button delta between before and after is the strongest candidate for the
streaming-complete signal, which is the one thing this spike exists to settle.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

FIXTURES = Path("tests/fixtures/quick")

PROBE_JS = """
() => {
  const out = {editables: [], buttons: [], live: [], busy: []};
  const desc = (el) => ({
    tag: el.tagName.toLowerCase(),
    testid: el.getAttribute('data-testid'),
    role: el.getAttribute('role'),
    label: el.getAttribute('aria-label'),
    id: el.id || null,
    cls: (el.className && el.className.toString().slice(0, 120)) || null,
    text: (el.innerText || '').trim().slice(0, 60),
  });
  document.querySelectorAll('textarea,[contenteditable="true"],input[type="text"]')
    .forEach(el => out.editables.push(desc(el)));
  document.querySelectorAll('button,[role="button"]').forEach(el => out.buttons.push(desc(el)));
  document.querySelectorAll('[aria-live]').forEach(el => out.live.push(desc(el)));
  document.querySelectorAll('[aria-busy]').forEach(el => out.busy.push(desc(el)));
  return out;
}
"""


def _key(d: dict) -> tuple:
    return (d["tag"], d["testid"], d["label"], d["text"])


def _report(label: str, probe: dict) -> None:
    print(f"\n--- {label} ---")
    for kind in ("editables", "buttons", "live", "busy"):
        items = probe[kind]
        print(f"  {kind}: {len(items)}")
        for it in items[:8]:
            bits = [f"<{it['tag']}>"]
            for attr in ("testid", "role", "label", "id"):
                if it[attr]:
                    bits.append(f"{attr}={it[attr]!r}")
            if it["text"]:
                bits.append(f"text={it['text']!r}")
            print("      " + " ".join(bits))
        if len(items) > 8:
            print(f"      ... {len(items) - 8} more")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="Quick chat agent URL")
    ap.add_argument("--out", default="conversation_complete", help="fixture basename")
    args = ap.parse_args()

    FIXTURES.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(args.url)

        print("\n" + "=" * 70)
        print("STEP 1 — sign in; the chat agent should already be open")
        print("=" * 70)
        print("Log in via Identity Center. This URL lands directly on the Quick page with")
        print("the default chat agent already open (in a panel, not full screen).")
        print("Change nothing yet — press Enter as soon as it has finished loading.")
        input("> ")

        landing = page.evaluate(PROBE_JS)
        (FIXTURES / f"{args.out}.landing.selectors.json").write_text(
            json.dumps(landing, indent=2)
        )
        (FIXTURES / f"{args.out}.landing.html").write_text(page.content())
        _report("LANDING (default agent, as the URL leaves it)", landing)
        print(f"\n  landing URL: {page.url}")

        print("\n" + "=" * 70)
        print("STEP 2 — get it into the exact state a scored run would use")
        print("=" * 70)
        print("Two things, and it is fine if either is a no-op:")
        print()
        print("  a) If the open agent is NOT the one you want to test (Engineering")
        print("     Onboarding Specialist), switch to it now.")
        print("  b) If there is an expand / full-screen control for the chat, use it.")
        print("     A scored run must always start from the same layout, and a panel")
        print("     and an expanded view can carry different selectors.")
        print()
        print("Press Enter once the chat input is visible in the state a run would use.")
        input("> ")
        print(f"  URL in run state: {page.url}")
        print("  (same as the landing URL means the state is not addressable by URL,")
        print("   so the transport has to reproduce it by clicking)")

        pre = page.evaluate(PROBE_JS)
        (FIXTURES / f"{args.out}.selectors_before.json").write_text(json.dumps(pre, indent=2))
        _report("IDLE (before asking anything)", pre)

        print("\n" + "=" * 70)
        print("STEP 3 — ask two questions")
        print("=" * 70)
        print("Ask at least two questions. Make ONE of them a question whose answer runs")
        print("several paragraphs — completion detection has to be exercised against a long")
        print("streaming response, not a one-liner. A good long one from the real bank:")
        print()
        print('  "Walk me through the daily bank reconciliation job L204DF2: what does it')
        print('   produce, and how do check records get from the daily register to the bank')
        print('   files?"')
        print()
        print("Press Enter once the LAST answer has completely finished rendering.")
        input("> ")

        post = page.evaluate(PROBE_JS)
        (FIXTURES / f"{args.out}.selectors_after.json").write_text(json.dumps(post, indent=2))
        (FIXTURES / f"{args.out}.html").write_text(page.content())
        _report("DONE (after the last answer finished)", post)

        before, after = {_key(b) for b in pre["buttons"]}, {_key(b) for b in post["buttons"]}
        print("\n" + "=" * 70)
        print("BUTTON DELTA — candidate streaming-complete signals")
        print("=" * 70)
        appeared, vanished = sorted(after - before), sorted(before - after)
        for k in appeared:
            print("  appeared:", k)
        for k in vanished:
            print("  vanished:", k)
        if not appeared and not vanished:
            print("  (no button changed — completion will need aria-busy, aria-live,")
            print("   or a DOM-quiet interval instead)")

        print(f"\nWrote fixtures to {FIXTURES}/")
        print("Next: scrub the HTML for tokens before it is committed (the repo's")
        print("docs/recon note lists the exact grep commands).")
        input("\nPress Enter to close the browser. ")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
