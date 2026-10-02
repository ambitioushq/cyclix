Feature: The names check keeps private names out of the public repo

  @issue-3
  Scenario: A file holding a forbidden name fails the check
    Given the forbidden names "acme" and "Blue Harbor"
    And a tracked file "notes.md" whose line 3 reads "We ran it at ACME last week"
    When the names check runs
    Then it exits 1
    And it prints "notes.md:3: forbidden name #1"
    And the output does not contain "acme" in any case

  @issue-3
  Scenario: A name with a space matches across a hyphen
    Given the forbidden names "Blue Harbor"
    And a tracked file "a.md" whose line 1 reads "blue-harbor"
    When the names check runs
    Then it exits 1

  @issue-3
  Scenario: Part of a word does not match
    Given the forbidden names "acme"
    And a tracked file "a.md" whose line 1 reads "acmeology"
    When the names check runs
    Then it exits 0

  @issue-3
  Scenario: A commit message holding a forbidden name fails the check
    Given the forbidden names "acme"
    And a commit whose message reads "Fix the acme run"
    When the names check runs over that commit
    Then it exits 1
    And it prints the commit's short SHA and "forbidden name #1"

  @issue-3
  Scenario: A missing list fails closed
    Given no forbidden names are set
    When the names check runs
    Then it exits 2
