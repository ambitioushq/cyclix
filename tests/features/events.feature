Feature: Stage-run events are written to the event log

  @issue-12
  Scenario: A finished stage run writes one event with every key
    Given a stage run for #12 at stage "gate" ending "parked" with reason "gate command 2 exited 1"
    When its event is written
    Then the event log holds one line for #12
    And the line has schema "cyclix.event/0" and body "stage_run"
    And it has every stage-run key, with null for the model fields

  @issue-12
  Scenario: Long text is refused
    Given a stage run whose reason is 2000 characters long
    When its event is written
    Then it fails with "event attribute cyclix.outcome.reason is too long"
    And the event log is unchanged

  @issue-12
  Scenario: A key outside the schema is refused
    Given a stage run with the extra field "cyclix.prompt" = "plan the change"
    When its event is written
    Then it fails with "event attribute cyclix.prompt is not in schema cyclix.event/0"
    And the event log is unchanged

  @issue-12
  Scenario: Each stage run is its own trace
    Given two stage runs for #12
    When both events are written
    Then the two lines have different trace IDs
    And both carry cyclix.issue.id 12
