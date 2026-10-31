Feature: The cyclix command checks a tenant's setup and refuses unknown subcommands

  Scenario: check passes when everything is in place
    Given a valid tenant config
    And gh is signed in
    And the board has every configured Status option
    When I run "cyclix check"
    Then it exits 0
    And every line ends in "ok"

  Scenario: check fails when gh is not signed in
    Given a valid tenant config
    And gh is not signed in
    When I run "cyclix check"
    Then it exits 1
    And it prints "FAIL: gh is not signed in"

  Scenario: check fails when the board lacks a configured option
    Given a valid tenant config mapping "in_review" to "In review"
    And the board has no "In review" option
    When I run "cyclix check"
    Then it exits 1
    And it prints "FAIL: the board has no Status option \"In review\""

  Scenario Outline: check fails when the base branch is not protected
    Given a valid tenant config
    And the base branch <protection>
    When I run "cyclix check"
    Then it exits 1
    And it prints "FAIL: <message>"

    Examples:
      | protection          | message                                                                                                         |
      | has no protection   | the base branch \"main\" lets a change skip a pull request, allows force-pushes and allows deletion           |
      | allows force-pushes | the base branch \"main\" allows force-pushes                                                                   |

  Scenario: check passes when a ruleset protects the base branch
    Given a valid tenant config
    And the base branch is protected by a ruleset alone
    And its branch protection settings cannot be read
    When I run "cyclix check"
    Then it exits 0

  Scenario: check fails when it cannot read the base branch's protection
    Given a valid tenant config
    And the base branch has no ruleset
    And its branch protection settings cannot be read
    When I run "cyclix check"
    Then it exits 1
    And it prints "FAIL: cannot read the protection of the base branch \"main\": gh: Upgrade to GitHub Pro or make this repository public to enable this feature. (HTTP 403)"

  Scenario: An unknown subcommand is a usage error
    When I run "cyclix fly"
    Then it exits 2
