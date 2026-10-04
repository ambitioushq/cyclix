Feature: The fakes behave like the real tools for the commands Cyclix uses

  @issue-4 @issue-47
  Scenario: The fake gh lists board items from the world
    Given an issue #3 titled "Add a thing" in state "Ready" on the board
    When the fake gh lists the board through the BoardItems query
    Then the output lists one item for #3 with status "Ready"
    And the call is recorded

  @issue-4
  Scenario: The fake gh moves an item
    Given an issue #3 in state "Ready" on the board
    When the fake gh runs "project item-edit" setting #3 to the "In progress" option
    Then the board shows #3 in "In progress"

  @issue-4
  Scenario: An injected fault fails one call
    Given "pr create" fails with exit 1 and stderr "HTTP 502" once
    When the fake gh runs "pr create" twice
    Then the first call exits 1 with "HTTP 502"
    And the second call succeeds

  @issue-4
  Scenario: The fake gh refuses a command it does not support
    When the fake gh runs "repo delete o/r"
    Then it exits 2

  @issue-4
  Scenario: A scenario without an issue tag fails the suite
    Given a feature file with a scenario that has no @issue tag
    When the tag check runs
    Then it fails and names the scenario

  @issue-4
  Scenario: The fake agent follows its script
    Given the agent script writes "a.txt", commits it, and answers "done"
    When the fake agent runs in a git worktree
    Then "a.txt" is committed
    And the output is JSON with result "done" and the scripted usage numbers
