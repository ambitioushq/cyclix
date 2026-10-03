import re

from pytest_bdd import given, parsers, scenarios, then

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


@then(parsers.parse('every line ends in "{text}"'))
def every_line_ends_in(result, text):
    lines = result.stdout.splitlines()
    assert lines, result.stderr
    assert all(line.endswith(text) for line in lines), result.stdout
