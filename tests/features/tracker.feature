Feature: The GitHub tracker adapter

  @issue-9
  Scenario: Ready items come back oldest first
    Given issues #7 and #3 in state "Ready" on the board, #3 created first
    When the tracker lists Ready items
    Then it returns #3, then #7

  @issue-9
  Scenario: Items outside the configured repo are ignored
    Given a Ready item for issue #2 of another repository
    And a Ready draft item
    When the tracker lists Ready items
    Then neither is returned

  @issue-9
  Scenario: Setting a state moves the item on the board
    Given an issue #3 in state "Ready" on the board
    When the tracker sets #3 to In progress
    Then the board shows #3 in the option mapped to "in_progress"

  @issue-9 @issue-47
  Scenario: A gh failure surfaces with its details
    Given "api graphql" fails with exit 1 and stderr "HTTP 502" once
    When the tracker lists Ready items
    Then it raises a GhError holding exit 1 and "HTTP 502"

  @issue-9
  Scenario: A board with more items than one page is read in full
    Given 150 items on the board
    When the tracker lists all items
    Then it returns 150 items
