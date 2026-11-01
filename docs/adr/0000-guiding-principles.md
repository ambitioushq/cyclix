# ADR-0000: Guiding principles

**Status:** Accepted

**Date:** October 2026

## Context

Cyclix runs a loop with no person watching. It takes an issue, plans and builds the change, checks it, and opens a pull request. Every later design call has to weigh two things: how well a person can see what the loop did, and how much of a person's time the loop uses. Two principles settle those calls, so each later record can point to them.

## Decision

1. **Everything the loop does or hears is recorded.** The record is one append-only log of wide events, shaped like OpenTelemetry log records. The loop never reads the log to decide anything. [ADR-0003](0003-the-event-log-is-never-read-to-decide.md) and [ADR-0004](0004-wide-events-in-opentelemetry-shape.md) give the detail.
2. **A person's attention is the scarce resource.** The loop's job is to spend as little of it as it can. The loop asks a person only for a call that needs one, and it says where and why when it does.

## Consequences

- Each stage run writes an event, and each move out of In progress writes a comment on the issue that says why. A person finds the reason where they act on the item.
- Limits on work in progress (see [ADR-0008](0008-one-item-in-progress-per-tenant.md)) stop the loop from piling up pull requests faster than a person can review them.
- A change that adds a step for a person needs a reason. A change that hides what the loop did needs a better one.
