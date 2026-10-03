Feature: One pass of the loop

  @issue-13 @xfail-until-14
  Scenario: A Ready issue runs through every stage to a PR
    Given an issue #12 in state "Ready" on the board
    And the agent writes a plan, then commits a change
    And the gate commands pass
    When one pass runs
    Then a PR for #12 is open
    And the board shows #12 in "In review"
    And the event log holds stage_run events for #12 at admission, plan, build, gate, adversarial_review and pr

  @issue-13 @xfail-until-14
  Scenario: A failing stage stops the run and parks the item
    Given an issue #12 in state "Ready" on the board
    And the gate's second command fails
    When one pass runs
    Then no PR for #12 exists
    And the board shows #12 in "Parked"
    And the gate event's outcome is "parked"

  @issue-13
  Scenario: A human moving an item wins over the state core
    Given issue #12 is claimed in the state core and In progress on the board
    And a human moves #12 to "Parked" on the board
    When one pass runs
    Then the claim on #12 is released
    And issue #12 is not run

  @issue-13
  Scenario: A crashed run is recorded and parked
    Given a run for #12 began at stage "build" in phase "agent" and its process is gone
    When one pass runs
    Then a stage_run event for #12 at "build" has outcome "crashed"
    And the board shows #12 in "Parked" with reason "run crashed in phase agent"

  @issue-13
  Scenario: Two passes never overlap
    Given a pass is running for the tenant
    When a second pass starts
    Then it exits 0
    And it prints "another pass is running"

  @issue-13
  Scenario: Only one item is In progress at a time
    Given issue #12 is In progress and issue #13 is Ready
    When one pass runs
    Then issue #13 stays in "Ready"
