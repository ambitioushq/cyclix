from conftest import name_list
from pytest_bdd import given, parsers, scenarios, then

scenarios("stages.feature")

TENANT = "test"


# Given


@given("the agent writes a plan, then answers without committing")
def plan_then_no_commit(world):
    world.add_agent_step(answer="## Approach\nChange one file.\n")
    world.add_agent_step(answer="done")


@given(parsers.parse('the gate command is "{command}"'))
def gate_command_is(world, command):
    world.set_gate_commands(command.split())


# Then


@then(parsers.parse('the {stage} event\'s outcome is "{outcome}" with that reason'))
def outcome_with_reason(world, result, stage, outcome):
    [answer] = [step["answer"] for step in world.agent_script()]
    found = [
        (e["attributes"]["cyclix.outcome"], e["attributes"]["cyclix.outcome.reason"])
        for e in world.events()
        if e["attributes"]["cyclix.stage"] == stage
    ]
    assert found == [(outcome, answer.removeprefix("STOP:").strip())], result.stderr


@then(parsers.parse("issue #{issue:d} is parked"))
def is_parked(world, issue):
    assert world.board_state(issue) == "Parked"


def gate_output(world, issue):
    [path] = (world.state_dir / "runs" / TENANT / str(issue)).glob("*/gate-1.txt")
    return path.read_text().splitlines()


@then(parsers.parse("the gate output for #{issue:d} holds neither {names}"))
def gate_output_lacks(world, result, issue, names):
    lines = gate_output(world, issue)
    for name in name_list(names):
        assert not any(line.startswith(f"{name}=") for line in lines), name


@then(parsers.parse('the gate output for #{issue:d} holds "{line}"'))
def gate_output_holds(world, issue, line):
    assert line in gate_output(world, issue)


@then(parsers.parse('the build prompt lists "{line}"'))
def build_prompt_lists(world, result, line):
    assert line in world.prompts()[1].splitlines()


@then("the build prompt says to run each shell command on its own")
def build_prompt_one_command(world):
    assert "Run each shell command on its own." in world.prompts()[1]
