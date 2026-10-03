Feature: The engine makes only the moves in the transition table

  @issue-8
  Scenario Outline: Allowed moves
    Then <writer> may move an item from <from> to <to>

    Examples:
      | writer     | from        | to             |
      | admission  | Ready       | In progress    |
      | pr         | In progress | In review      |
      | any        | In progress | Parked         |
      | plan       | In progress | Needs decision |
      | reconciler | In review   | Done           |
      | reconciler | In review   | Parked         |

  @issue-8
  Scenario: The engine never moves an item back to Ready
    Then no engine writer may move an item from Parked to Ready
    And no engine writer may move an item from Needs decision to Ready

  @issue-8 @xfail-until-9
  Scenario: An illegal move changes nothing on the board
    Given an issue #4 in state "Parked" on the board
    When the PR station tries to move #4 to "In review"
    Then the move fails as illegal
    And the board still shows #4 in "Parked"
