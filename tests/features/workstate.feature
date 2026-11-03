Feature: Cyclix moves a board item only in the ways its work states allow

  Scenario Outline: A pass does not pick up an item that waits for a person
    Given an issue #4 in state "<state>" on the board
    When one pass runs
    Then the board shows #4 in "<state>"
    And no stage runs for #4

    Examples:
      | state          |
      | Parked         |
      | Needs decision |

  Scenario: A move the work states do not allow leaves the item where it is
    Given an issue #4 in state "Parked" on the board
    When the PR stage tries to move #4 to "In review"
    Then the move is refused
    And the board still shows #4 in "Parked"
