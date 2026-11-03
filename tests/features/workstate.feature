Feature: The engine makes only the moves in the transition table

  Scenario Outline: Allowed moves
    Then <mover> may move an item from <from> to <to>

    Examples:
      | mover      | from        | to             |
      | admission  | Ready       | In progress    |
      | pr         | In progress | In review      |
      | admission  | In progress | Parked         |
      | plan       | In progress | Parked         |
      | build      | In progress | Parked         |
      | gate       | In progress | Parked         |
      | pr         | In progress | Parked         |
      | reconciler | In progress | Parked         |
      | plan       | In progress | Needs decision |
      | reconciler | In review   | Done           |
      | reconciler | In review   | Parked         |

  Scenario: The engine never moves an item back to Ready
    Then no engine mover may move an item from Parked to Ready
    And no engine mover may move an item from Needs decision to Ready

  Scenario: An illegal move changes nothing on the board
    Given an issue #4 in state "Parked" on the board
    When the PR stage tries to move #4 to "In review"
    Then the move fails as illegal
    And the board still shows #4 in "Parked"
