"""Capture the agent and space configuration a run was executed against.

Without this, an old score is uninterpretable: you cannot tell whether a
regression came from the model, the instructions, or the corpus. Everything here
is read-only - the harness reads agent config and never writes it.

The AWS account id is used to scope the calls but is deliberately never stored:
snapshots are committed to the repo.
"""

from __future__ import annotations

import json
import subprocess

READ_ONLY_OPS = ("list-agents", "describe-agent", "list-spaces")


class SnapshotError(Exception):
    """The control-plane capture could not be completed."""


def default_aws_runner(args: list[str]) -> str:
    """Run `aws <args>` and return stdout. Read-only calls only."""
    if args[1] not in READ_ONLY_OPS:
        raise SnapshotError(f"refusing non-read-only operation: {args[1]}")
    completed = subprocess.run(
        ["aws", *args, "--output", "json"],
        capture_output=True, text=True, check=False,
    )
    if completed.returncode != 0:
        raise SnapshotError(
            f"aws {' '.join(args)} failed ({completed.returncode}): "
            f"{completed.stderr.strip()[:400]}"
        )
    return completed.stdout


def _call(runner, args: list[str]) -> dict:
    try:
        raw = runner(args)
    except SnapshotError:
        raise
    except Exception as err:  # OSError, subprocess problems, injected fakes
        raise SnapshotError(f"aws {' '.join(args)} failed: {err}") from err
    try:
        return json.loads(raw)
    except json.JSONDecodeError as err:
        raise SnapshotError(f"aws {' '.join(args)} returned non-JSON: {err}") from err


def capture(
    account_id: str,
    agent_id: str | None = None,
    runner=default_aws_runner,
    agent_name: str | None = None,
) -> dict:
    """Snapshot the agent and its linked spaces.

    Pass agent_id when known. Otherwise pass agent_name and it is resolved from
    list-agents, so a run is never recorded against a guessed agent.
    """
    agents = _call(runner, ["quicksight", "list-agents", "--aws-account-id", account_id])

    if agent_id is None:
        if not agent_name:
            raise SnapshotError("one of agent_id or agent_name is required")
        matches = [a for a in agents.get("AgentSummaryList", [])
                   if a.get("Name") == agent_name]
        if not matches:
            available = ", ".join(sorted(
                a.get("Name", "?") for a in agents.get("AgentSummaryList", [])
            ))
            raise SnapshotError(
                f"no agent named {agent_name!r}; available: {available or '(none)'}"
            )
        agent_id = matches[0]["AgentId"]

    agent = _call(runner, ["quicksight", "describe-agent", "--aws-account-id",
                           account_id, "--agent-id", agent_id])
    spaces = _call(runner, ["quicksight", "list-spaces", "--aws-account-id", account_id])

    return {
        "captured_with": "aws quicksight (read-only)",
        "operations": list(READ_ONLY_OPS),
        "agent": agent.get("Agent", {}),
        "agent_list": agents.get("AgentSummaryList", []),
        "spaces": spaces.get("SpaceSummaryList", []),
    }
