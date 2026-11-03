import hashlib
from decimal import Decimal

from fakes.world import PLAN_ANSWER, PR_BODY_ANSWER, REPO
from pytest_bdd import given, parsers, scenarios, then

from cyclix.events import schema

scenarios("stage_run_events.feature")


def stage_events(world, result, stage):
    """The attributes of each event at the stage, failing with the pass's output if there is none."""
    found = [e["attributes"] for e in world.events() if e["attributes"][schema.STAGE] == stage]
    assert found, result.stdout + result.stderr
    return found


def issue_events(world, result, issue):
    """The attributes of each event for the issue, failing with the pass's output if there is none."""
    found = [e["attributes"] for e in world.events() if e["attributes"][schema.ISSUE_ID] == issue]
    assert found, result.stdout + result.stderr
    return found


# Given


@given(parsers.parse("the agent reports a cost of {cost}"))
def agent_reports_cost(world, cost):
    world.add_agent_step(answer="## Approach\nChange one file.\n", cost_usd=float(cost))
    world.add_agent_step(
        files={"change.txt": "a change\n"}, commit=True, answer="done", cost_usd=float(cost)
    )


@given(
    parsers.parse(
        "the agent writes a plan in {plan_turns:d} turns, "
        "then commits a change in {build_turns:d} turns"
    )
)
def plan_and_build_in_turns(world, plan_turns, build_turns):
    world.add_agent_step(answer=PLAN_ANSWER, num_turns=plan_turns)
    world.add_agent_step(
        files={"change.txt": "a change\n"}, commit=True, answer=PR_BODY_ANSWER,
        num_turns=build_turns,
    )  # fmt: skip


@given("the gate's second command fails")
def gate_fails_second(world):
    world.set_gate_commands(["true"], ["false"])


# Then


@then(parsers.parse("the event log holds one {stage} event for #{issue:d}"))
def one_stage_event(world, result, stage, issue):
    found = stage_events(world, result, stage)
    assert [a[schema.ISSUE_ID] for a in found] == [issue], found


@then(parsers.parse('the {stage} event records the outcome "{outcome}" with the reason "{reason}"'))
def stage_event_outcome(world, result, stage, outcome, reason):
    [event] = stage_events(world, result, stage)
    assert (event[schema.OUTCOME], event[schema.OUTCOME_REASON]) == (outcome, reason), event


@then(parsers.parse("the {stage} event's model, token and turn fields are empty"))
def agent_fields_empty(world, result, stage):
    [event] = stage_events(world, result, stage)
    agent_keys = (schema.MODEL, schema.INPUT_TOKENS, schema.OUTPUT_TOKENS, schema.AGENT_TURNS)
    assert {key: event[key] for key in agent_keys} == dict.fromkeys(agent_keys), event


@then(parsers.parse("every stage-run event for #{issue:d} records the tenant's repository URL"))
def events_carry_repository_url(world, result, issue):
    found = issue_events(world, result, issue)
    assert [a.get(schema.REPOSITORY_URL) for a in found] == [f"https://github.com/{REPO}"] * len(
        found
    )


@then(parsers.parse("the plan event records a cost of {cost}, rounded to six decimal places"))
def plan_cost_is_rounded(world, result, cost):
    [plan] = stage_events(world, result, "plan")
    written = plan[schema.COST_USD]
    assert Decimal(repr(written)).as_tuple().exponent >= -6, written
    assert written == float(cost)


@then(parsers.parse("the {stage} event records {turns:d} agent turns"))
def event_records_turns(world, result, stage, turns):
    [event] = stage_events(world, result, stage)
    assert event[schema.AGENT_TURNS] == turns


def folder_version(folder):
    """The rule in docs/src/content/docs/design/engine.md: each file's relative path, its length and its content."""
    digest = hashlib.sha256()
    for path in sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()):
        content = (folder / path).read_bytes()
        digest.update(f"{path}\0{len(content)}\0".encode() + content)
    return "sha256:" + digest.hexdigest()


@then(
    parsers.parse("every stage-run event for #{issue:d} records the instruction folder's version")
)
def events_carry_instructions_version(world, result, issue):
    found = issue_events(world, result, issue)
    expected = [folder_version(world.instructions)] * len(found)
    assert [a.get(schema.INSTRUCTIONS_VERSION) for a in found] == expected


@then(parsers.parse("every stage-run event for #{issue:d} has an empty instruction folder version"))
def events_have_no_instructions_version(world, result, issue):
    found = issue_events(world, result, issue)
    assert all(
        schema.INSTRUCTIONS_VERSION in a and a[schema.INSTRUCTIONS_VERSION] is None for a in found
    ), found
