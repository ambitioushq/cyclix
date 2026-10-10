# Changelog

Behaviour changes are listed by scenario: the feature file and the scenario's name.

## Unreleased

### Added

Iteration 0, the spine (#2 to #17). These 60 scenarios are the first entries of the functional spec:

- `agent.feature`
  - A successful call returns the answer and the numbers
  - A call that runs past the timeout is stopped
  - Output that is not JSON is an error
- `cli.feature`
  - check passes when everything is in place
  - check fails when gh is not signed in
  - check fails when the board lacks a configured option
  - An unknown subcommand is a usage error
- `codehost.feature`
  - A new worktree is on its own branch from the base
  - Opening a PR twice returns the first PR
  - Push never forces
  - A merged PR reports merged
- `config.feature`
  - A complete config loads
  - A missing state mapping is named
  - An unknown key is refused
  - CYCLIX_CONFIG picks the file
- `events.feature`
  - A finished stage run writes one event with every key
  - Long text is refused
  - A key outside the schema is refused
  - Each stage run is its own trace
- `fakes.feature`
  - The fake gh lists board items from the world
  - The fake gh moves an item
  - An injected fault fails one call
  - The fake gh refuses a command it does not support
  - A scenario without an issue tag fails the suite
  - The fake agent follows its script
- `gh_shapes.feature`
  - Each fake command returns the same keys as the real one
- `install.feature`
  - A dry run prints the units and changes nothing
  - An existing different unit is not overwritten
  - Install writes both units and starts the timer
  - Force overwrites a different unit
  - Uninstall stops the timer and removes both units
- `package.feature`
  - The CLI prints the version
- `sandbox.feature`
  - A real issue reaches an open PR and then Done
- `self_tenant.feature`
  - A real Cyclix issue reaches a merged PR through the spine
- `stages.feature`
  - A plan that starts with STOP parks the item with its reason
  - A build with no commit fails
  - Admission ignores issues that are not on the board
  - Admission never reads comments
  - A merged PR moves its item to Done
  - A PR closed without merging parks its item
  - A crash after the PR opened does not open a second PR
- `state_core.feature`
  - An issue can be claimed once
  - A run's fields build up and come back at the end
  - An unfinished run is reported as open
  - The best verified commit is the last one whose checks all passed
  - A newer schema is refused
- `sweep.feature`
  - A Ready issue runs through every stage to a PR
  - A failing stage stops the run and parks the item
  - A human moving an item wins over the state core
  - A crashed run is recorded and parked
  - Two passes never overlap
  - Only one item is In progress at a time
- `tracker.feature`
  - Ready items come back oldest first
  - Items outside the configured repo are ignored
  - Setting a state moves the item on the board
  - A gh failure surfaces with its details
  - A board with more items than one page is read in full
- `workstate.feature`
  - Allowed moves
  - The engine never moves an item back to Ready
  - An illegal move changes nothing on the board

The README's usage examples (#35), the first change Cyclix built through its own loop:

- `readme.feature`
  - Every subcommand has an example in the README

WIP limits for each column (#44):

- `wip.feature`
  - A full In review column stops admission
  - A merge in the same pass frees a place
  - Items a human moved count toward the limit
  - A config without WIP limits admits as before
  - A WIP limit the engine cannot keep is refused

Narrow board reads (#47):

- `board_reads.feature`
  - One pass reads the board once
  - A board larger than one page is read in full

The repository URL on every stage-run event (#39):

- `sweep.feature`
  - Every stage-run event carries the repository URL

Rounded costs in the event log (#40):

- `sweep.feature`
  - An agent's cost is written rounded

PRs that follow the template (#50):

- `stages.feature`
  - The PR title is the issue title
  - The PR body follows the PR template
