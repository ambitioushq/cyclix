import re
import subprocess

from fakes.runner import environment
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("cli.feature")


@given("a valid tenant config")
def valid_config(world):
    pass


@given(parsers.parse('a valid tenant config mapping "{state}" to "{option}"'))
def config_mapping(world, state, option):
    text = world.config.read_text()
    text, count = re.subn(rf"(?m)^{state} = .*$", f'{state} = "{option}"', text)
    assert count == 1, f"no {state} mapping in the test config"
    world.config.write_text(text)


@given(parsers.parse('a valid tenant config whose agent command is "{command}"'))
def config_agent_command(world, command):
    text = world.config.read_text()
    world.config.write_text(text.replace('command = ["fake-agent"]', f'command = ["{command}"]'))


@given("a valid tenant config naming a missing instruction folder")
def config_missing_instructions(world):
    world.name_instructions(world.root / "no-such-folder")


@given("gh is signed in")
def gh_signed_in(world):
    world.set_logged_in(True)


@given("gh is not signed in")
def gh_not_signed_in(world):
    world.set_logged_in(False)


@given("the board has every configured Status option")
def board_has_every_option(world):
    pass


@given(parsers.parse('the board has no "{option}" option'))
def board_lacks_option(world, option):
    world.remove_option(option)


@when(parsers.parse('the shell asks cyclix to complete "{line}"'), target_fixture="completions")
def complete(world, tmp_path, line):
    """Run cyclix the way argcomplete's shell hook does, and return what it offers."""
    out = tmp_path / "completions"
    env = {
        **environment(world),
        "_ARGCOMPLETE": "1",
        "COMP_LINE": line,
        "COMP_POINT": str(len(line)),
        "_ARGCOMPLETE_STDOUT_FILENAME": str(out),
    }
    result = subprocess.run(["cyclix"], env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    # argcomplete separates the offers with a vertical tab, and ends a whole word with a space.
    return [offer.strip() for offer in out.read_text().split("\v")]


@then(parsers.parse('it offers "{word}"'))
def offers(completions, word):
    assert completions == [word]


@then(parsers.parse('every line ends in "{text}"'))
def every_line_ends_in(result, text):
    lines = result.stdout.splitlines()
    assert lines, result.stderr
    assert all(line.endswith(text) for line in lines), result.stdout


@then(parsers.parse('it reports "{failure}" with the fix "{fix}"'))
def reports_with_fix(world, result, failure, fix):
    """The failure line, then its fix line.

    <config> stands for the config file's path, and <world> for the world's folder.
    """
    failure = failure.replace('\\"', '"')
    failure = failure.replace("<world>", str(world.root))
    fix = fix.replace('\\"', '"').replace("<config>", str(world.config))
    lines = result.stdout.splitlines()
    assert failure in lines, result.stdout
    index = lines.index(failure)
    assert lines[index + 1 : index + 2] == [f"  fix: {fix}"], result.stdout


# The rules a ruleset adds to protect a branch, in the shape GitHub lists them.
RULESET = [
    {"type": kind, "ruleset_source_type": "Repository", "ruleset_source": "o/r", "ruleset_id": 2}
    for kind in ("pull_request", "non_fast_forward", "deletion")
]


def set_protection(world, protection=..., rules=...):
    data = world.load()
    if protection is not ...:
        data["protection"] = protection
    if rules is not ...:
        data["rules"] = rules
    world.save(data)


@given("the base branch has no protection")
def no_protection(world):
    set_protection(world, protection=None)


@given("the base branch allows force-pushes")
def allows_force_pushes(world):
    protection = world.load()["protection"]
    protection["allow_force_pushes"]["enabled"] = True
    set_protection(world, protection=protection)


@given("the base branch is protected by a ruleset alone")
def ruleset_alone(world):
    set_protection(world, protection=None, rules=RULESET)


@given("the base branch has no ruleset")
def no_ruleset(world):
    set_protection(world, rules=[])


@given("its branch protection settings cannot be read")
def protection_unreadable(world):
    world.add_fault(
        "api repos/o/r/branches/main/protection",
        stderr="gh: Upgrade to GitHub Pro or make this repository public to enable this feature. (HTTP 403)\n",
    )
