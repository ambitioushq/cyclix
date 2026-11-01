# ADR-0013: The agent and the gate get no GitHub credential through their environment

**Status:** Accepted

**Date:** October 2026

## Context

The agent writes code, and the gate runs that code. Both can be steered by the text they read. If either could reach a GitHub login, it could merge a PR or push to the main branch, and ADR-0001 would hold only because no agent tried.

## Decision

The engine holds the GitHub credential and does every push and PR call itself. The agent and the gate run with an allow-list of environment variables, not the engine's own.

- The agent gets the Claude login, because it needs one. The gate gets no credential at all.
- `gh` is pointed at an empty config folder, and git reads no credential helper from the user's or the system's config. Commits keep the identity git would have used.
- A tenant can let more variables through with `pass_env`. The config is refused if `pass_env` names a GitHub token, an SSH agent socket, a program that git or SSH would ask for a credential, or a variable that sets git's config.
- `GH_TOKEN`, `GITHUB_TOKEN` and `SSH_AUTH_SOCK` are never passed.

The exact lists are in [Configuration](../reference/configuration.md#what-the-agent-and-the-gate-see).

## Consequences

- No credential reaches the agent or the gate through the environment or through git's config.
- Both still run as the host user, with the real `HOME`. Code they run, such as Python started through `Bash(uv run *)`, can read a credential file in that home folder, such as `~/.config/gh/hosts.yml`, by its full path. The `--restricted` flag stops only the agent's Read tool from doing so. [Isolation](../design/isolation.md) describes the container that closes this gap, which is coming soon.
- Run Cyclix as a dedicated user that holds only the tokens the loop needs.
- The agent can also write files that the engine later runs, such as hooks in the tenant's clone. The container closes this too.
