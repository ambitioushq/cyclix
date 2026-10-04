@issue-47
Feature: The tracker reads the board cheaply

  Scenario: One pass reads the board once
    Given a board with issues #7 in state "Ready" and #8 in state "In progress"
    When one pass runs
    Then the board's items are read with one paged GraphQL query
    And no "gh project item-list" or "gh project field-list" call is made

  Scenario: A board larger than one page is read in full
    Given a board with 150 items
    When the tracker lists the board
    Then it reads two pages and returns all 150 items
