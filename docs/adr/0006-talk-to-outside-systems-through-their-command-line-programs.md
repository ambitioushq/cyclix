# ADR-0006: Talk to outside systems through their command-line programs, not their HTTP APIs

**Status:** Accepted

**Date:** October 2026

## Context

Most outside systems Cyclix uses ship a command-line program that handles login, protocol and output format. GitHub ships `gh`, and each coding agent ships its own program.

## Decision

Each adapter runs the system's own program. Cyclix has no HTTP code.

- Every GitHub call goes through `adapters/gh.py`, which parses the JSON and raises one kind of error. Nothing else calls `gh`.
- The clone uses `gh repo clone`, so `gh` picks the protocol and the credentials.
- `gh` is needed only when GitHub is the tracker or the code host. `cyclix check` confirms it is installed and signed in.

## Consequences

- Cyclix does not handle GitHub tokens or choose a protocol.
- The tests put a fake `gh` first on `PATH`. A shape check keeps its output like the real one ([Testing](../design/testing.md)).
- A change in a program's output can break an adapter. The shape check catches that.
- There are no retries. The next timer run makes the pass again.
