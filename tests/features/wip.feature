@issue-44
Feature: WIP limits stop admission while a column is full

  Scenario: A full In review column stops admission
    Given the config sets a WIP limit of 2 on in_review
    And issues #1 and #2 in state "In review" on the board, each with an open PR
    And an issue #3 in state "Ready" on the board
    When one pass runs
    Then the board shows #3 in "Ready"
    And it prints "admission waits: In review holds 2 of its WIP limit of 2"

  Scenario: A merge in the same pass frees a place
    Given the config sets a WIP limit of 1 on in_review
    And an issue #1 in state "In review" on the board, with a merged PR
    And an issue #2 in state "Ready" on the board
    And the agent writes a plan, then commits a change
    When one pass runs
    Then the board shows #1 in "Done"
    And the board shows #2 in "In review"

  Scenario: Items a human moved count toward the limit
    Given the config sets a WIP limit of 1 on parked
    And an issue #1 in state "Parked" on the board
    And an issue #2 in state "Ready" on the board
    When one pass runs
    Then the board shows #2 in "Ready"
    And it prints "admission waits: Parked holds 1 of its WIP limit of 1"

  Scenario: A config without WIP limits admits as before
    Given the config has no WIP limits
    And issues #1 and #2 in state "In review" on the board, each with an open PR
    And an issue #3 in state "Ready" on the board
    And the agent writes a plan, then commits a change
    When one pass runs
    Then the board shows #3 in "In review"

  Scenario Outline: A WIP limit the engine cannot keep is refused
    Given the config's [limits.wip] holds <key> = <value>
    When I run "cyclix check"
    Then a line starts with "FAIL: config: [limits.wip]"

    Examples:
      | key         | value |
      | ready       | 3     |
      | done        | 3     |
      | in_progress | 2     |
      | in_review   | 0     |
      | in_review   | "5"   |
