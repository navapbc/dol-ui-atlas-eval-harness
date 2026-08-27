from pathlib import Path

import pytest

from atlas_eval.cli import main
from atlas_eval.runs import read_run

BANK = """version: v3
agent: engineering_onboarding_specialist
corpus: quick_space_ca7_daily_s3
questions:
  - id: v3-Q1
    text: Describe the ACP.
    type: retrieval
    expected_stance: answer
    ground_truth: ACP is the Accelerated Collection Process.
    checks:
      required_all: [ACP]
"""


def _bank(tmp_path):
    p = tmp_path / "v3.yaml"
    p.write_text(BANK)
    return p


def test_paste_transport_end_to_end(tmp_path, capsys):
    bank = _bank(tmp_path)
    transcript = tmp_path / "pasted.md"
    transcript.write_text(
        "<!-- atlas:answer v3-Q1 -->\nThe ACP is the Accelerated Collection Process.\n"
    )
    runs = tmp_path / "runs"

    code = main(["run", "--bank", str(bank), "--transport", "paste",
                 "--transcript", str(transcript), "--runs", str(runs), "--no-snapshot"])
    assert code == 0
    out = capsys.readouterr().out
    assert "complete" in out

    run_dir = next(runs.iterdir())
    meta, responses, rows = read_run(run_dir)
    assert meta.transport == "paste"
    assert responses["v3-Q1"].startswith("The ACP")
    assert len(rows) == 1


def test_paste_transport_requires_a_transcript(tmp_path, capsys):
    code = main(["run", "--bank", str(_bank(tmp_path)), "--transport", "paste",
                 "--runs", str(tmp_path / "runs"), "--no-snapshot"])
    assert code == 2
    assert "--transcript" in capsys.readouterr().out


def test_incomplete_paste_exits_nonzero_but_still_writes_the_run(tmp_path, capsys):
    bank = tmp_path / "v3.yaml"
    bank.write_text(BANK + """  - id: v3-Q2
    text: And what does ACP stand for?
    type: acronym_check
    expected_stance: answer
    ground_truth: Accelerated Collection Process.
""")
    transcript = tmp_path / "pasted.md"
    transcript.write_text("<!-- atlas:answer v3-Q1 -->\nThe ACP.\n")
    runs = tmp_path / "runs"

    code = main(["run", "--bank", str(bank), "--transport", "paste",
                 "--transcript", str(transcript), "--runs", str(runs), "--no-snapshot"])
    assert code == 1, "an incomplete run must not report success"
    assert "incomplete" in capsys.readouterr().out.lower()
    assert read_run(next(runs.iterdir()))[0].status.value == "incomplete"


def test_print_sheet_emits_the_run_sheet_and_exits_zero(tmp_path, capsys):
    code = main(["run", "--bank", str(_bank(tmp_path)), "--transport", "paste",
                 "--print-sheet", "--runs", str(tmp_path / "runs"), "--no-snapshot"])
    assert code == 0
    out = capsys.readouterr().out
    assert "v3-Q1" in out
    assert "<!-- atlas:answer v3-Q1 -->" in out
    assert "Describe the ACP." in out
    assert "same conversation" in out.lower()


def test_playwright_transport_requires_a_url(tmp_path, capsys):
    code = main(["run", "--bank", str(_bank(tmp_path)), "--transport", "playwright",
                 "--runs", str(tmp_path / "runs"), "--no-snapshot"])
    assert code == 2
    assert "--url" in capsys.readouterr().out


def test_missing_bank_exits_two(tmp_path, capsys):
    code = main(["run", "--bank", str(tmp_path / "nope.yaml"), "--transport", "paste",
                 "--transcript", str(tmp_path / "t.md"), "--runs", str(tmp_path / "runs"),
                 "--no-snapshot"])
    assert code == 2


def test_run_help_lists_both_transports(capsys):
    with pytest.raises(SystemExit):
        main(["run", "--help"])
    out = capsys.readouterr().out
    assert "paste" in out and "playwright" in out
