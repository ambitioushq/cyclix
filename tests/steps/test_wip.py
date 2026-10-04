from pytest_bdd import given, parsers, scenarios, then

scenarios("wip.feature")


def add_wip(world, line):
    """Add a [limits.wip] table, after [limits], which is the test config's last table."""
    world.config.write_text(world.config.read_text() + f"\n[limits.wip]\n{line}\n")


# Given


@given(parsers.parse("the config sets a WIP limit of {limit:d} on {state}"))
def wip_limit(world, limit, state):
    add_wip(world, f"{state} = {limit}")


@given(parsers.parse("the config's [limits.wip] holds {key} = {value}"))
def wip_line(world, key, value):
    add_wip(world, f"{key} = {value}")


@given("the config has no WIP limits")
def no_wip(world):
    assert "[limits.wip]" not in world.config.read_text()


@given(
    parsers.parse(
        'issues #{first:d} and #{second:d} in state "{state}" on the board, each with an open PR'
    )
)
def issues_with_open_prs(world, first, second, state):
    for number in (first, second):
        world.add_issue(number, state=state)
        world.add_pr(number)


@given(parsers.parse('an issue #{number:d} in state "{state}" on the board, with a merged PR'))
def issue_with_merged_pr(world, number, state):
    world.add_issue(number, state=state)
    world.add_pr(number, state="MERGED", merged_at="2026-10-04T00:00:00Z")


# Then


@then(parsers.parse('a line starts with "{text}"'))
def line_starts_with(result, text):
    assert any(line.startswith(text) for line in result.stdout.splitlines()), result.stdout
