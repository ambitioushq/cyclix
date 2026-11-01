# ADR-0009: The fake GitHub is a world model built for the tests, with no replayed recordings

**Status:** Accepted

**Date:** October 2026

## Context

The tests run the engine as a subprocess against a stand-in for GitHub. There are two ways to build the stand-in: record real GitHub answers and replay them, or model GitHub's state and answer from the model.

## Decision

The fake GitHub is a world model. A JSON file holds the issues, the board with its items and states, and the PRs with their states. A fake `gh` program reads and changes that world and prints output in the same JSON shape as the real `gh`. A scenario's Given steps write the world, and its Then steps read it.

A separate shape check keeps the fake honest. A script records the key paths of the real `gh` output for each command from a sandbox repo and board. A scenario fails if the fake's output has different keys.

## Consequences

- A new scenario needs no new recording. It sets up the world it needs.
- A scenario can make any one call fail, with an exit code, a stderr message or a stale read.
- The fake can drift from real GitHub in ways that are not about keys. The weekly sandbox run, which uses the real `gh` and the real agent, covers that.

## Alternatives Considered

**Replaying recorded answers.** Recordings carry real quirks. But every new scenario would need a new recording, and a scenario could not inject a fault into one call. The shape check covers the quirks that matter, which are the JSON keys.
