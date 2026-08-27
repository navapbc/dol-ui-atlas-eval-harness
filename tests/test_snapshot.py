import json

import pytest

from atlas_eval.snapshot import SnapshotError, capture

AGENTS = {"AgentSummaryList": [
    {"AgentId": "093ac4e3-0712-481e-af95-9ddc5e4fc734",
     "Name": "Engineering Onboarding Specialist"},
    {"AgentId": "aaaaaaaa-0000-0000-0000-000000000000", "Name": "Other Agent"},
]}
AGENT = {"Agent": {"AgentId": "093ac4e3-0712-481e-af95-9ddc5e4fc734",
                   "Name": "Engineering Onboarding Specialist",
                   "Instructions": "you are an onboarding specialist"}}
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
    assert "aws" in str(exc.value)


def test_bad_json_surfaces_as_snapshot_error():
    with pytest.raises(SnapshotError):
        capture("123456789012", agent_id="x", runner=lambda args: "not json")
