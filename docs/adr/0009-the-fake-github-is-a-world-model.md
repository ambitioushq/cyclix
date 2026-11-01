# ADR-0009: The fake GitHub is a world model built for the tests, with no replayed recordings

**Status:** Accepted

**Date:** October 2026

## Context

The tests run the engine against a stand-in for GitHub. The stand-in can replay recorded answers or answer from a model of GitHub's state.

## Decision

The fake GitHub is a model. A JSON file holds the issues, the board and the PRs. A fake `gh` program reads and changes it and prints the real `gh` output shape. A scenario's Given steps write the world and its Then steps read it.

A shape check compares the fake's output keys with keys recorded from real `gh` in a sandbox.

## Consequences

- A new scenario needs no new recording.
- A scenario can fail any one call, with an exit code, a stderr message or a stale read.
- The fake can differ from GitHub in ways other than keys. The weekly sandbox run, with the real `gh` and the real agent, covers that.

## Alternatives Considered

**Replaying recordings.** Rejected. Every new scenario would need a new recording, and a scenario could not inject a fault into one call.
