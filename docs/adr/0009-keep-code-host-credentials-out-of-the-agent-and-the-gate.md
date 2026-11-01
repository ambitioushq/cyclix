# ADR-0009: Keep code host credentials out of the agent's and the gate's environment

**Status:** Accepted

**Date:** October 2026

## Context

The agent writes code from text that can carry instructions, and the gate runs that code. With a code host credential, either one could merge a PR or push to the base branch.

## Decision

The engine holds the code host credential and makes every push and PR call itself. The agent and the gate get a short list of environment variables, not the engine's own.

- The agent gets the login it needs to reach the model, and the gate gets no credential. Today the agent's login is the Claude login.
- The code host's program points at an empty config folder (for GitHub, `gh`). Git reads no credential helper from the user's or the system's config. Commits keep the identity git would have used.
- A tenant can pass more variables with `pass_env`. The config is refused if `pass_env` names a code host token, an SSH agent socket, a program that git or SSH would ask for a credential, or a variable that sets git's config.

The exact lists are in [Configuration](../reference/configuration.md#what-the-agent-and-the-gate-see).

## Consequences

- No credential reaches either one through the environment or through git's config.
- Both still run as the host user, with the real `HOME`. Code they run can read a credential file there by its full path, and can write files that the engine runs later. A container would close this ([Isolation](../design/isolation.md)). Until then, run Cyclix as its own user, with only the tokens the loop needs.
