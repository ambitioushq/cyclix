# ADR-0000: Guiding principles

**Status:** Accepted

**Date:** October 2026

## Context

Cyclix runs a loop with no person watching. Design calls in it trade how well a person can see what the loop did against how much of a person's time it uses.

## Decision

1. Everything the loop does or hears is recorded in one append-only log of wide events. The loop never reads the log to decide anything ([ADR-0003](0003-the-event-log-is-never-read-to-decide.md), [ADR-0004](0004-wide-events-in-opentelemetry-shape.md)).
2. A person's attention is the scarce resource. The loop asks a person only for a call that needs one.

## Consequences

- Each stage run writes an event.
- Each move out of In progress writes a comment on the issue with the reason.
- Limits on work in progress stop the loop from queuing more PRs than a person can review ([ADR-0008](0008-one-item-in-progress-per-tenant.md)).
