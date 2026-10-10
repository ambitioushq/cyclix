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
  Scenario Outline: A budget cap must be a finite number above 0
    Given the example config with "max_budget_usd" set to <value> under [agent.build]
    When the config is loaded
    Then it fails with 'config: [agent.build] "max_budget_usd" must be a finite number above 0'

    Examples:
      | value |
      | 0     |
      | -1.5  |
      | nan   |
      | inf   |

  @issue-55
  Scenario Outline: pass_env cannot let a credential or git's config through
    Given the example config with "pass_env" set to ["<name>"] under [<table>]
    When the config is loaded
    Then it fails with 'config: [<table>] "pass_env" must not hold <name>: the engine keeps credentials and git's config out of the agent and the gate'

    Examples:
      | table | name                    |
      | agent | GH_TOKEN                |
      | gate  | GITHUB_TOKEN            |
      | agent | SSH_AUTH_SOCK           |
      | gate  | CLAUDE_CODE_OAUTH_TOKEN |
      | gate  | ANTHROPIC_API_KEY       |
      | agent | GIT_CONFIG_PARAMETERS   |
      | gate  | GIT_CONFIG_KEY_0        |

  @issue-55
  Scenario Outline: A value the engine puts in a command or a path must have its expected form
    Given the example config with "<key>" set to <value> under [<table>]
    When the config is loaded
    Then it fails with 'config: [<table>] "<key>" must be <form>, not <value>'

    Examples:
      | table       | key    | value            | form                                                                   |
      | tenant      | name   | "../other"       | letters, digits, ".", "_" and "-", starting with a letter or digit     |
      | tenant      | name   | "-x"             | letters, digits, ".", "_" and "-", starting with a letter or digit     |
      | tracker     | owner  | "--help"         | a GitHub user or organization name                                     |
      | codehost    | repo   | "--upload-pack"  | a GitHub repository written as owner/name                              |
      | codehost    | repo   | "ambitioushq"    | a GitHub repository written as owner/name                              |
      | codehost    | base   | "-b"             | a branch name                                                          |
      | codehost    | base   | "main..other"    | a branch name                                                          |
      | agent.plan  | model  | "--settings"     | a model name or alias                                                  |
      | agent.build | model  | "sonnet x"       | a model name or alias                                                  |

  @issue-55
  Scenario Outline: A pass_env entry must be an environment variable name
    Given the example config with "pass_env" set to ["<name>"] under [<table>]
    When the config is loaded
    Then it fails with 'config: [<table>] "pass_env" must be a list of environment variable names, not "<name>"'

    Examples:
      | table | name     |
      | agent | -x       |
      | gate  | A=B      |
      | gate  | HAS SPACE |

  @issue-55
  Scenario Outline: A count in the config cannot be negative
    Given the example config with "<key>" set to <value> under [<table>]
    When the config is loaded
    Then it fails with 'config: [<table>] "<key>" must be <form>'

    Examples:
      | table   | key          | value | form                       |
      | tracker | project      | 0     | a whole number of 1 or more |
      | limits  | runs_per_day | -1    | a whole number of 0 or more |

  @issue-55
  Scenario Outline: A stage's tools must be tool rules, never flags
    Given the example config with "tools" set to ["Read", "<rule>"] under [agent.build]
    When the config is loaded
    Then it fails with 'config: [agent.build] "tools" must hold tool rules such as Read or Bash(git commit *), not "<rule>"'

    Examples:
      | rule                           |
      | --dangerously-skip-permissions |
      | --settings                     |
      | -p                             |
      | Bash(git commit *              |
      | Read, Write                    |

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
