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

  Scenario: A link to a page on the docs site is left to the site build
    Given a docs folder where "a.md" links to "/reference/commands/#cyclix-check"
    When the links in that folder are checked
    Then the report is empty

  Scenario: A link to a docs site page that does not exist is reported
    Given a docs folder where "README.md" links to the site page "https://docs.cyclix.dev/missing/"
    When the links in that folder are checked
    Then the report names "README.md" and "https://docs.cyclix.dev/missing/"

  Scenario: A link to a docs site heading that does not exist is reported
    Given a docs folder where "README.md" links to the site page "https://docs.cyclix.dev/b/#nowhere"
    When the links in that folder are checked
    Then the report names "README.md" and "https://docs.cyclix.dev/b/#nowhere"

  Scenario: A link to a docs site page and heading that exist passes
    Given a docs folder where "README.md" links to the site page "https://docs.cyclix.dev/b/#the-second-part"
    When the links in that folder are checked
    Then the report is empty

  Scenario: A link to the docs site's home page passes
    Given a docs folder where "README.md" links to the site page "https://docs.cyclix.dev/"
    When the links in that folder are checked
    Then the report is empty

  Scenario: Markdown files of installed packages are not checked
    Given a docs folder where "node_modules/pkg/a.md" links to "missing.md"
    When the links in that folder are checked
    Then the report is empty

  Scenario: A link to a heading that exists passes
    Given a docs folder where "a.md" links to "b.md#the-second-part"
    When the links in that folder are checked
    Then the report is empty

  Scenario: A link inside a code block is not checked
    Given a docs folder where "a.md" shows the link "missing.md" in a code block
    When the links in that folder are checked
    Then the report is empty

  Scenario: A broken link with a title is reported
    Given a docs folder where "a.md" links to "missing.md" with a title
    When the links in that folder are checked
    Then the report names "a.md" and "missing.md"

  Scenario: A broken reference link is reported
    Given a docs folder where "a.md" links to "missing.md" through a reference definition
    When the links in that folder are checked
    Then the report names "a.md" and "missing.md"

  Scenario: A link inside a code block that shows a shorter fence is not checked
    Given a docs folder where "a.md" shows the link "missing.md" inside a fence example in a longer code block
    When the links in that folder are checked
    Then the report is empty
