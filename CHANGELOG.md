# Changelog

Behaviour changes are listed by scenario: the feature file and the scenario's name.

## Unreleased

### Added

WIP limits for each column (#44):

- `wip.feature`
  - A full In review column stops admission
  - A merge in the same pass frees a place
  - Items a human moved count toward the limit
  - A config without WIP limits admits as before
  - A WIP limit the engine cannot keep is refused
