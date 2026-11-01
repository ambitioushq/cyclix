# ADR-0001: The engine does not merge, and a person merges every PR

**Status:** Accepted

**Date:** October 2026

## Context

The loop writes code unattended, from text that others can influence. A merge puts that code on the base branch.

## Decision

The engine pushes the run's branch without force, opens the PR, and reads its state. It has no code that merges. A person reviews and merges every PR.

## Consequences

- A PR waits In review until a person acts. A limit on In review caps how many wait ([ADR-0008](0008-one-item-in-progress-per-tenant.md)).
- `cyclix check` confirms that the base branch requires a pull request and refuses force-pushes and deletion.
- The sandbox tests merge their PR from test code, because the scheduled run has nobody to do it.
- Merging on approval by a designated person, or by rule for a class of PR (a lockfile refresh or a dependency bot's PR, once CI is green and the review is approved), is not built. Adding it supersedes this record.
