# ADR-0012: The agent runs in dontAsk mode with a tool list for each stage, and its command takes only allow-listed flags

**Status:** Accepted

**Date:** October 2026

## Context

Print mode cannot ask before it edits a file or runs `git`, so an unattended agent must act without asking. The first version used `--permission-mode bypassPermissions`, which allows every tool call. The agent reads text that can carry instructions, so it can be steered.

## Decision

The engine runs the agent with `--permission-mode dontAsk --permission-prompts none`. Each stage has its own tool list in the tenant config, and a call outside it is refused. The engine also passes:

- `--restricted`: settings files are ignored, repository hooks do not run, and file tools stay in the working directory.
- `--strict-mcp-config`: the repository's MCP servers do not load.
- `--tools`, built from the stage's list. A stage with no `Bash` rule has no shell.
- `--max-turns` and `--max-budget-usd` for each stage.

The plan stage may use `Read`, `Grep` and `Glob`. The build stage may also use `Edit`, `Write`, some `git` commands and the tenant's test commands. `git push` and `gh` are on no list, because the engine does them.

The agent command in the config is a program followed only by `-p`, `--print` and `--effort <level>`. The engine adds every other flag. Any other argument is refused. Config values that go into a command or path must have their expected form, and none may start with `-`.

## Consequences

- A useful command missing from a list is refused, and the run fails until it is added.
- The list is not the security boundary. `Bash(uv run *)` lets the agent run any Python it writes. The list is a second layer.
- The build prompt lists the stage's tools and asks for one shell command at a time, because a joined command is refused as a whole if any part is off the list.
- `--bare` stays off. It needs an API key, not a subscription login.

## Alternatives Considered

**`bypassPermissions`.** Replaced. It allows every tool call.

**A list of refused flags.** Rejected. It missed flags such as `--plugin-dir`, whose plugins can bring hooks. It also missed `--`, which makes later arguments plain text, and a trailing flag that takes a value, which would swallow the engine's `--model`. An allow-list knows which of its flags take a value.
