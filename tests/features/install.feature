Feature: Installing the loop as a systemd timer

  @issue-16
  Scenario: A dry run prints the units and changes nothing
    Given a valid tenant config for "cyclix"
    When I run "cyclix install --tenant cyclix --dry-run"
    Then it prints a service with "ExecStart=" ending in "run --once --tenant cyclix"
    And it prints a timer with "OnUnitActiveSec=10min"
    And no file is written

  @issue-16
  Scenario: An existing different unit is not overwritten
    Given a valid tenant config for "cyclix"
    And a unit "cyclix-cyclix.service" that differs from the one Cyclix would write
    When I run "cyclix install --tenant cyclix"
    Then it exits 1
    And it prints the difference
    And the unit is unchanged

  @issue-16
  Scenario: Install writes both units and starts the timer
    Given a valid tenant config for "cyclix"
    When I run "cyclix install --tenant cyclix --every 30min"
    Then it exits 0
    And the unit "cyclix-cyclix.service" holds "Type=oneshot"
    And the unit "cyclix-cyclix.service" holds the config's absolute path
    And the unit "cyclix-cyclix.timer" holds "OnUnitActiveSec=30min"
    And systemctl was called with "--user daemon-reload"
    And systemctl was called with "--user enable --now cyclix-cyclix.timer"

  @issue-16
  Scenario: Force overwrites a different unit
    Given a valid tenant config for "cyclix"
    And a unit "cyclix-cyclix.service" that differs from the one Cyclix would write
    When I run "cyclix install --tenant cyclix --force"
    Then it exits 0
    And the unit "cyclix-cyclix.service" holds "Type=oneshot"

  @issue-16
  Scenario: Uninstall stops the timer and removes both units
    Given a valid tenant config for "cyclix"
    And the loop is installed for "cyclix"
    When I run "cyclix uninstall --tenant cyclix"
    Then it exits 0
    And systemctl was called with "--user disable --now cyclix-cyclix.timer"
    And no unit file is left
