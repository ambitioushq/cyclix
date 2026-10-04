@live @issue-17
Feature: Cyclix builds itself

  # Checked by hand once, on the host, and recorded in the PR for #17.
  # No steps file binds this feature, so pytest never runs it.

  Scenario: A real Cyclix issue reaches a merged PR through the spine
    Given a Cyclix issue in "Ready" on Cyclix's board
    When the timer's passes run
    Then a PR for the issue is opened by the loop
    And the PR passes CI
    When the maintainer merges it
    Then the board shows the issue in "Done"
    And the event log holds one stage_run event for each stage it passed
