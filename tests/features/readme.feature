Feature: The README shows how to run cyclix

  @issue-35
  Scenario: Every subcommand has an example in the README
    When I run "cyclix --help"
    Then each subcommand it lists appears in a "cyclix <subcommand>" example in the README's Usage section
