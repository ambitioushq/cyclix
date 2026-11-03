Feature: Cyclix keeps its working state between passes

  Scenario: Two runs never hold the same issue
    Given one run holds issue #5
    When a second run tries to take issue #5
    Then the second run does not get issue #5
    And issue #5 stays with the first run

  Scenario: A state file from a newer Cyclix is refused
    Given the state file was written by a newer Cyclix, at schema version 99
    When one pass runs
    Then it exits 1
    And it logs "cyclix run: state.db is schema 99; this Cyclix reads up to 2"
