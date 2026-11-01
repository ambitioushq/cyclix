Feature: The lint checks fail a function that is too complex to read

  Scenario: A function with 11 paths fails ruff
    Given a file holding a function with 11 paths
    When ruff checks the file under the project's config
    Then it exits 1
    And the output names "C901"

  Scenario Outline: A function over a pylint limit fails ruff
    Given a file holding a function with <count> <kind>
    When ruff checks the file under the project's config
    Then it exits 1
    And the output names "<rule>"

    Examples:
      | count | kind       | rule    |
      | 7     | returns    | PLR0911 |
      | 13    | branches   | PLR0912 |
      | 51    | statements | PLR0915 |

  Scenario: A function over the cognitive limit fails complexipy
    Given a file holding a function with a cognitive complexity of 16
    When complexipy checks the file under the project's config
    Then it exits 1
    And the output names "tangled"

  Scenario: The source, the tests and the scripts pass both checks
    When ruff and complexipy check the repository
    Then both exit 0

  Scenario: complexipy checks every script in the fakes folder
    When I read the complexipy config
    Then it names every file in "tests/fakes/bin"
