Feature: Each stage run writes one stage-run event to the event log

  Scenario: A stage that makes no agent call writes its event with the agent fields empty
    Given an issue #12 in state "Ready" on the board
    And the agent writes a plan, then commits a change
    And the gate's second command fails
    When one pass runs
    Then the event log holds one gate event for #12
    And the gate event records the outcome "parked" with the reason "gate command 2 exited 1"
    And the gate event's model, token and turn fields are empty

  Scenario: Every stage-run event carries the repository URL
    Given an issue #7 in state "Ready" on the board
    And the agent writes a plan, then commits a change
    When one pass runs
    Then every stage-run event for #7 records the tenant's repository URL

  Scenario: An agent's cost is written rounded
    Given the agent reports a cost of 0.36616580000000004
    And an issue #7 in state "Ready" on the board
    When one pass runs
    Then the plan event records a cost of 0.366166, rounded to six decimal places

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
    Then every stage-run event for #7 records the instruction folder's version

  Scenario: With no instruction folder the version is empty
    Given an issue #7 in state "Ready" on the board
    And the agent writes a plan, then commits a change
    When one pass runs
    Then every stage-run event for #7 has an empty instruction folder version
