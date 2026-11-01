# ADR-0006: Adapters wrap the vendor's CLI, with no HTTP layer

**Status:** Accepted

**Date:** October 2026

## Context

Cyclix talks to three outside systems: a tracker, a code host and a coding agent. For GitHub and Claude Code, the vendor already ships a command-line program, `gh` and `claude`, that handles login, protocol choice and output formats.

## Decision

Each adapter runs the vendor's own program. Cyclix builds no HTTP layer.

- The GitHub adapters call the `gh` CLI. All calls go through one module, `adapters/gh.py`, which runs `gh`, parses its JSON and raises one error type. Nothing else in the engine calls `gh`.
- The clone goes through `gh repo clone`, so `gh` picks the protocol and the credentials.
- The agent adapter runs the configured agent command, `claude -p` by default.
- `gh` is required only when GitHub is the chosen tracker or code host. `cyclix check` confirms that it is installed and signed in.

## Consequences

- Cyclix does not handle GitHub tokens, paging of REST calls or protocol selection. `gh` does.
- The tests put a fake `gh` first on `PATH`. A check keeps that fake's output in the same shape as the real one (see [Testing](../design/testing.md)).
- A call that takes longer than 60 seconds fails as exit code 124. There are no retries, because the next timer run makes the pass again.
- A change in a vendor program's output can break an adapter. The shape check exists to catch that.
