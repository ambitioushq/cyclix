# ADR-0009: Test against fake outside systems that keep state, not recorded answers

**Status:** Accepted

**Date:** October 2026

## Context

The tests run the engine against stand-ins for the tracker, the code host and the agent. A stand-in can replay recorded answers, or answer from a model of the system's state.

## Decision

Each fake is a model. A state file holds what the system would hold, such as issues, the board and PRs. A fake program reads and changes that file and prints output in the shape of the real program. A scenario's Given steps write the file, and its Then steps read it.

For GitHub, the fake is a `gh` program over a JSON file. A shape check compares the keys in its output with keys recorded from the real `gh` in a sandbox.

## Consequences

- A new scenario needs no new recording.
- A scenario can make any one call fail, with an exit code, a stderr message or a stale read.
- A fake can differ from the real system in ways other than keys. The weekly sandbox run, which uses the real programs and the real agent, covers that.

## Alternatives Considered

**Replay recorded answers.** Rejected. Every new scenario would need a new recording, and a scenario could not make one call fail.
