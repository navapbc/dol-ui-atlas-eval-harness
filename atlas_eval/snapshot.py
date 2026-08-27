"""Capture the agent and space configuration a run was executed against.

Without this, an old score is uninterpretable: you cannot tell whether a
regression came from the model, the instructions, or the corpus. Everything here
is read-only - the harness reads agent config and never writes it.

The AWS account id is used to scope the calls but is deliberately never stored:
snapshots are committed to the repo.
"""

from __future__ import annotations

import json
import re
import subprocess

READ_ONLY_OPS = ("list-agents", "describe-agent", "list-spaces")

# Known mutating quicksight operations. Checked against every element of args
# (not a fixed index) because a caller can put a decoy at the position we'd
# otherwise trust, e.g. ["--profile", "list-agents", "quicksight",
# "update-agent", ...] - the real operation would run unchecked if we only
# looked at args[1]. Scanning for known-bad operations anywhere in args, and
# requiring exactly one known-good operation to be present, does not depend
# on positional assumptions at all.
MUTATING_OPS = (
    "create-agent",
    "update-agent",
    "delete-agent",
    "update-space",
    "update-space-resources",
    "delete-space",
)

_ACCOUNT_PLACEHOLDER = "<ACCOUNT-ID>"
_EMAIL_PLACEHOLDER = "<EMAIL>"
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


class SnapshotError(Exception):
    """The control-plane capture could not be completed."""


def _validate_read_only(args: list[str]) -> None:
    """Reject anything that isn't exactly one allowed read-only operation.

    Does not trust any particular position in args - see the comment on
    MUTATING_OPS for why. Every element is checked against both the denylist
    of known mutating operations and the allowlist of read-only ones.
    """
    mutating_present = [a for a in args if a in MUTATING_OPS]
    if mutating_present:
        raise SnapshotError(f"refusing non-read-only operation: {mutating_present[0]}")
    read_only_present = [a for a in args if a in READ_ONLY_OPS]
    if len(read_only_present) != 1:
        raise SnapshotError(f"expected exactly one read-only operation in {args}")


def default_aws_runner(args: list[str]) -> str:
    """Run `aws <args>` and return stdout. Read-only calls only."""
    _validate_read_only(args)
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
    # Enforced here too (not just in default_aws_runner) so the guard holds
    # no matter which runner capture() is given - a test fake or any other
    # injected runner cannot skip it.
    _validate_read_only(args)
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


def _scrub(value, account_id: str):
    """Recursively redact account ids and email addresses from a payload.

    Redacts rather than deletes: an ARN like
    arn:aws:quicksight:us-east-1:<ACCOUNT-ID>:agent/093ac4e3-... keeps its
    shape and resource path (arn:aws:quicksight:us-east-1:<ACCOUNT-ID>:agent/
    093ac4e3-...) so the snapshot stays useful for debugging while the
    identifying number is gone.
    """
    if isinstance(value, dict):
        return {k: _scrub(v, account_id) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(v, account_id) for v in value]
    if isinstance(value, str):
        scrubbed = value.replace(account_id, _ACCOUNT_PLACEHOLDER)
        scrubbed = _EMAIL_RE.sub(_EMAIL_PLACEHOLDER, scrubbed)
        return scrubbed
    return value


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

    snapshot = {
        "captured_with": "aws quicksight (read-only)",
        "operations": list(READ_ONLY_OPS),
        "agent": agent.get("Agent", {}),
        "agent_list": agents.get("AgentSummaryList", []),
        "spaces": spaces.get("SpaceSummaryList", []),
    }
    return _scrub(snapshot, account_id)
