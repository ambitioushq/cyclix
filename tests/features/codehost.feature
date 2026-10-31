Feature: The code host keeps one branch and one PR per issue, and never forces a push

  Scenario: A new worktree is on its own branch from the base
    Given the remote's main branch at commit "c1"
    When a worktree is made for #12 titled "Add the state core"
    Then the worktree is on branch "cyclix/12-add-the-state-core"
    And its head is "c1"

  Scenario: Opening a PR twice returns the first PR
    Given a pushed branch "cyclix/12-add-the-state-core"
    When a PR is opened for it
    And a PR is opened for it again
    Then exactly one PR exists for the branch

  Scenario: Push never forces
    Given the remote branch has a commit the worktree lacks
    When the worktree is pushed
    Then the push fails
    And the remote branch is unchanged

  Scenario: A merged PR reports merged
    Given PR #20 for #12 is merged
    When its state is read
    Then it is merged, with its merge time
