# ADR-0008: One item in progress per tenant

**Status:** Accepted

**Date:** October 2026

## Context

A tenant could build several issues at once. A person reviews every PR ([ADR-0001](0001-merges-need-approval-or-a-written-rule.md)), and a person's attention is the scarce resource ([ADR-0000](0000-guiding-principles.md)).

## Decision

A Ready item is admitted only when no item is In progress.

A tenant can limit the other columns with `[limits.wip]`. When a column holds as many items as its limit or more, the sweep admits nothing, writes no event, and logs why. The count includes items a person moved in. Only `in_progress`, `in_review`, `parked` and `needs_decision` take a limit, and the config refuses an `in_progress` limit other than 1.

## Consequences

- The loop stops starting work while finished work waits for a person. This follows the flow practice of Reinertsen and Kanban.
- The reconciler runs before admission, so a PR merged since the last pass frees a place in the same pass.
- A run needs no coordination with another run of the same tenant.
- Throughput for a tenant is one item at a time.

## Alternatives Considered

**Several items in progress.** Not built. It needs claims and worktrees that do not collide, and the review queue would grow faster.
