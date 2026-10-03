Feature: The cyclix command

  @issue-5
  Scenario: check passes when everything is in place
    Given a valid tenant config
    And gh is signed in
    And the board has every configured Status option
    When I run "cyclix check"
    Then it exits 0
    And every line ends in "ok"

  @issue-5
  Scenario: check fails when gh is not signed in
    Given a valid tenant config
    And gh is not signed in
    When I run "cyclix check"
    Then it exits 1
    And it prints "FAIL: gh is not signed in"

  @issue-5
  Scenario: check fails when the board lacks a configured option
    Given a valid tenant config mapping "in_review" to "In review"
    And the board has no "In review" option
    When I run "cyclix check"
    Then it exits 1
    And it prints "FAIL: the board has no Status option \"In review\""

  @issue-5
  Scenario: An unknown subcommand is a usage error
    When I run "cyclix fly"
    Then it exits 2
