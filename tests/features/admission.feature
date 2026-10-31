Feature: Admission takes a Ready issue from the board when there is room

  Scenario: Admission ignores issues that are not on the board
    Given an open #30 with no board item
    And an issue #12 in state "Ready" on the board
    When one pass runs
    Then issue #12 is admitted
    And issue #30 is never read

  Scenario: Admission never reads comments
    Given an issue #12 in state "Ready" on the board with a comment from a non-maintainer
    When one pass runs
    Then no gh call reads #12's comments

  Scenario: Only one item is In progress at a time
    Given issue #12 is In progress and issue #13 is Ready
    When one pass runs
    Then issue #13 stays in "Ready"

  Scenario: A full In review column stops admission
    Given the config sets a WIP limit of 2 on in_review
    And issues #1 and #2 in state "In review" on the board, each with an open PR
    And an issue #3 in state "Ready" on the board
    When one pass runs
    Then the board shows #3 in "Ready"
    And it logs "admission waits: In review holds 2 of its WIP limit of 2"

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
    And it logs "admission waits: Parked holds 1 of its WIP limit of 1"

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

  Scenario: The instruction files are copied into the run's worktree
    Given the config names an instruction folder holding "CLAUDE.md" and "docs/CLAUDE.md"
    And an issue #12 in state "Ready" on the board
    And the agent writes a plan, then commits a change
    When one pass runs
    Then the worktree for #12 holds "CLAUDE.md" and "docs/CLAUDE.md" as copies of the folder's files

  Scenario: A symlink in the instruction folder is copied as its content
    Given the config names an instruction folder whose "CLAUDE.md" is a symlink to a file outside it
    And an issue #12 in state "Ready" on the board
    And the agent writes a plan, then commits a change
    When one pass runs
    Then the worktree for #12 holds "CLAUDE.md" as copies of the folder's files

  Scenario: A commit the agent makes leaves the instruction files out
    Given the config names an instruction folder holding "CLAUDE.md"
    And an issue #12 in state "Ready" on the board
    And the agent writes a plan, then stages every file and commits a change
    When one pass runs
    Then the branch pushed for #12 holds "change.txt" and not "CLAUDE.md"

  Scenario: An instruction file the repository tracks parks the item
    Given the repository tracks "CLAUDE.md"
    And the config names an instruction folder holding "CLAUDE.md"
    And an issue #12 in state "Ready" on the board
    When one pass runs
    Then the board shows #12 in "Parked"
    And the admission event's outcome is "parked"
    And the admission event's reason is "the repository tracks CLAUDE.md, which the instruction folder also holds"
    And the agent was never called
