@issue-15
Feature: The fake gh matches real gh output

  Scenario: Each fake command returns the same keys as the real one
    Given the recorded key paths for every gh command Cyclix uses
    When the fake gh runs each command
    Then its key paths match the recording
