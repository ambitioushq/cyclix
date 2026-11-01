# ADR-0003: The event log is a record the loop never reads to decide

**Status:** Accepted

**Date:** October 2026

## Context

The event log answers questions for a person: what happened to an issue, where a run stopped, what a stage cost. A log that the engine also reads becomes a second store of state. Then a missing, late or reshaped line could change what the loop does.

## Decision

The event log serves review and debugging only. The loop decides from the board, the code host and the SQLite file. It never reads the log.

## Consequences

- A line can be queried, copied, rotated or deleted without changing what the loop does next.
- The log's schema can change for readers without a migration of the loop's state.
- Anything the loop needs to remember across passes, such as a claim or the phase of a run, has its own place in the SQLite file. It is not rebuilt from events.
- A stage-run event builds up in the SQLite file while the run goes, and the log gets it once, when the run ends. If the run dies, the next sweep writes the event with the outcome `crashed`, so a crash cannot lose it.
