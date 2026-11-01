# ADR-0008: Run the agent without approval prompts, with a tool list for each stage, and allow only listed flags in its command

**Status:** Accepted

**Date:** October 2026

## Context

An unattended agent cannot stop to ask before it edits a file or runs `git`. The first version let the agent make every tool call. The agent reads text that can carry instructions, so whoever wrote that text can direct what the agent does.

## Decision

The engine runs the agent in a mode that refuses any tool call outside an allow list and never asks. Each stage has its own tool list in the tenant config. The engine also limits the agent to:

- Its working directory for file tools.
- No settings files, repository hooks or repository tool servers.
- Only the tools in the stage's list. A stage with no shell rule has no shell.
- A turn limit and a spend limit for each stage.

The plan stage may read and search files. The build stage may also edit and write files, run some `git` commands and run the tenant's test commands. `git push` and the code host's program are on no list, because the engine runs them.

The agent command in the config is a program followed only by a small set of flags: print mode and an effort level. The engine adds every other flag, and the config is refused if the command has any other argument. A config value that goes into a command or a path must have the form the engine expects, and none may start with `-`.

With Claude Code, the mode is `--permission-mode dontAsk --permission-prompts none`. The limits are `--restricted`, `--strict-mcp-config`, `--tools`, `--max-turns` and `--max-budget-usd`. The allowed command flags are `-p`, `--print` and `--effort <level>`.

## Consequences

- A useful command that is missing from a list is refused, and the run fails until a person adds it to the tenant config.
- The list is not the security boundary. A rule such as `Bash(uv run *)` lets the agent run any Python it writes. The list is a second layer.
- The build prompt lists the stage's tools and asks for one shell command at a time. A joined command is refused whole if any part of it is off the list.
- With Claude Code, `--bare` stays off, because it needs an API key and not a subscription login.

## Alternatives Considered

**Allow every tool call.** Replaced. Anything the agent reads could steer it to any action.

**A list of refused flags.** Rejected. It missed flags such as `--plugin-dir`, whose plugins can bring hooks. It also missed `--`, which makes every later argument plain text, and a last flag that takes a value, which would swallow the engine's `--model`. An allow list knows which of its flags take a value.
