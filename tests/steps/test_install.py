import json
import re
import shlex

from fakes.runner import run_cyclix
from pytest_bdd import given, parsers, scenarios, then

scenarios("install.feature")

DIFFERENT_UNIT = "[Service]\nExecStart=/somewhere/else run --once\n"


@given(parsers.parse('a valid tenant config for "{tenant}"'))
def config_for_tenant(world, tenant):
    text, count = re.subn(r'(?m)^name = ".*"$', f'name = "{tenant}"', world.config.read_text())
    assert count == 1, "no tenant name in the test config"
    world.config.write_text(text)


@given(parsers.parse('a unit "{name}" that differs from the one Cyclix would write'))
def different_unit(world, name):
    world.units_dir.mkdir(parents=True, exist_ok=True)
    (world.units_dir / name).write_text(DIFFERENT_UNIT)


@given(parsers.parse('the loop is installed for "{tenant}"'))
def installed(world, tenant):
    result = run_cyclix(world, "install", "--tenant", tenant)
    assert result.returncode == 0, result.stdout + result.stderr


@then(parsers.parse('it prints a service with "{key}" ending in "{ending}"'))
def prints_service_line(result, key, ending):
    lines = [line for line in result.stdout.splitlines() if line.startswith(key)]
    assert any(line.endswith(ending) for line in lines), result.stdout


@then(parsers.parse('it prints a timer with "{line}"'))
def prints_timer_line(result, line):
    assert line in result.stdout.splitlines(), result.stdout


@then("no file is written")
@then("no unit file is left")
def no_unit_files(world):
    assert not world.units_dir.exists() or not list(world.units_dir.iterdir())


@then("it prints the difference")
def prints_difference(result):
    lines = result.stdout.splitlines()
    assert "-ExecStart=/somewhere/else run --once" in lines, result.stdout
    assert any(line.startswith("+ExecStart=") for line in lines), result.stdout


@then("the unit is unchanged")
def unit_unchanged(world):
    assert (world.units_dir / "cyclix-cyclix.service").read_text() == DIFFERENT_UNIT


@then(parsers.parse('the unit "{name}" holds "{line}"'))
def unit_holds(world, name, line):
    text = (world.units_dir / name).read_text()
    assert line in text.splitlines(), text


@then(parsers.parse('the unit "{name}" holds the config\'s absolute path'))
def unit_holds_config(world, name):
    text = (world.units_dir / name).read_text()
    assert f"Environment=CYCLIX_CONFIG={world.config}" in text.splitlines(), text


@then(parsers.parse('systemctl was called with "{args}"'))
def systemctl_called(world, args):
    lines = world.systemctl_path.read_text().splitlines() if world.systemctl_path.exists() else []
    calls = [json.loads(line)["argv"] for line in lines]
    assert shlex.split(args) in calls, calls
