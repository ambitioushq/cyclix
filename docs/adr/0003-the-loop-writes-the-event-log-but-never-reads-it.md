# ADR-0003: The loop writes the event log but never reads it

**Status:** Accepted

**Date:** October 2026

## Context

If the engine reads the log, the log becomes another place that holds state. Then a missing or late line could change what the loop does.

## Decision

The event log is for people, to review and debug. The loop decides from the tracker, the code host and its local store.

## Consequences

- Anyone can query, copy, rotate or delete the log without changing what the loop does next.
- The log's schema can change without moving the loop's state.
- A stage-run event builds up in the local store while the run goes. The log gets it once, when the run ends. If the run dies while its row is open, the next sweep writes it with the outcome `crashed`. The engine marks the row ended before it writes the event, so a crash between those two steps loses that one event.
