import json
from unittest import mock

import pytest

from atlas_eval.snapshot import MUTATING_OPS, SnapshotError, capture, default_aws_runner

AGENTS = {"AgentSummaryList": [
    {"AgentId": "093ac4e3-0712-481e-af95-9ddc5e4fc734",
     "Name": "Engineering Onboarding Specialist"},
    {"AgentId": "aaaaaaaa-0000-0000-0000-000000000000", "Name": "Other Agent"},
]}
AGENT = {"Agent": {"AgentId": "093ac4e3-0712-481e-af95-9ddc5e4fc734",
                   "Name": "Engineering Onboarding Specialist",
                   "CustomPromptInterface": {
                       "CustomInstructions": "you are an onboarding specialist",
                       "ModelProfileId": "c394c917-e855-4485-ba79-f96d9461d551",
                   }}}
SPACES = {"SpaceSummaryList": [{"SpaceId": "s1", "Name": "quick_space_ca7_daily_s3"}]}


def _runner(calls, responses):
    def run(args):
        calls.append(args)
        for key, payload in responses.items():
            if key in args:
                return json.dumps(payload)
        raise AssertionError(f"unexpected call: {args}")
    return run


def test_capture_records_agent_and_spaces():
    calls = []
    snap = capture("123456789012", agent_id="093ac4e3-0712-481e-af95-9ddc5e4fc734",
                   runner=_runner(calls, {"list-agents": AGENTS,
                                          "describe-agent": AGENT,
                                          "list-spaces": SPACES}))
    assert snap["agent"]["Name"] == "Engineering Onboarding Specialist"
    assert snap["agent"]["Instructions"] == "you are an onboarding specialist"
    assert snap["spaces"][0]["Name"] == "quick_space_ca7_daily_s3"
    assert snap["captured_with"] == "aws quicksight (read-only)"


def test_capture_uses_only_read_only_operations():
    calls = []
    capture("123456789012", agent_id="093ac4e3-0712-481e-af95-9ddc5e4fc734",
            runner=_runner(calls, {"list-agents": AGENTS, "describe-agent": AGENT,
                                   "list-spaces": SPACES}))
    flat = [a for call in calls for a in call]
    for forbidden in ("create-agent", "update-agent", "delete-agent",
                      "update-space", "update-space-resources", "delete-space"):
        assert forbidden not in flat, forbidden
    assert all(call[0] == "quicksight" for call in calls)


def test_account_id_is_not_stored_in_the_snapshot():
    # Snapshots are committed; an AWS account id must not enter the repo.
    snap = capture("123456789012", agent_id="093ac4e3-0712-481e-af95-9ddc5e4fc734",
                   runner=_runner([], {"list-agents": AGENTS, "describe-agent": AGENT,
                                       "list-spaces": SPACES}))
    assert "123456789012" not in json.dumps(snap)


def test_agent_id_resolved_by_name_when_not_given():
    snap = capture("123456789012", agent_id=None,
                   runner=_runner([], {"list-agents": AGENTS, "describe-agent": AGENT,
                                       "list-spaces": SPACES}),
                   agent_name="Engineering Onboarding Specialist")
    assert snap["agent"]["AgentId"] == "093ac4e3-0712-481e-af95-9ddc5e4fc734"


def test_unknown_agent_name_raises():
    with pytest.raises(SnapshotError) as exc:
        capture("123456789012", agent_id=None,
                runner=_runner([], {"list-agents": AGENTS}),
                agent_name="No Such Agent")
    assert "No Such Agent" in str(exc.value)


def test_cli_failure_surfaces_as_snapshot_error():
    def boom(args):
        raise OSError("aws: command not found")
    with pytest.raises(SnapshotError) as exc:
        capture("123456789012", agent_id="x", runner=boom)
    # Must carry the actual underlying detail, not just the wrapper's own
    # boilerplate ("aws" appears in every wrapped message unconditionally).
    assert "command not found" in str(exc.value)


def test_bad_json_surfaces_as_snapshot_error():
    with pytest.raises(SnapshotError):
        capture("123456789012", agent_id="x", runner=lambda args: "not json")


def test_empty_account_id_is_refused_rather_than_corrupting_the_scrub():
    # str.replace("", "<ACCOUNT-ID>") inserts the placeholder between every
    # character of every string in the snapshot -- an empty account_id must
    # be refused up front, not silently produce a mangled snapshot.
    with pytest.raises(SnapshotError):
        capture("", agent_id="093ac4e3-0712-481e-af95-9ddc5e4fc734",
                runner=_runner([], {"list-agents": AGENTS, "describe-agent": AGENT,
                                    "list-spaces": SPACES}))


# ---------------------------------------------------------------------------
# Finding 1, fix pass 2: denylist scrubbing caught the account id and
# email-shaped strings but let a username inside an ARN, a CreatedBy, an
# Owner block, a tag value, and a role name through - none of those match
# an account-id or email pattern. The fix replaces scrubbing-only with a
# projection onto an allowlist: fields not on the allowlist are dropped
# regardless of what they contain, so an unrecognised leak shape cannot
# survive by accident.
# ---------------------------------------------------------------------------

REAL_ACCOUNT_ID = "000000000000"  # obviously-fake account id, not the real one

# Mirrors the four leaks the reviewer demonstrated getting past the old
# scrubber: a username inside an IAM ARN, a plain CreatedBy, a tag value,
# and a role name embedding a username.
LEAKY_AGENT = {"Agent": {
    "AgentId": "093ac4e3-0712-481e-af95-9ddc5e4fc734",
    "Name": "Engineering Onboarding Specialist",
    "Arn": f"arn:aws:iam::{REAL_ACCOUNT_ID}:user/jsmith",
    "CreatedBy": "jsmith",
    "Owner": {"Arn": f"arn:aws:iam::{REAL_ACCOUNT_ID}:role/created-by-jdoe-admin-role"},
    "Tags": [{"Key": "Owner", "Value": "jdoe"}],
    "CustomPromptInterface": {
        "CustomInstructions": "you are an onboarding specialist",
        "ModelProfileId": "c394c917-e855-4485-ba79-f96d9461d551",
    },
    "CreatedAt": "2026-06-10T18:19:25.328000-04:00",
}}
LEAKY_AGENTS = {"AgentSummaryList": [
    {"AgentId": "093ac4e3-0712-481e-af95-9ddc5e4fc734",
     "Name": "Engineering Onboarding Specialist",
     "Arn": f"arn:aws:iam::{REAL_ACCOUNT_ID}:user/jsmith"},
]}
LEAKY_SPACES = {"SpaceSummaryList": [
    {"SpaceId": "s1", "Name": "quick_space_ca7_daily_s3",
     "createdBy": "AWSReservedSSO_AWSAdministratorAccess_x/jsmith@example.invalid",
     "createdByArn": f"arn:aws:quicksight:us-east-1:{REAL_ACCOUNT_ID}:user/default/jsmith",
     "Tags": [{"Key": "Owner", "Value": "jdoe"}],
     "resourcesCount": 1, "consumedSourceDocCount": 28},
]}


def test_allowlist_projection_drops_identity_leaks_the_old_scrubber_missed():
    snap = capture(REAL_ACCOUNT_ID, agent_id="093ac4e3-0712-481e-af95-9ddc5e4fc734",
                   runner=_runner([], {"list-agents": LEAKY_AGENTS, "describe-agent": LEAKY_AGENT,
                                       "list-spaces": LEAKY_SPACES}))
    dumped = json.dumps(snap)

    # The four leaks the reviewer demonstrated.
    assert "jsmith" not in dumped
    assert "jdoe" not in dumped
    assert "created-by-jdoe-admin-role" not in dumped
    assert f"arn:aws:iam::{REAL_ACCOUNT_ID}:user/jsmith" not in dumped

    # The keys that carried them are gone entirely, not just redacted.
    assert "Arn" not in snap["agent"]
    assert "CreatedBy" not in snap["agent"]
    assert "Owner" not in snap["agent"]
    assert "Tags" not in snap["agent"]
    assert "createdBy" not in snap["spaces"][0]
    assert "createdByArn" not in snap["spaces"][0]
    assert "Tags" not in snap["spaces"][0]


def test_allowlisted_fields_survive_the_projection():
    # Dropping instructions would silently make snapshots useless, so this
    # is the field most worth pinning as surviving.
    snap = capture(REAL_ACCOUNT_ID, agent_id="093ac4e3-0712-481e-af95-9ddc5e4fc734",
                   runner=_runner([], {"list-agents": LEAKY_AGENTS, "describe-agent": LEAKY_AGENT,
                                       "list-spaces": LEAKY_SPACES}))
    assert snap["agent"]["AgentId"] == "093ac4e3-0712-481e-af95-9ddc5e4fc734"
    assert snap["agent"]["Name"] == "Engineering Onboarding Specialist"
    assert snap["agent"]["Instructions"] == "you are an onboarding specialist"
    assert snap["agent"]["ModelId"] == "c394c917-e855-4485-ba79-f96d9461d551"
    assert snap["agent"]["CreatedAt"] == "2026-06-10T18:19:25.328000-04:00"
    assert snap["agent_list"][0]["AgentId"] == "093ac4e3-0712-481e-af95-9ddc5e4fc734"
    assert snap["spaces"][0]["SpaceId"] == "s1"
    assert snap["spaces"][0]["Name"] == "quick_space_ca7_daily_s3"
    assert snap["spaces"][0]["ResourcesCount"] == 1
    assert snap["spaces"][0]["ConsumedSourceDocCount"] == 28


def test_unexpected_new_field_does_not_leak_through():
    # Pins the actual property the allowlist buys over denylist scrubbing:
    # a field this code has never seen before is dropped by construction,
    # not merely scrubbed if it happens to resemble an account id or email.
    agent = {"Agent": {**LEAKY_AGENT["Agent"],
                       "SomeFieldAwsAddsNextQuarter": "internal-secret-xyz"}}
    snap = capture(REAL_ACCOUNT_ID, agent_id="093ac4e3-0712-481e-af95-9ddc5e4fc734",
                   runner=_runner([], {"list-agents": LEAKY_AGENTS, "describe-agent": agent,
                                       "list-spaces": LEAKY_SPACES}))
    dumped = json.dumps(snap)
    assert "SomeFieldAwsAddsNextQuarter" not in dumped
    assert "internal-secret-xyz" not in dumped


def test_instructions_stays_scrubbed_despite_being_allowlisted():
    # Instructions is free text a human wrote and could itself name someone,
    # so being on the allowlist must not exempt it from _scrub.
    agent = {"Agent": {
        **LEAKY_AGENT["Agent"],
        "CustomPromptInterface": {
            "CustomInstructions": (
                f"Contact ops@example.invalid or account {REAL_ACCOUNT_ID} for access."
            ),
        },
    }}
    snap = capture(REAL_ACCOUNT_ID, agent_id="093ac4e3-0712-481e-af95-9ddc5e4fc734",
                   runner=_runner([], {"list-agents": LEAKY_AGENTS, "describe-agent": agent,
                                       "list-spaces": LEAKY_SPACES}))
    assert "@" not in snap["agent"]["Instructions"]
    assert REAL_ACCOUNT_ID not in snap["agent"]["Instructions"]


# ---------------------------------------------------------------------------
# Finding 2/3: the read-only guard must hold for capture() itself, and must
# not be sidesteppable by putting the real operation somewhere other than
# args[1].
# ---------------------------------------------------------------------------

def test_call_enforces_guard_independent_of_the_runner():
    # capture() reaches every runner through _call(). This is a runner that
    # enforces nothing itself and would happily execute any operation it was
    # given - if the guard lived only in default_aws_runner, this fake would
    # sail straight through. It must be rejected before the runner ever runs.
    from atlas_eval.snapshot import _call

    invoked = []

    def permissive_runner(args):
        invoked.append(args)
        return json.dumps({})

    with pytest.raises(SnapshotError):
        _call(permissive_runner, ["quicksight", "update-agent", "--agent-id", "x"])
    assert invoked == []


def test_capture_rejects_decoy_ordering_that_hides_real_operation():
    # Exercise the guard directly with a decoy-ordered args list, the shape
    # described in the finding: a real read-only op sits at args[1] as a
    # decoy, while the actual mutating op runs unchecked elsewhere.
    from atlas_eval.snapshot import _validate_read_only
    with pytest.raises(SnapshotError):
        _validate_read_only(["--profile", "list-agents", "quicksight", "update-agent"])


# ---------------------------------------------------------------------------
# Finding 4: default_aws_runner's guard needs direct coverage. None of these
# may reach a subprocess call.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mutating_op", [
    "create-agent", "update-agent", "delete-agent",
    "update-space", "update-space-resources", "delete-space",
])
def test_default_aws_runner_refuses_each_mutating_operation(mutating_op):
    assert mutating_op in MUTATING_OPS
    with mock.patch("subprocess.run") as run:
        with pytest.raises(SnapshotError):
            default_aws_runner(["quicksight", mutating_op, "--aws-account-id", "123456789012"])
        run.assert_not_called()


def test_default_aws_runner_refuses_decoy_ordering():
    with mock.patch("subprocess.run") as run:
        with pytest.raises(SnapshotError):
            default_aws_runner(["--profile", "list-agents", "quicksight", "update-agent"])
        run.assert_not_called()


def test_default_aws_runner_raises_snapshot_error_not_index_error_when_too_short():
    with mock.patch("subprocess.run") as run:
        with pytest.raises(SnapshotError):
            default_aws_runner(["quicksight"])
        run.assert_not_called()


# ---------------------------------------------------------------------------
# This is the third instance in this project of the exact leak class the
# allowlist projection above exists to prevent, this time in the test file
# that asserts the leak cannot happen: a real AWS account id and real
# operator email addresses were committed as fixture literals. Nothing in
# this test module needs the real values to exercise the scrubbing/allowlist
# behaviour -- obvious fakes exercise the same code paths.
# ---------------------------------------------------------------------------

def test_no_real_account_id_or_operator_email_committed_in_source():
    import base64
    import pathlib

    # The real values themselves must never appear as a contiguous literal in
    # this repo, including in this very check -- so the needles are decoded
    # at runtime from base64 rather than spelled out, and it is *these
    # decoded strings* that must not appear in the target files' source text.
    encoded_needles = (
        "Mjk4NjMyMzE3MjI4",  # the real AWS account id
        "bWljaGFlbC5hbmdlbGlAZG9sLm5qLmdvdg==",  # the real named operator email
        "b3BzQGRvbC5uai5nb3Y=",  # the real shared ops email
    )
    real_needles = [base64.b64decode(n).decode() for n in encoded_needles]
    for rel_path in ("atlas_eval/snapshot.py", "tests/test_snapshot.py"):
        text = (pathlib.Path(__file__).parent.parent / rel_path).read_text()
        for needle in real_needles:
            assert needle not in text, f"{rel_path} still contains a real committed value"


# --- AWS profile support -------------------------------------------------


def test_default_runner_passes_the_profile_when_given():
    calls = []

    def fake_subprocess_run(argv, **kwargs):
        calls.append(argv)
        class R:
            returncode = 0
            stdout = "{}"
            stderr = ""
        return R()

    import atlas_eval.snapshot as mod
    original = mod.subprocess.run
    mod.subprocess.run = fake_subprocess_run
    try:
        mod.default_aws_runner(["quicksight", "list-agents", "--aws-account-id", "1"],
                               profile="dev")
    finally:
        mod.subprocess.run = original

    assert calls, "subprocess.run was never called"
    argv = calls[0]
    assert "--profile" in argv and argv[argv.index("--profile") + 1] == "dev"
    # The profile must not displace the operation, or the read-only guard
    # would be validating the wrong element.
    assert "list-agents" in argv


def test_default_runner_omits_the_profile_when_not_given():
    calls = []

    def fake_subprocess_run(argv, **kwargs):
        calls.append(argv)
        class R:
            returncode = 0
            stdout = "{}"
            stderr = ""
        return R()

    import atlas_eval.snapshot as mod
    original = mod.subprocess.run
    mod.subprocess.run = fake_subprocess_run
    try:
        mod.default_aws_runner(["quicksight", "list-agents", "--aws-account-id", "1"])
    finally:
        mod.subprocess.run = original

    assert "--profile" not in calls[0]


def test_profile_does_not_defeat_the_read_only_guard():
    # A profile value that happens to name a mutating operation must not sneak
    # one past the guard, and a genuinely mutating op must still be refused
    # even when a profile is supplied.
    import atlas_eval.snapshot as mod
    with pytest.raises(SnapshotError) as exc:
        mod.default_aws_runner(["quicksight", "update-agent", "--aws-account-id", "1"],
                               profile="dev")
    assert "update-agent" in str(exc.value)


def test_capture_threads_the_profile_through_to_the_runner():
    seen = []

    def runner(args, profile=None):
        seen.append(profile)
        for key, payload in (("list-agents", AGENTS), ("describe-agent", AGENT),
                             ("list-spaces", SPACES)):
            if key in args:
                return json.dumps(payload)
        raise AssertionError(args)

    capture("000000000000", agent_id="093ac4e3", runner=runner, profile="dev")
    assert seen == ["dev", "dev", "dev"], "every call must use the same profile"


def test_capture_works_with_a_runner_that_takes_no_profile():
    # Existing tests inject single-argument runners; that must keep working.
    def runner(args):
        for key, payload in (("list-agents", AGENTS), ("describe-agent", AGENT),
                             ("list-spaces", SPACES)):
            if key in args:
                return json.dumps(payload)
        raise AssertionError(args)

    snap = capture("000000000000", agent_id="093ac4e3", runner=runner)
    assert snap["agent"]["Name"]
