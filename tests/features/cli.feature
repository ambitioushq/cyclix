Feature: The cyclix command checks a tenant's setup and refuses unknown subcommands

  Scenario: check passes when everything is in place
    Given a valid tenant config
    And gh is signed in
    And the board has every configured Status option
    When I run "cyclix check"
    Then it exits 0
    And every line ends in "ok"

  Scenario: check --verbose logs the config it read and its gh calls
    Given a valid tenant config
    And gh is signed in
    When I run "cyclix check --verbose"
    Then it exits 0
    And every line ends in "ok"
    And a log line starts with "DEBUG cyclix.cli: read the config at "
    And a log line starts with "DEBUG cyclix.adapters.gh: gh auth status exited 0 after "

  Scenario: check fails when gh is not signed in, and skips the checks that need it
    Given a valid tenant config
    And gh is not signed in
    When I run "cyclix check"
    Then it exits 1
    And it reports "FAIL: gh: not signed in" with the fix "run \"gh auth login\""
    And it prints "skipped: board: needs gh signed in"
    And it prints "skipped: protection of the base branch: needs gh signed in"

  Scenario: check fails when the agent command is not on PATH
    Given a valid tenant config whose agent command is "no-such-agent"
    When I run "cyclix check"
    Then it exits 1
    And it reports "FAIL: agent command no-such-agent: not on PATH" with the fix "install it, or change [agent] command in <config>"

  Scenario: check fails when the instruction folder is missing
    Given a valid tenant config naming a missing instruction folder
    When I run "cyclix check"
    Then it exits 1
    And it reports "FAIL: config: [agent] \"instructions\" names <world>/no-such-folder, which does not exist" with the fix "edit <config>"

  Scenario: check fails when the board lacks a configured option
    Given a valid tenant config mapping "in_review" to "In review"
    And the board has no "In review" option
    When I run "cyclix check"
    Then it exits 1
    And it reports "FAIL: board option \"In review\" for in_review: not on the Status field" with the fix "add \"In review\" to the board's Status field, or change [tracker.states] in_review in <config>"

  Scenario Outline: check fails when the base branch is not protected
    Given a valid tenant config
    And the base branch <protection>
    When I run "cyclix check"
    Then it exits 1
    And it reports "FAIL: protection of the base branch \"main\": <message>" with the fix "<fix>"

    Examples:
      | protection          | message                                                                 | fix                                                                                                                                         |
      | has no protection   | lets a change skip a pull request, allows force-pushes and allows deletion | in the settings of o/r, add a ruleset for \"main\" with \"Require a pull request before merging\", \"Block force pushes\" and \"Restrict deletions\" |
      | allows force-pushes | allows force-pushes                                                     | in the settings of o/r, add a ruleset for \"main\" with \"Block force pushes\"                                                              |

  Scenario: check passes when a ruleset protects the base branch
    Given a valid tenant config
    And the base branch is protected by a ruleset alone
    And its branch protection settings cannot be read
    When I run "cyclix check"
    Then it exits 0

  Scenario: check fails when the repository's plan hides the base branch's protection
    Given a valid tenant config
    And the base branch has no ruleset
    And its branch protection settings cannot be read
    When I run "cyclix check"
    Then it exits 1
    And it reports "FAIL: protection of the base branch \"main\": cannot read it: gh: Upgrade to GitHub Pro or make this repository public to enable this feature. (HTTP 403)" with the fix "make o/r public, or move its owner to a paid GitHub plan; then add a ruleset for \"main\" in the settings of o/r"

  Scenario: The shell completes a command when the extras group is installed
    When the shell asks cyclix to complete "cyclix ch"
    Then it offers "check"

  Scenario: An unknown subcommand is a usage error
    When I run "cyclix fly"
    Then it exits 2
