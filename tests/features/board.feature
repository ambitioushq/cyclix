Feature: Cyclix reads and moves items on the GitHub board

  Scenario: Ready items come back oldest first
    Given issues #7 and #3 in state "Ready" on the board, #3 created first
    When the tracker lists Ready items
    Then it returns #3, then #7

  Scenario: Items outside the configured repo are ignored
    Given a Ready item for issue #2 of another repository
    And a Ready draft item
    When the tracker lists Ready items
    Then neither is returned

  Scenario: Setting a state moves the item on the board
    Given an issue #3 in state "Ready" on the board
    When the tracker sets #3 to In progress
    Then the board shows #3 in the option mapped to "in_progress"

  Scenario: A gh failure surfaces with its details
    Given "api graphql" fails with exit 1 and stderr "HTTP 502" once
    When the tracker lists Ready items
    Then it raises a GhError holding exit 1 and "HTTP 502"

  Scenario: One pass reads the board once
    Given a board with issues #7 in state "Ready" and #8 in state "In progress"
    When one pass runs
    Then the board's items are read with one paged GraphQL query
    And no "gh project item-list" or "gh project field-list" call is made

  Scenario: A board larger than one page is read in full
    Given a board with 150 items
    When the tracker lists the board
    Then it reads two pages and returns all 150 items
