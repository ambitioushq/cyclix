Feature: Each issue gets one PR, and merging or closing it moves the item to Done or Parked

  Scenario: The PR title is the issue title
    Given an issue #7 in state "Ready" on the board
    And the agent writes a plan, then commits a change
    When one pass runs
    Then the PR for #7 is titled with the issue's title and no issue number

  Scenario: The PR body follows the PR template
    Given an issue #7 in state "Ready" on the board
    And the agent writes a plan, then commits a change
    When one pass runs
    Then the PR body for #7 starts with "Closes #7"
    And it has each section of the PR template
    And it does not contain the plan

  Scenario: A crash after the PR opened does not open a second PR
    Given a run for #12 crashed in phase "open_pr" after the PR was created
    And a human moves #12 back to "Ready"
    And the agent writes a plan, then commits a change
    When one pass runs
    Then exactly one PR exists for #12's branch

  Scenario: A merged PR moves its item to Done
    Given issue #12 is In review with PR #20
    And PR #20 is merged
    When one pass runs
    Then the board shows #12 in "Done"
    And the worktree for #12 is removed

  Scenario: A PR closed without merging parks its item
    Given issue #12 is In review with PR #20
    And PR #20 is closed without merging
    When one pass runs
    Then the board shows #12 in "Parked"
