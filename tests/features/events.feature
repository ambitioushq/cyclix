Feature: Each stage run writes one event to the event log

  Scenario: A finished stage run writes one event with every key
    Given a stage run for #12 at stage "gate" ending "parked" with reason "gate command 2 exited 1"
    When its event is written
    Then the event log holds one line for #12
    And the line has schema "cyclix.event/1" and body "stage_run"
    And it has every stage-run key, with null for the model fields

  Scenario: Long text is refused
    Given a stage run whose reason is 2000 characters long
    When its event is written
    Then it fails with "event attribute cyclix.outcome.reason is too long"
    And the event log is unchanged

  Scenario: A key outside the schema is refused
    Given a stage run with the extra field "cyclix.prompt" = "plan the change"
    When its event is written
    Then it fails with "event attribute cyclix.prompt is not in schema cyclix.event/1"
    And the event log is unchanged

  Scenario: Each stage run is its own trace
    Given two stage runs for #12
    When both events are written
    Then the two lines have different trace IDs
    And both carry cyclix.issue.id 12

  Scenario: Every stage-run event carries the repository URL
    Given an issue #7 in state "Ready" on the board
    And the agent writes a plan, then commits a change
    When one pass runs
    Then every stage_run event for #7 has "vcs.repository.url.full" set to the tenant's repository URL

  Scenario: An agent's cost is written rounded
    Given the agent reports a cost of 0.36616580000000004
    And an issue #7 in state "Ready" on the board
    When one pass runs
    Then the plan event's "cyclix.cost.usd" is written with no more than the settled number of decimal places

  Scenario: The plan and build events record the agent's turns
    Given an issue #12 in state "Ready" on the board
    And the agent writes a plan in 7 turns, then commits a change in 12 turns
    When one pass runs
    Then the plan event records 7 agent turns
    And the build event records 12 agent turns

  Scenario: Every stage-run event records the instruction folder's version
    Given the config names an instruction folder holding "CLAUDE.md"
    And an issue #7 in state "Ready" on the board
    And the agent writes a plan, then commits a change
    When one pass runs
    Then every stage_run event for #7 has "cyclix.agent.instructions.version" set to the instruction folder's version

  Scenario: With no instruction folder the version is null
    Given an issue #7 in state "Ready" on the board
    And the agent writes a plan, then commits a change
    When one pass runs
    Then every stage_run event for #7 has "cyclix.agent.instructions.version" set to null
