Feature: The state core keeps the loop's working state

  @issue-7
  Scenario: An issue can be claimed once
    Given an empty state core
    When run "r1" claims #5
    And run "r2" claims #5
    Then the first claim succeeds
    And the second claim fails

  @issue-7
  Scenario: A run's fields build up and come back at the end
    Given run "r1" has begun for #5 at stage "build"
    When the fields "cyclix.round" = 1 and "cyclix.cost.usd" = 0.4 are added
    And the run ends with outcome "passed"
    Then the returned fields hold the round, the cost and the outcome

  @issue-7
  Scenario: An unfinished run is reported as open
    Given run "r1" has begun and not ended
    When open runs are listed
    Then "r1" is listed with its last phase

  @issue-7
  Scenario: The best verified commit is the last one whose checks all passed
    Given checks recorded for #5: sha "a" all passed, then sha "b" with one failed
    When the best verified commit for #5 is read
    Then it is "a"

  @issue-7
  Scenario: A newer schema is refused
    Given a state file at schema version 99
    When the state core opens it
    Then it fails with "state.db is schema 99; this Cyclix reads up to 1"
