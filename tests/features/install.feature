Feature: Installing the loop as a systemd timer

  Scenario: A dry run prints the units and changes nothing
    Given a valid tenant config for "storefront"
    When I run "cyclix install --tenant storefront --dry-run"
    Then it prints a service with "ExecStart=" ending in "run --tenant storefront"
    And it prints a timer with "OnUnitActiveSec=10min"
    And no file is written

  Scenario: An existing different unit is not overwritten
    Given a valid tenant config for "storefront"
    And a unit "cyclix-storefront.service" that differs from the one Cyclix would write
    When I run "cyclix install --tenant storefront"
    Then it exits 1
    And it prints the difference
    And the unit is unchanged

  Scenario: Install writes both units and starts the timer
    Given a valid tenant config for "storefront"
    When I run "cyclix install --tenant storefront --every 30min"
    Then it exits 0
    And the unit "cyclix-storefront.service" holds "Type=oneshot"
    And the unit "cyclix-storefront.service" holds the config's absolute path
    And the unit "cyclix-storefront.timer" holds "OnUnitActiveSec=30min"
    And systemctl was called with "--user daemon-reload"
    And systemctl was called with "--user enable --now cyclix-storefront.timer"

  Scenario: Force overwrites a different unit
    Given a valid tenant config for "storefront"
    And a unit "cyclix-storefront.service" that differs from the one Cyclix would write
    When I run "cyclix install --tenant storefront --force"
    Then it exits 0
    And the unit "cyclix-storefront.service" holds "Type=oneshot"

  Scenario: Uninstall stops the timer and removes both units
    Given a valid tenant config for "storefront"
    And the loop is installed for "storefront"
    When I run "cyclix uninstall --tenant storefront"
    Then it exits 0
    And systemctl was called with "--user disable --now cyclix-storefront.timer"
    And no unit file is left
