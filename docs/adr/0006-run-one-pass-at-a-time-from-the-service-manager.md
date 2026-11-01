# ADR-0006: Run one pass at a time from the host's service manager, with no long-running process

**Status:** Accepted

**Date:** October 2026

## Context

A long-running process needs its own scheduler, its own restart logic, and a way to notice that it hung.

## Decision

`cyclix run` makes one pass for one tenant and exits. `cyclix install` registers a service that runs one pass, and a timer that starts it every 10 minutes by default, with the host's service manager. Today that is systemd, and the files are a user service and a timer.

A lock file at `<state directory>/<tenant>.lock` stops two passes from overlapping. A pass that finds the lock held logs "another pass is running" and exits 0.

## Consequences

- The service manager does the scheduling and the restarts.
- The lock shows which runs crashed. Only the pass that holds the lock runs stages. So a run still open when a pass takes the lock was left by a pass that died, and the sweep ends it as `crashed`.
- A pass that is alive but hung keeps the lock, and later passes wait behind it.
- Every pass reads the board again.
- `cyclix install` supports systemd only. Another service manager needs its own installer.
