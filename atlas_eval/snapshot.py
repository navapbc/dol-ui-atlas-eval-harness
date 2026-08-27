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


def default_aws_runner(args: list[str], profile: str | None = None) -> str:
    """Run `aws <args>` and return stdout. Read-only calls only.

    profile selects a named AWS CLI profile. It is appended AFTER the
    operation rather than prepended, so it can never displace the element the
    read-only guard inspects -- and the guard is validated before the profile
    is added at all.
    """
    _validate_read_only(args)
    argv = ["aws", *args, "--output", "json"]
    if profile:
        argv += ["--profile", profile]
    completed = subprocess.run(
        argv, capture_output=True, text=True, check=False,
    )
    if completed.returncode != 0:
        raise SnapshotError(
            f"aws {' '.join(args)} failed ({completed.returncode}): "
            f"{completed.stderr.strip()[:400]}"
        )
    return completed.stdout


def _invoke(runner, args: list[str], profile: str | None):
    """Call a runner, passing profile only if it accepts one.

    Tests inject single-argument runners, and a caller's runner has no reason
    to know about profiles unless it shells out to the AWS CLI.
    """
    if profile is None:
        return runner(args)
    try:
        return runner(args, profile=profile)
    except TypeError:
        # Runner does not accept a profile; the caller supplied one that
        # cannot be honoured, which is worth saying rather than ignoring.
        raise SnapshotError(
            f"a profile ({profile!r}) was supplied but the runner does not "
            "accept one"
        ) from None


def _call(runner, args: list[str], profile: str | None = None) -> dict:
    # Enforced here too (not just in default_aws_runner) so the guard holds
    # no matter which runner capture() is given - a test fake or any other
    # injected runner cannot skip it.
    _validate_read_only(args)
    try:
        raw = _invoke(runner, args, profile)
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
    arn:aws:quicksight:us-east-1:000000000000:agent/093ac4e3-... keeps its
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


# ---------------------------------------------------------------------------
# Projection: keep only the fields a snapshot needs, drop everything else.
#
# A denylist scrubber (_scrub, above) can only redact the shapes it already
# knows to look for - an account id, an email address. It has no way to
# catch a username inside an IAM ARN, a CreatedBy field, an Owner block, a
# tag value, or a role name: those don't match either pattern, so they sail
# through untouched. That is the same operator-identity leak the account-id
# fix was about, just without an '@' to match on, and each new pattern added
# to catch it would be one more guess about how a person's identity might
# show up in a string.
#
# The fix is to stop trying to recognise identity strings and instead keep
# only the handful of fields a snapshot actually needs to make an old score
# interpretable: what agent produced it (id, name, instructions, model), and
# what corpus it could draw on (which spaces, roughly how big). Everything
# else describe-agent / list-agents / list-spaces returns - Arn, Creator,
# CreatedBy, Owner, Tags, ActionConnectors, QbsAwsAccountId, SubscriptionId,
# and any field AWS adds later - is dropped by construction, not by
# recognising it as sensitive. A field only ends up in a snapshot if someone
# adds it to one of the projections below on purpose.
#
# Field names below come from data/runs/*/snapshot.json (40 migrated
# snapshots of real describe-agent / list-spaces responses), not from
# guessing at AWS's shape. Notably the real instructions field lives at
# Agent.CustomPromptInterface.CustomInstructions, not a flat "Instructions"
# key, and the model lives at CustomPromptInterface.ModelProfileId. The real
# list-spaces payloads observed use lowercase spaceId/name/resourcesCount/
# consumedSourceDocCount/consumedSourceSize; both that casing and the
# PascalCase the rest of this API uses are accepted, since this projection
# should not have an opinion about which one a given AWS response uses.
# ---------------------------------------------------------------------------


def _first_present(d: dict, *keys):
    """Return the value of the first key in `keys` that is present in `d`."""
    for key in keys:
        if key in d:
            return d[key]
    return None


def _project_agent(agent: dict) -> dict:
    """Project a describe-agent Agent onto the allowlisted fields.

    Instructions is the most important field here: a changed prompt is the
    most likely cause of a score shift, and it is also the one most likely
    to contain free text a human wrote - so it stays subject to _scrub (see
    capture()) even though it is allowlisted.
    """
    custom_prompt = agent.get("CustomPromptInterface") or {}
    projected = {
        "AgentId": agent.get("AgentId"),
        "Name": agent.get("Name"),
        "Instructions": custom_prompt.get("CustomInstructions", agent.get("Instructions")),
        "ModelId": custom_prompt.get("ModelProfileId", agent.get("ModelId")),
        "CreatedAt": agent.get("CreatedAt"),
        "UpdatedAt": agent.get("UpdatedAt"),
    }
    return {k: v for k, v in projected.items() if v is not None}


def _project_agent_summary(summary: dict) -> dict:
    """Project a list-agents summary: just enough to tell which agents existed."""
    projected = {"AgentId": summary.get("AgentId"), "Name": summary.get("Name")}
    return {k: v for k, v in projected.items() if v is not None}


def _project_space(space: dict) -> dict:
    """Project a list-spaces summary onto id, name, and corpus size.

    The linked corpus is what determines what the agent can retrieve, so a
    rough size (document count / byte size) is kept as the closest thing to
    a resource identifier the real payloads carry - there is no distinct
    per-resource id or arn in the data this was checked against.
    """
    projected = {
        "SpaceId": _first_present(space, "SpaceId", "spaceId"),
        "Name": _first_present(space, "Name", "name"),
        "ResourcesCount": _first_present(space, "ResourcesCount", "resourcesCount"),
        "ConsumedSourceDocCount": _first_present(
            space, "ConsumedSourceDocCount", "consumedSourceDocCount"),
        "ConsumedSourceSize": _first_present(space, "ConsumedSourceSize", "consumedSourceSize"),
    }
    return {k: v for k, v in projected.items() if v is not None}


def capture(
    account_id: str,
    agent_id: str | None = None,
    runner=default_aws_runner,
    agent_name: str | None = None,
    profile: str | None = None,
) -> dict:
    """Snapshot the agent and its linked spaces.

    Pass agent_id when known. Otherwise pass agent_name and it is resolved from
    list-agents, so a run is never recorded against a guessed agent.
    """
    if not account_id:
        # str.replace("", "<ACCOUNT-ID>") (in _scrub) inserts the placeholder
        # between every character of every string in the snapshot -- refuse
        # up front rather than silently produce a mangled snapshot.
        raise SnapshotError("account_id must not be empty")
    agents = _call(runner, ["quicksight", "list-agents", "--aws-account-id", account_id],
                   profile)

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
                           account_id, "--agent-id", agent_id], profile)
    spaces = _call(runner, ["quicksight", "list-spaces", "--aws-account-id", account_id],
                    profile)

    snapshot = {
        "captured_with": "aws quicksight (read-only)",
        "operations": list(READ_ONLY_OPS),
        "agent": _project_agent(agent.get("Agent", {})),
        "agent_list": [_project_agent_summary(a) for a in agents.get("AgentSummaryList", [])],
        "spaces": [_project_space(s) for s in spaces.get("SpaceSummaryList", [])],
    }
    # The projection above already drops ARNs/CreatedBy/Owner/tags/etc, but
    # the scrubber still runs over what's left as defence in depth: Instructions
    # is free text a human wrote and could itself name someone.
    return _scrub(snapshot, account_id)
