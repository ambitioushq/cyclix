Feature: The plan, build and gate stages do the work on the issue

  Scenario: A plan that starts with STOP parks the item with its reason
    Given an issue #12 in state "Ready" on the board
    And the agent answers "STOP: the issue does not say which file to change"
    When one pass runs
    Then the board shows #12 in "Parked"
    And the plan event's outcome is "stopped" with that reason

  Scenario: A build with no commit fails
    Given an issue #12 in state "Ready" on the board
    And the agent writes a plan, then answers without committing
    When one pass runs
    Then the build event's outcome is "failed"
    And issue #12 is parked

  Scenario: The gate sees neither the GitHub token nor the Claude login
    Given an issue #12 in state "Ready" on the board
    And the agent writes a plan, then commits a change
    And the gate command is "env"
    And the engine's environment holds GH_TOKEN, CLAUDE_CODE_OAUTH_TOKEN and CLAUDE_CONFIG_DIR
    When one pass runs
    Then the gate output for #12 holds neither GH_TOKEN, CLAUDE_CODE_OAUTH_TOKEN nor CLAUDE_CONFIG_DIR
    And the gate output for #12 holds "GIT_TERMINAL_PROMPT=0"

  Scenario: The build prompt lists the commands the agent may run
    Given an issue #12 in state "Ready" on the board
    And the agent writes a plan, then commits a change
    When one pass runs
    Then the build prompt lists "- Bash(git commit *)"
    And the build prompt says to run each shell command on its own
