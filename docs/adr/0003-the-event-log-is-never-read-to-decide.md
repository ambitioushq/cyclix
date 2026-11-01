# ADR-0003: The event log is a record the loop never reads to decide

**Status:** Accepted

**Date:** October 2026

## Context

A log the engine also reads becomes a second store of state. A missing, late or reshaped line could then change what the loop does.

## Decision

The event log serves review and debugging only. The loop decides from the tracker, the code host and its local store.

## Consequences

- A line can be queried, copied, rotated or deleted without changing what the loop does.
- The log's schema can change without a migration of the loop's state.
- A stage-run event builds up in the local store while the run goes, and the log gets it once, when the run ends. If the run dies, the next sweep writes it with the outcome `crashed`.
