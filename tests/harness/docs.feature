Feature: The links in the docs lead somewhere

  Scenario: Every relative link in the README and the docs reaches a file and a heading
    When the links in README.md and under docs/ are checked
    Then every relative link reaches a file, and a heading when it names one

  Scenario: A link to a file that does not exist is reported
    Given a docs folder where "a.md" links to "missing.md"
    When the links in that folder are checked
    Then the report names "a.md" and "missing.md"

  Scenario: A link to a heading that does not exist is reported
    Given a docs folder where "a.md" links to "b.md#nowhere"
    When the links in that folder are checked
    Then the report names "a.md" and "b.md#nowhere"

  Scenario: A link to a heading that exists passes
    Given a docs folder where "a.md" links to "b.md#the-second-part"
    When the links in that folder are checked
    Then the report is empty

  Scenario: A link inside a code block is not checked
    Given a docs folder where "a.md" shows the link "missing.md" in a code block
    When the links in that folder are checked
    Then the report is empty
