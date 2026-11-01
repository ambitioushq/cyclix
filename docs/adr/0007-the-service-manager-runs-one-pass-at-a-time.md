# ADR-0007: The host's service manager runs one pass at a time, with no long-running process

**Status:** Accepted

**Date:** October 2026

## Context

A long-running process needs its own scheduler, restart logic and hang detection.

## Decision

`cyclix run` makes one pass for one tenant and exits. `cyclix install` writes a systemd user service that runs one pass and a timer that starts it, every 10 minutes by default.

A file lock at `<state directory>/<tenant>.lock` keeps passes from overlapping. A pass that finds it held logs "another pass is running" and exits 0.

## Consequences

- Scheduling and restarts belong to systemd.
- The lock tells the sweep which runs crashed. Only the pass that holds it runs stages, so a run still open when a pass takes the lock was left by a pass that died. The sweep ends it as `crashed`.
- A pass that is alive but hung keeps the lock, and later passes wait behind it.
- Every pass reads the board again ([ADR-0010](0010-the-board-is-read-with-narrow-graphql-queries.md)).
- `cyclix install` needs systemd.
