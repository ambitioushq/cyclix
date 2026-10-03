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
