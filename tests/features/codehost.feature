Feature: The GitHub code-host adapter

  @issue-10
  Scenario: A new worktree is on its own branch from the base
    Given the remote's main branch at commit "c1"
    When a worktree is made for #12 titled "Add the state core"
    Then the worktree is on branch "cyclix/12-add-the-state-core"
    And its head is "c1"

  @issue-10
  Scenario: Opening a PR twice returns the first PR
    Given a pushed branch "cyclix/12-add-the-state-core"
    When a PR is opened for it
    And a PR is opened for it again
    Then exactly one PR exists for the branch

  @issue-10
  Scenario: Push never forces
    Given the remote branch has a commit the worktree lacks
    When the worktree is pushed
    Then the push fails
    And the remote branch is unchanged

  @issue-10
  Scenario: A merged PR reports merged
    Given PR #20 for #12 is merged
    When its state is read
    Then it is merged, with its merge time
