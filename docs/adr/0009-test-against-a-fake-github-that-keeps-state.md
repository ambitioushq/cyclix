# ADR-0009: Test against a fake GitHub that keeps state, not recorded answers

**Status:** Accepted

**Date:** October 2026

## Context

The tests run the engine against a stand-in for GitHub. The stand-in can replay recorded answers, or answer from a model of GitHub's state.

## Decision

The fake GitHub is a model. A JSON file holds the issues, the board and the PRs. A fake `gh` program reads and changes that file and prints output in the real `gh` shape. A scenario's Given steps write it, and its Then steps read it.

A shape check compares the keys in the fake's output with keys recorded from the real `gh` in a sandbox.

## Consequences

- A new scenario needs no new recording.
- A scenario can make any one call fail, with an exit code, a stderr message or a stale read.
- The fake can differ from GitHub in ways other than keys. The weekly sandbox run, which uses the real `gh` and the real agent, covers that.

## Alternatives Considered

**Replay recorded answers.** Rejected. Every new scenario would need a new recording, and a scenario could not make one call fail.
