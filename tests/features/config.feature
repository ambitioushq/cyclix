Feature: The tenant config

  @issue-6
  Scenario: A complete config loads
    Given the example tenant config
    When the config is loaded
    Then the tenant is "cyclix"
    And the version starts with "sha256:"

  @issue-6
  Scenario: A missing state mapping is named
    Given the example config without "needs_decision" under [tracker.states]
    When the config is loaded
    Then it fails with 'config: [tracker.states] is missing "needs_decision"'

  @issue-6
  Scenario: An unknown key is refused
    Given the example config with "colour = 3" under [gate]
    When the config is loaded
    Then it fails with 'config: unknown key "colour" in [gate]'

  @issue-6
  Scenario: CYCLIX_CONFIG picks the file
    Given CYCLIX_CONFIG points at a config for tenant "sandbox"
    When the config is loaded with no path
    Then the tenant is "sandbox"
