# ADR-0013: The agent and the gate get no GitHub credential through their environment

**Status:** Accepted

**Date:** October 2026

## Context

The agent writes code and the gate runs it. Text they read can steer them. With a GitHub credential, either could merge a PR or push to the base branch.

## Decision

The engine holds the GitHub credential and does every push and PR call. The agent and the gate run with an allow-list of environment variables, not the engine's own.

- The agent gets the Claude login. The gate gets no credential.
- `gh` is pointed at an empty config folder. Git reads no credential helper from the user's or the system's config. Commits keep the identity git would have used.
- A tenant can pass more variables with `pass_env`. The config is refused if `pass_env` names a GitHub token, an SSH agent socket, a program git or SSH would ask for a credential, or a variable that sets git's config.

The exact lists are in [Configuration](../reference/configuration.md#what-the-agent-and-the-gate-see).

## Consequences

- No credential reaches either through the environment or git's config.
- Both still run as the host user with the real `HOME`. Code they run can read a credential file there by its full path, and can write files the engine later runs. A container would close this ([Isolation](../design/isolation.md)). Until then, run Cyclix as a dedicated user that holds only the tokens the loop needs.
