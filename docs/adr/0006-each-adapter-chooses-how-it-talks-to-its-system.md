# ADR-0006: Each adapter chooses how it talks to its system

**Status:** Accepted

**Date:** October 2026

## Context

An outside system can offer a command-line program, an HTTP API, or both. Neither is better for every system. A program handles login, protocol and output format. An HTTP API has versions and documented errors, and Cyclix then owns auth, paging and rate limits. Today the GitHub adapters run `gh` and the agent adapter runs `claude`.

## Decision

The way an adapter talks to its system is a detail of that adapter. The engine sees only the adapter's interface: `Tracker`, `CodeHost` or `Agent`.

- Each system has one adapter module, and nothing else talks to that system.
- The adapter parses what it gets back and raises one kind of error.
- The adapter keeps its credentials to itself, within the limits of [ADR-0013](0013-keep-code-host-credentials-out-of-the-agent-and-the-gate.md).
- An adapter that uses HTTP follows [ADR-0005](0005-use-only-the-standard-library-unless-a-dependency-has-a-written-reason.md).
- `cyclix check` confirms that each adapter's system is reachable and signed in.

## Consequences

- A new tracker, code host or agent needs one new adapter, and the engine does not change.
- An adapter can change its transport without touching the engine.
- Each adapter needs a test fake that matches its transport ([ADR-0009](0009-test-against-fake-outside-systems-that-keep-state.md)). For `gh`, the fake is a program first on `PATH`.
- There are no retries. The next timer run makes the pass again.

## Alternatives Considered

**Command-line programs only.** Rejected. A system with no usable program could not have an adapter.

**HTTP only.** Rejected. Cyclix would own auth, paging and rate limits for every system, including ones whose program already does that.
