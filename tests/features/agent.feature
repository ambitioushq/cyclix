Feature: The Claude Code agent adapter

  @issue-11
  Scenario: A successful call returns the answer and the numbers
    Given the agent answers "plan written" with 1200 input tokens, 300 output tokens and cost 0.05
    When the adapter runs a prompt
    Then the result's answer is "plan written"
    And its tokens are 1200 and 300 and its cost is 0.05
    And the prompt and the raw output are saved in the run folder

  @issue-11
  Scenario: A call that runs past the timeout is stopped
    Given the agent takes longer than the timeout
    When the adapter runs a prompt
    Then the result is an error with reason "timeout after 1 minutes"
    And no agent process is left running

  @issue-11
  Scenario: Output that is not JSON is an error
    Given the agent prints "hello" and exits 0
    When the adapter runs a prompt
    Then the result is an error with reason "agent output was not JSON"

  @issue-55
  Scenario: The agent runs restricted, with the stage's tools and caps
    Given the agent answers "plan written"
    When the adapter runs a prompt for the plan stage
    Then the agent was started with "--model claude-opus-5-5"
    And the agent was started with "--restricted --strict-mcp-config --tools Read,Grep,Glob"
    And the agent was started with "--permission-mode dontAsk --permission-prompts none"
    And the agent was started with "--max-turns 30 --max-budget-usd 2.0"
    And the agent was started with "--allowedTools Read Grep Glob"

  @issue-55
  Scenario: The build stage's shell rules give the agent the shell tool
    Given the agent answers "built"
    When the adapter runs a prompt for the build stage
    Then the agent was started with "--tools Read,Edit,Bash"
    And the agent was started with "--allowedTools Read Edit 'Bash(git commit *)'"

  @issue-55
  Scenario: The agent sees only the environment it needs
    Given the engine's environment holds GH_TOKEN, GITHUB_TOKEN, SSH_AUTH_SOCK and AWS_SECRET_ACCESS_KEY
    And the engine's environment holds CLAUDE_CODE_OAUTH_TOKEN, CLAUDE_CONFIG_DIR and USER
    And the agent answers "plan written"
    When the adapter runs a prompt for the plan stage
    Then the agent's environment lacks GH_TOKEN, GITHUB_TOKEN, SSH_AUTH_SOCK and AWS_SECRET_ACCESS_KEY
    And the agent's environment holds CLAUDE_CODE_OAUTH_TOKEN, CLAUDE_CONFIG_DIR, USER, PATH, HOME and CYCLIX_FAKES_DIR
    And the agent's environment sets GIT_TERMINAL_PROMPT to "0" and GIT_CONFIG_NOSYSTEM to "1"
    And the agent's environment sets GIT_CONFIG_GLOBAL to the null device
    And the agent's GH_CONFIG_DIR is an empty folder

  @issue-55
  Scenario: The agent's commits carry the engine's git identity
    Given the engine's git config names the user "Ada Lovelace" with email "ada@example.com"
    And the agent commits a file
    When the adapter runs a prompt for the build stage
    Then the agent's commit is authored by "Ada Lovelace <ada@example.com>" and committed by "Ada Lovelace <ada@example.com>"

  @issue-55
  Scenario: A git identity variable in the engine's environment sets only its own role
    Given the engine's git config names the user "Ada Lovelace" with email "ada@example.com"
    And the engine's environment sets GIT_AUTHOR_NAME to "Grace Hopper"
    And the agent commits a file
    When the adapter runs a prompt for the build stage
    Then the agent's commit is authored by "Grace Hopper <ada@example.com>" and committed by "Ada Lovelace <ada@example.com>"

  @issue-55
  Scenario: The repository's own git identity wins over the engine's
    Given the engine's git config names the user "Ada Lovelace" with email "ada@example.com"
    And the agent commits a file
    And the repository's own git config names the user "Grace Hopper" with email "grace@example.com"
    When the adapter runs a prompt for the build stage
    Then the agent's commit is authored by "Grace Hopper <grace@example.com>" and committed by "Grace Hopper <grace@example.com>"

  @issue-55
  Scenario Outline: A call stopped by a cap says which cap
    Given the agent stops with subtype "<subtype>"
    When the adapter runs a prompt for the build stage
    Then the result is an error with reason "<reason>"

    Examples:
      | subtype              | reason             |
      | error_max_turns      | turn cap reached   |
      | error_max_budget_usd | budget cap reached |
