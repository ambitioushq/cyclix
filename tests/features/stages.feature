Feature: The minimal stages

  @issue-14
  Scenario: A plan that starts with STOP parks the item with its reason
    Given an issue #12 in state "Ready" on the board
    And the agent answers "STOP: the issue does not say which file to change"
    When one pass runs
    Then the board shows #12 in "Parked"
    And the plan event's outcome is "stopped" with that reason

  @issue-14
  Scenario: A build with no commit fails
    Given an issue #12 in state "Ready" on the board
    And the agent writes a plan, then answers without committing
    When one pass runs
    Then the build event's outcome is "failed"
    And issue #12 is parked

  @issue-14
  Scenario: Admission ignores issues that are not on the board
    Given an open #30 with no board item
    And an issue #12 in state "Ready" on the board
    When one pass runs
    Then issue #12 is admitted
    And issue #30 is never read

  @issue-14
  Scenario: Admission never reads comments
    Given an issue #12 in state "Ready" on the board with a comment from a non-maintainer
    When one pass runs
    Then no gh call reads #12's comments

  @issue-14
  Scenario: A merged PR moves its item to Done
    Given issue #12 is In review with PR #20
    And PR #20 is merged
    When one pass runs
    Then the board shows #12 in "Done"
    And the worktree for #12 is removed

  @issue-14
  Scenario: A PR closed without merging parks its item
    Given issue #12 is In review with PR #20
    And PR #20 is closed without merging
    When one pass runs
    Then the board shows #12 in "Parked"

  @issue-14
  Scenario: A crash after the PR opened does not open a second PR
    Given a run for #12 crashed in phase "open_pr" after the PR was created
    And a human moves #12 back to "Ready"
    And the agent writes a plan, then commits a change
    When one pass runs
    Then exactly one PR exists for #12's branch

  @issue-50
  Scenario: The PR title is the issue title
    Given an issue #7 in state "Ready" on the board
    And the agent writes a plan, then commits a change
    When one pass runs
    Then the PR for #7 is titled with the issue's title and no issue number

  @issue-50
  Scenario: The PR body follows the PR template
    Given an issue #7 in state "Ready" on the board
    And the agent writes a plan, then commits a change
    When one pass runs
    Then the PR body for #7 starts with "Closes #7"
    And it has each section of the PR template
    And it does not contain the plan

  @issue-55
  Scenario: The gate sees neither the GitHub token nor the Claude login
    Given an issue #12 in state "Ready" on the board
    And the agent writes a plan, then commits a change
    And the gate command is "env"
    And the engine's environment holds GH_TOKEN, CLAUDE_CODE_OAUTH_TOKEN and CLAUDE_CONFIG_DIR
    When one pass runs
    Then the gate output for #12 holds neither GH_TOKEN, CLAUDE_CODE_OAUTH_TOKEN nor CLAUDE_CONFIG_DIR
    And the gate output for #12 holds "GIT_TERMINAL_PROMPT=0"

  @issue-55
  Scenario: The plan and build events record the agent's turns
    Given an issue #12 in state "Ready" on the board
    And the agent writes a plan in 7 turns, then commits a change in 12 turns
    When one pass runs
    Then the plan event records 7 agent turns
    And the build event records 12 agent turns

  @issue-55
  Scenario: The build prompt lists the commands the agent may run
    Given an issue #12 in state "Ready" on the board
    And the agent writes a plan, then commits a change
    When one pass runs
    Then the build prompt lists "- Bash(git commit *)"
    And the build prompt says to run each shell command on its own
