# ADR-0006: Adapters wrap the vendor's CLI, with no HTTP layer

**Status:** Accepted

**Date:** October 2026

## Context

For GitHub and Claude Code, the vendor ships a command-line program (`gh`, `claude`) that handles login, protocol and output formats.

## Decision

Each adapter runs the vendor's program. Cyclix builds no HTTP layer.

- All GitHub calls go through `adapters/gh.py`, which parses JSON and raises one error type. Nothing else calls `gh`.
- The clone uses `gh repo clone`, so `gh` picks the protocol and credentials.
- `gh` is required only when GitHub is the tracker or the code host. `cyclix check` confirms it is installed and signed in.

## Consequences

- Cyclix does not handle GitHub tokens or protocol choice.
- The tests put a fake `gh` first on `PATH`, and a shape check keeps its output like the real one ([Testing](../design/testing.md)).
- A change in a vendor program's output can break an adapter. The shape check catches it.
- There are no retries. The next timer run makes the pass again.
