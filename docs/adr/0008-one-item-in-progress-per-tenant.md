# ADR-0008: One item in progress per tenant

**Status:** Accepted

**Date:** October 2026

## Context

A tenant could build several issues at once, and each build uses the agent's time and the account's usage limits. But a person reviews every PR (see [ADR-0001](0001-cyclix-never-merges.md)), and a person's attention is the scarce resource (see [ADR-0000](0000-guiding-principles.md)).

## Decision

A Ready item is admitted only when no item is In progress. A tenant has at most one item In progress at a time.

A tenant can also limit how many items each other column holds, through `[limits.wip]` in its config. When a column holds as many items as its limit, or more, the sweep admits nothing, writes no event, and logs why. The count includes items that a person moved into the column. Only `in_progress`, `in_review`, `parked` and `needs_decision` take a limit, and the config refuses an `in_progress` limit other than 1.

Items In review count toward admission only through a limit on In review. Up to that limit, PRs wait for a person while the next item builds.

## Consequences

- The loop does not start new work while finished work waits for a person. This follows the flow practice of Reinertsen and Kanban: when a column is full, stop starting and finish what is there.
- The reconciler runs before admission, so a PR merged since the last pass frees a place in the same pass.
- A run needs no coordination with another run of the same tenant, because no other run is in progress.
- Throughput for one tenant is one item at a time. Running items side by side is coming soon, and the config refuses a larger `in_progress` limit until then.

## Alternatives Considered

**Several items in progress at once.** Left out for now. It needs claims and worktrees that do not collide, and it makes the review queue grow faster than a person can clear it.
