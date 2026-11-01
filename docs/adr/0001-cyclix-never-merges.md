# ADR-0001: Cyclix never merges, and a person merges every PR

**Status:** Accepted

**Date:** October 2026

## Context

The loop writes code unattended, from text that anyone with access to the board can influence. A merge puts that code on the main branch. A bad merge costs far more than a PR that waits a day for review.

## Decision

Cyclix opens pull requests and never merges one. A person reviews and merges every PR.

The engine has no code that merges. It pushes the run's branch without force, opens the PR, and moves the item to In review. After that it only reads the PR's state, to find out whether a person merged or closed it.

## Consequences

- A PR waits In review until a person acts. The In review column can hold a limit (see [ADR-0008](0008-one-item-in-progress-per-tenant.md)), so waiting PRs stop the loop from starting more work than a person can review.
- The rule holds only as far as the agent and the gate cannot reach a credential that can merge. [ADR-0013](0013-the-agent-and-the-gate-get-no-github-credential.md) covers what is built, and [Isolation](../design/isolation.md) covers what is coming.
- `cyclix check` confirms that the base branch requires a pull request and refuses force-pushes and deletion, so GitHub enforces the rule too.
- The sandbox tests merge their PR from the test itself, because the scheduled run has nobody to do it. That merge is in test code and never in the engine.
