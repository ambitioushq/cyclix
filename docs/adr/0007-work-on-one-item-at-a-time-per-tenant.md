# ADR-0007: Work on one item at a time for each tenant

**Status:** Accepted

**Date:** October 2026

## Context

A tenant could build several issues at once. But a person reviews the PRs ([ADR-0001](0001-merge-only-after-approval-or-under-a-written-rule.md)), and a person's attention is the scarce resource ([ADR-0000](0000-guiding-principles.md)).

## Decision

Cyclix admits a Ready item only when no item is In progress.

A tenant can limit the other columns under `[limits.wip]`. When a column holds as many items as its limit or more, the sweep admits nothing, writes no event, and logs the reason. The count includes items that a person moved in. Only `in_progress`, `in_review`, `parked` and `needs_decision` take a limit. The config refuses an `in_progress` limit other than 1.

## Consequences

- The loop stops starting work while finished work waits for a person. This is the flow practice of Reinertsen and Kanban.
- The reconciler runs before admission. A PR merged since the last pass frees a place in the same pass.
- Two runs of one tenant never need to coordinate.
- A tenant builds one item at a time.

## Alternatives Considered

**Several items in progress.** Not built. It needs claims and worktrees that cannot collide, and the review queue would grow faster.
