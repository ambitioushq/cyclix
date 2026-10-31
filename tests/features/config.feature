Feature: The tenant config loads, or names what is wrong with it

  Scenario: A complete config loads
    Given the example tenant config
    When the config is loaded
    Then the tenant is "storefront"
    And the version starts with "sha256:"

  Scenario: A missing state mapping is named
    Given the example config without "needs_decision" under [tracker.states]
    When the config is loaded
    Then it fails with 'config: [tracker.states] is missing "needs_decision"'

  Scenario: An unknown key is refused
    Given the example config with "colour = 3" under [gate]
    When the config is loaded
    Then it fails with 'config: unknown key "colour" in [gate]'

  Scenario: CYCLIX_CONFIG picks the file
    Given CYCLIX_CONFIG points at a config for tenant "sandbox"
    When the config is loaded with no path
    Then the tenant is "sandbox"

  Scenario: Each agent stage has its own model, caps and tools
    Given the example tenant config
    When the config is loaded
    Then the plan stage uses "claude-opus-5-5" with 30 turns, a budget of 2.0 and the tools "Read Grep Glob"

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
      | codehost    | repo   | "acme"           | a GitHub repository written as owner/name                              |
      | codehost    | base   | "-b"             | a branch name                                                          |
      | codehost    | base   | "main..other"    | a branch name                                                          |
      | agent.plan  | model  | "--settings"     | a model name or alias                                                  |
      | agent.build | model  | "sonnet x"       | a model name or alias                                                  |

  Scenario Outline: A pass_env entry must be an environment variable name
    Given the example config with "pass_env" set to ["<name>"] under [<table>]
    When the config is loaded
    Then it fails with 'config: [<table>] "pass_env" must be a list of environment variable names, not "<name>"'

    Examples:
      | table | name     |
      | agent | -x       |
      | gate  | A=B      |
      | gate  | HAS SPACE |

  Scenario Outline: A count in the config cannot be negative
    Given the example config with "<key>" set to <value> under [<table>]
    When the config is loaded
    Then it fails with 'config: [<table>] "<key>" must be <form>'

    Examples:
      | table   | key          | value | form                       |
      | tracker | project      | 0     | a whole number of 1 or more |
      | limits  | runs_per_day | -1    | a whole number of 0 or more |

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

  Scenario Outline: A turn cap or timeout below 1 is refused
    Given the example config with "<key>" set to <value> under [<table>]
    When the config is loaded
    Then it fails with 'config: [<table>] "<key>" must be a whole number of 1 or more'

    Examples:
      | table       | key             | value |
      | agent.plan  | max_turns       | 0     |
      | agent.build | max_turns       | -1    |
      | agent       | timeout_minutes | 0     |
      | gate        | timeout_minutes | 0     |

  Scenario Outline: The agent command holds only the flags the engine allows
    Given the example config with the agent command "<command>"
    When the config is loaded
    Then it fails with 'config: [agent] "command" may hold only -p, --print and --effort <level> after the program, not "<arg>"'

    Examples:
      | command                                       | arg                            |
      | claude -p --permission-mode bypassPermissions | --permission-mode              |
      | claude -p --dangerously-skip-permissions      | --dangerously-skip-permissions |
      | claude -p --allowedTools=Bash                 | --allowedTools=Bash            |
      | claude -p --max-turns 500                     | --max-turns                    |
      | claude -p --settings {}                       | --settings                     |
      | claude -p --plugin-dir ./plugin               | --plugin-dir                   |
      | claude -p --                                  | --                             |
      | claude -p prompt                              | prompt                         |
      | claude -p --output-format json                | --output-format                |
      | claude -p --verbose                           | --verbose                      |

  Scenario Outline: A flag in the agent command must have its value
    Given the example config with the agent command "<command>"
    When the config is loaded
    Then it fails with 'config: [agent] "command" gives <flag> no value'

    Examples:
      | command                                 | flag            |
      | claude -p --effort                      | --effort        |
      | claude -p --effort --max-turns 1        | --effort        |

  Scenario Outline: The allowed flags load in either form
    Given the example config with the agent command "<command>"
    When the config is loaded
    Then the agent command is "<command>"

    Examples:
      | command                                                   |
      | claude --print --effort high |
      | claude -p --effort=low       |

  Scenario: A config without an instruction folder loads
    Given the example tenant config
    When the config is loaded
    Then it names no instruction folder

  Scenario: An instruction folder under the home folder is found
    Given a folder "rules" in the home folder holding "CLAUDE.md"
    And the example config names the instruction folder "~/rules"
    When the config is loaded
    Then the instruction folder is "rules" in the home folder

  Scenario Outline: An instruction folder that cannot be used is refused
    Given the example config names <folder> as its instruction folder
    When the config is loaded
    Then it fails with '<message>' about that folder

    Examples:
      | folder            | message                                                                          |
      | a missing folder  | config: [agent] "instructions" names <folder>, which does not exist                |
      | a file            | config: [agent] "instructions" names <folder>, which is not a folder               |
      | a relative path   | config: [agent] "instructions" must be an absolute path or start with ~, not "<folder>" |
