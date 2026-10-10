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

  @issue-55
  Scenario: Each agent stage has its own model, caps and tools
    Given the example tenant config
    When the config is loaded
    Then the plan stage uses "claude-opus-5-5" with 30 turns, a budget of 2.0 and the tools "Read Grep Glob"

  @issue-55
  Scenario Outline: A turn cap or timeout below 1 is refused
    Given the example config with "<key>" set to <value> under [<table>]
    When the config is loaded
    Then it fails with 'config: [<table>] "<key>" must be a whole number of 1 or more'

    Examples:
      | table       | key             | value |
      | agent.plan  | max_turns       | 0     |
      | agent.build | max_turns       | -1    |
      | agent       | timeout_minutes | 0     |

  @issue-55
  Scenario Outline: The agent command cannot set what the engine decides
    Given the example config with the agent command "claude -p <flag>"
    When the config is loaded
    Then it fails with 'config: [agent] "command" must not hold <name>: the engine decides the agent's permissions, tools and caps'

    Examples:
      | flag                                | name                           |
      | --permission-mode bypassPermissions | --permission-mode              |
      | --dangerously-skip-permissions      | --dangerously-skip-permissions |
      | --allowedTools=Bash                 | --allowedTools                 |
      | --max-turns 500                     | --max-turns                    |
      | --settings {}                       | --settings                     |
