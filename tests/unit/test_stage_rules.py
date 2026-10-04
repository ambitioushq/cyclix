"""Rules of the minimal stages that stages.feature and sweep.feature do not check.

The sweep runs in-process against the fake world, with the real stages.
"""

import re

import pytest
from fakes.world import PR_BODY_ANSWER, PR_TEMPLATE, TEMPLATE_PATH, git

from cyclix import config, runner
from cyclix.stages.pr import ensure_closes
from cyclix.state.core import RunStart
from cyclix.state.sqlite import SqliteStateCore

TENANT = "test"


@pytest.fixture
def core(world):
    core = SqliteStateCore(world.state_dir)
    yield core
    core.close()


def sweep(world):
    return runner.sweep(config.load(world.config))


def events(world, issue):
    return [e["attributes"] for e in world.events() if e["attributes"]["cyclix.issue.id"] == issue]


def set_gate(world, commands):
    listed = ", ".join("[" + ", ".join(f'"{word}"' for word in c) + "]" for c in commands)
    text = re.sub(r"(?m)^commands = .*$", f"commands = [{listed}]", world.config.read_text())
    world.config.write_text(text)


def run_dir(world, issue):
    [run] = (world.state_dir / "runs" / TENANT / str(issue)).iterdir()
    return run


def test_the_pr_has_the_issue_title_and_the_build_answer_as_its_body(world):
    world.add_issue(12, title="Add the gate", state="Ready")
    world.add_plan_and_commit()
    assert sweep(world) == 0
    [pr] = world.prs_for(12)
    assert pr["title"] == "Add the gate"
    assert pr["head"] == "cyclix/12-add-the-gate"
    assert pr["body"] == "Closes #12\n\n" + PR_BODY_ANSWER.strip() + "\n"
    assert "## Approach" not in pr["body"]
    assert (run_dir(world, 12) / "pr.md").read_text() == PR_BODY_ANSWER.strip() + "\n"
    assert (run_dir(world, 12) / "plan.md").read_text() == "## Approach\nChange one file.\n"
    assert world.comments(12) == [f"In review: https://github.com/o/r/pull/{pr['number']}"]
    by_stage = {e["cyclix.stage"]: e for e in events(world, 12)}
    assert by_stage["pr"]["vcs.change.id"] == str(pr["number"])
    assert by_stage["adversarial_review"]["cyclix.outcome"] == "skipped"
    assert by_stage["plan"]["gen_ai.request.model"] == "claude-sonnet-5-5"
    assert by_stage["plan"]["gen_ai.usage.input_tokens"] == 1000


def test_the_plan_prompt_holds_the_issue_and_the_build_prompt_holds_the_plan(world):
    world.add_issue(12, title="Add the gate", state="Ready", body="Run each command.")
    world.add_plan_and_commit()
    sweep(world)
    plan_prompt, build_prompt = world.prompts()
    assert "Issue #12: Add the gate\n\nRun each command." in plan_prompt
    assert "## Approach\nChange one file." in build_prompt


def test_the_build_prompt_holds_the_template_of_the_tenant_repository(world):
    world.add_issue(12, state="Ready")
    world.add_plan_and_commit()
    sweep(world)
    _, build_prompt = world.prompts()
    assert PR_TEMPLATE in build_prompt
    assert "Closes #12` on its first line" in build_prompt
    assert "word for word" in build_prompt


def test_without_a_template_the_build_prompt_asks_for_closes_and_a_summary(world, tmp_path):
    clone = tmp_path / "clone"
    git(tmp_path, "clone", "-q", str(world.remote), str(clone))
    git(clone, "rm", "-q", TEMPLATE_PATH)
    git(clone, "commit", "-q", "-m", "Drop the template")
    git(clone, "push", "-q", "origin", "HEAD:main")
    world.add_issue(12, state="Ready")
    world.add_plan_and_commit()
    sweep(world)
    _, build_prompt = world.prompts()
    assert "## What changed" not in build_prompt
    assert "Start it with `Closes #12` on its first line" in build_prompt
    assert "short plain summary" in build_prompt


def test_a_body_that_starts_with_closes_is_not_given_a_second_line():
    assert ensure_closes("Closes #12\n\n## What changed\nA gate.\n", 12) == (
        "Closes #12\n\n## What changed\nA gate.\n"
    )
    assert ensure_closes("\n\nCloses #12\nMore.", 12) == "Closes #12\nMore.\n"
    assert ensure_closes("Closes #120\n", 12) == "Closes #12\n\nCloses #120\n"


def test_an_empty_build_answer_gives_a_body_of_closes_alone(world):
    world.add_issue(12, state="Ready")
    world.add_agent_step(answer="## Approach\nChange one file.\n")
    world.add_agent_step(files={"change.txt": "a change\n"}, commit=True, answer="")
    sweep(world)
    [pr] = world.prs_for(12)
    assert pr["body"] == "Closes #12\n"


def test_the_gate_records_each_check_against_the_head_and_saves_its_output(world, core):
    world.add_issue(12, state="Ready")
    world.add_plan_and_commit()
    set_gate(world, [["echo", "first"], ["false"], ["echo", "never"]])
    sweep(world)
    gate = events(world, 12)[-1]
    assert gate["cyclix.outcome.reason"] == "gate command 2 exited 1"
    checks = [(c["name"], c["passed"]) for c in gate["cyclix.gate.checks"]]
    assert checks == [("echo first", True), ("false", False)]
    folder = run_dir(world, 12)
    assert (folder / "gate-1.txt").read_text() == "first\n"
    assert not (folder / "gate-3.txt").exists()
    assert core.best_verified(TENANT, 12) is None


def test_a_gate_command_that_is_not_found_exits_127(world):
    world.add_issue(12, state="Ready")
    world.add_plan_and_commit()
    set_gate(world, [["no-such-command-anywhere"]])
    sweep(world)
    assert events(world, 12)[-1]["cyclix.outcome.reason"] == "gate command 1 exited 127"


def test_a_passing_gate_makes_the_head_the_best_verified_commit(world, core):
    world.add_issue(12, state="Ready")
    world.add_plan_and_commit()
    sweep(world)
    gate = next(e for e in events(world, 12) if e["cyclix.stage"] == "gate")
    assert core.best_verified(TENANT, 12) == gate["vcs.ref.head.revision"]


def test_a_failed_agent_call_fails_the_plan(world):
    world.add_issue(12, state="Ready")
    world.add_agent_step(answer="overloaded", exit=1)
    sweep(world)
    plan = events(world, 12)[-1]
    assert (plan["cyclix.outcome"], plan["cyclix.outcome.reason"]) == (
        "failed",
        "agent: overloaded",
    )
    assert world.board_state(12) == "Parked"


def test_an_open_pr_leaves_its_item_in_review_and_writes_no_event(world, core):
    world.add_issue(12, state="In review")
    world.add_pr(12)
    core.claim(TENANT, 12, "r-earlier")
    assert sweep(world) == 0
    assert world.board_state(12) == "In review"
    assert events(world, 12) == []
    assert [c.issue for c in core.claims(TENANT)] == [12]


def test_the_reconciler_writes_under_the_claim_and_comments_only_when_parking(world, core):
    world.add_issue(12, state="In review")
    world.add_issue(13, state="In review")
    world.add_pr(12, state="MERGED", merged_at="2026-10-01T12:00:00Z")
    world.add_pr(13, state="CLOSED")
    core.claim(TENANT, 12, "r-earlier")
    sweep(world)
    [merged] = events(world, 12)
    assert (merged["cyclix.stage"], merged["cyclix.run.id"]) == ("reconciler", "r-earlier")
    assert merged["cyclix.outcome.reason"] == "PR merged"
    [closed] = events(world, 13)
    assert closed["cyclix.outcome.reason"] == "PR closed without merge"
    assert world.comments(12) == []
    assert world.comments(13) == ["Parked: PR closed without merge"]
    assert core.claims(TENANT) == []


def test_a_failed_reconciler_releases_the_claim_and_tries_again_next_pass(world, core):
    world.add_issue(12, state="In review")
    world.add_pr(12, state="MERGED", merged_at="2026-10-01T12:00:00Z")
    core.claim(TENANT, 12, "r-earlier")
    core.begin_run(RunStart(run_id="r-earlier", tenant=TENANT, issue=12, stage="pr"))
    core.end_run("r-earlier", "passed", "")
    world.add_fault("project item-edit", exit=1, stderr="HTTP 502")
    assert sweep(world) == 0
    assert [e["cyclix.outcome"] for e in events(world, 12)] == ["failed"]
    assert core.claims(TENANT) == []
    assert sweep(world) == 0
    assert world.board_state(12) == "Done"
    assert events(world, 12)[-1]["cyclix.outcome"] == "passed"
