# ADR-0012: Run the agent in dontAsk mode with a tool list for each stage, and allow only listed flags in its command

**Status:** Accepted

**Date:** October 2026

## Context

Print mode cannot stop to ask before it edits a file or runs `git`, so an unattended agent has to act without asking. The first version used `--permission-mode bypassPermissions`, which allows every tool call. The agent reads text that can carry instructions, so something it reads can steer it.

## Decision

The engine runs the agent with `--permission-mode dontAsk --permission-prompts none`. Each stage has its own tool list in the tenant config. A call outside the list is refused. The engine also passes:

- `--restricted`. Settings files are ignored, repository hooks do not run, and the file tools stay in the working directory.
- `--strict-mcp-config`. The repository's MCP servers do not load.
- `--tools`, built from the stage's list. A stage with no `Bash` rule has no shell.
- `--max-turns` and `--max-budget-usd` for each stage.

The plan stage may use `Read`, `Grep` and `Glob`. The build stage may also use `Edit`, `Write`, some `git` commands and the tenant's test commands. `git push` and `gh` are on no list, because the engine runs them.

The agent command in the config is a program followed only by `-p`, `--print` and `--effort <level>`. The engine adds every other flag, and the config is refused if the command has any other argument. A config value that goes into a command or a path must have the form the engine expects, and none may start with `-`.

## Consequences

- A useful command that is missing from a list is refused, and the run fails until someone adds it.
- The list is not the security boundary. `Bash(uv run *)` lets the agent run any Python it writes. The list is a second layer.
- The build prompt lists the stage's tools and asks for one shell command at a time. A joined command is refused whole if any part of it is off the list.
- `--bare` stays off, because it needs an API key and not a subscription login.

## Alternatives Considered

**`bypassPermissions`.** Replaced. It allows every tool call.

**A list of refused flags.** Rejected. It missed flags such as `--plugin-dir`, whose plugins can bring hooks. It also missed `--`, which makes every later argument plain text, and a last flag that takes a value, which would swallow the engine's `--model`. An allow list knows which of its flags take a value.
