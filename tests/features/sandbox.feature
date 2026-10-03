@sandbox @issue-15
Feature: The spine works against real GitHub

  Scenario: A real issue reaches an open PR and then Done
    Given a new issue in the sandbox repository, in state "Ready" on the sandbox board
    When one pass runs with the real gh and the real agent
    Then a PR for the issue is open in the sandbox repository
    And the sandbox board shows the issue in "In review"
    When the PR is merged by hand and one pass runs
    Then the sandbox board shows the issue in "Done"
