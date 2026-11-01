# ADR-0005: Confine the agent and the gate

**Status:** Accepted

**Date:** October 2026

## Context

The agent writes code unattended. It reads issues, comments and repository files, and anyone who can write those can put instructions in them for the agent to follow. The gate then runs the code the agent wrote. With a write credential, either one could merge a PR or push to the base branch. With network access, either one could send out what it can read.

Anthropic's cloud sessions of Claude Code, GitHub's Copilot coding agent and OpenAI's Codex cloud all confine their agents by the same rules. [Isolation](../design/isolation.md#what-comparable-agent-runners-do) gives the details and the sources.

## Decision

The engine is the trusted part. It holds the code host credential and makes every push, PR call and merge itself. The agent and the gate are the untrusted part, and they run under five rules:

1. Each agent call and each gate run is inside an isolation boundary: a container or a VM, separate from the host. The boundary covers the whole agent process, including its file tools, hooks and tool servers, not only the shell commands it runs.
2. No credential that can write to the repository enters the boundary. The agent gets only the login it needs to reach the model, and the gate gets no credential. The engine never runs git with its credential in a directory the agent could write.
3. Outgoing traffic is blocked, except to a listed set of hosts, such as the model's API and the package index.
4. Each run gets a fresh environment, removed when the run ends.
5. The code host is the final gate: branch protection on the base branch, and the merge rule in [ADR-0001](0001-merge-only-after-approval-or-under-a-written-rule.md).

Inside the boundary, a second layer limits what the agent asks to do:

- The agent runs in a mode that refuses any tool call outside its stage's list and never asks. Each stage has its own list in the tenant config. A stage with no shell rule has no shell. `git push` and the code host's program are on no list.
- The agent ignores settings files, repository hooks and repository tool servers, and its file tools stay in the working directory.
- Each stage has a turn limit and a spend limit.
- The agent command in the config is a program followed only by listed flags. The engine adds every other flag.
- The agent and the gate get an allow-list of environment variables, with no code host credential in it.

## Consequences

- The second layer and the branch protection check are built. The boundary, the network rules, the fresh environment for each run and the push from a repository the agent never touched are coming soon. Today the engine pushes from the worktree the agent wrote. [Isolation](../design/isolation.md#what-is-built-and-what-is-coming-soon) tracks each part.
- Until the boundary is built, the agent and the gate run as the host user, with the real `HOME`. Code they run can read a credential file by its full path, and can write files that the engine runs later. Run Cyclix as its own user, with only the tokens the loop needs.
- The tool list is not a boundary. A rule such as `Bash(uv run *)` lets the agent run any Python it writes.
- A useful command that is missing from a list is refused, and the run fails until a person adds it to the tenant config.
- The agent can still send out what it can read, through the model's API. A private repository's code goes to the model provider in any case.

## Alternatives Considered

**The second layer alone.** Rejected as the end state, though it is what is built today. It limits what the agent asks to do, not what the code it writes can do once a tool or the gate runs it.

**Allow every tool call.** Replaced. Anything the agent reads could direct it to any action.

**A list of refused flags in the agent command.** Rejected. With Claude Code, it missed flags such as `--plugin-dir`, whose plugins can bring hooks. It also missed `--`, which makes every later argument plain text, and a last flag that takes a value, which would swallow the engine's `--model`. An allow list knows which of its flags take a value.
