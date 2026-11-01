# ADR-0000: Guiding principles

**Status:** Accepted

**Date:** October 2026

## Context

Cyclix runs unattended. Each design call has to balance two things: how well a person can see what the loop did, and how much of a person's time it takes.

## Decision

1. Record everything the loop does or hears, so a person can see what it did and why ([ADR-0003](0003-one-wide-event-per-stage-run-in-opentelemetry-shape.md)).
2. A person's attention is the scarce resource. Ask a person only for a call that needs one.

## Consequences

- Every stage run writes an event.
- Every move out of In progress writes a comment on the issue that gives the reason.
- Limits on work in progress stop the loop from queuing more PRs than a person can review.
