Feature: The package installs and reports its version

  @issue-2
  Scenario: The CLI prints the version
    Given Cyclix is installed from the working tree
    When I run "cyclix --version"
    Then it exits 0
    And it prints "cyclix 0.0.1"
