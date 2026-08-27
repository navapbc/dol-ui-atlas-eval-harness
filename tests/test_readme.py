from pathlib import Path


def _section(text: str, heading: str) -> str:
    """The body of a '## heading' section, up to the next '## ' heading."""
    start = text.index(f"## {heading}")
    rest = text[start:]
    next_heading = rest.find("\n## ", 1)
    return rest if next_heading == -1 else rest[:next_heading]


def test_running_a_bank_section_mentions_the_rollup_command():
    # CI runs `atlas-eval rollup --check` (see .github/workflows/ci.yml), so
    # an operator's first real run -- which regenerates data/runs/ but not
    # data/scores.csv -- fails CI unless they already knew to run `rollup`
    # too. The "Running a bank" section walked through paste and playwright
    # runs end to end without ever mentioning it.
    readme = Path("README.md").read_text(encoding="utf-8")
    section = _section(readme, "Running a bank")
    assert "atlas-eval rollup" in section, (
        "the 'Running a bank' section must tell the operator to run "
        "`atlas-eval rollup` afterward, since CI checks it"
    )
