# ADR-0007: The host's service manager runs one pass at a time, with no long-running process

**Status:** Accepted

**Date:** October 2026

## Context

The loop has to run repeatedly with nobody watching, and it has to survive crashes. A long-running process needs its own scheduler, its own restart logic and its own way to detect that it hung.

## Decision

Cyclix has no long-running process. `cyclix run` makes one pass for one tenant and exits. The host's service manager starts it again: `cyclix install` writes a systemd user service that runs one pass and a systemd user timer that starts it, every 10 minutes by default.

A file lock at `<state directory>/<tenant>.lock` keeps two passes from overlapping. A pass that finds the lock held logs "another pass is running" and exits 0.

## Consequences

- Scheduling, restarts and logging of the process belong to systemd.
- The lock tells the sweep which runs crashed. Only the pass that holds the lock runs stages for the tenant, so any run still open when a pass takes the lock was left by a pass that died. The sweep ends it as `crashed`. The state file keeps no process ID.
- A pass that is alive but hung keeps the lock, and later passes wait behind it.
- Each pass reads the board again. The board read costs one point of GitHub's rate limit for each page of items (see [ADR-0010](0010-the-board-is-read-with-narrow-graphql-queries.md)).
- `cyclix install` needs systemd on the host.
