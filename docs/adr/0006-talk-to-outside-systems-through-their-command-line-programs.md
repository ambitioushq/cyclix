# ADR-0006: Talk to outside systems through their command-line programs, not their HTTP APIs

**Status:** Accepted

**Date:** October 2026

## Context

Most outside systems Cyclix uses ship a command-line program that handles login, protocol and output format. GitHub ships `gh`, and each coding agent ships its own program.

## Decision

Each adapter runs the system's own program. Cyclix has no HTTP code.

- Each system has one adapter module, and nothing else calls that system's program. The adapter parses the output and raises one kind of error.
- The program picks the protocol and the credentials. For GitHub, `adapters/gh.py` is the only caller of `gh`, and the clone uses `gh repo clone`.
- A program is needed only when its system is in use. `cyclix check` confirms it is installed and signed in.

## Consequences

- Cyclix does not handle tokens or choose a protocol.
- The tests put a fake program first on `PATH`, such as a fake `gh`. A shape check keeps its output like the real one ([Testing](../design/testing.md)).
- A change in a program's output can break an adapter. The shape check catches that.
- There are no retries. The next timer run makes the pass again.
