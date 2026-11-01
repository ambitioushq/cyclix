# ADR-0012: The agent runs in dontAsk mode with a tool list for each stage, and its command takes only allow-listed flags

**Status:** Accepted

**Date:** October 2026

## Context

Print mode cannot ask before it edits a file or runs `git`, so an unattended agent must act without asking. The first version ran Claude Code with `--permission-mode bypassPermissions`, which allows every tool call. Everything the agent reads can carry instructions: the issue, the repository's files, review comments. So the design assumes an agent can be made to try anything its process is able to do.

## Decision

The engine runs the agent with `--permission-mode dontAsk --permission-prompts none`. Each stage has its own tool list in the tenant config, and a tool call outside the list is refused, not allowed. The engine also passes:

- `--restricted`, so Claude Code ignores the user, project and local settings files, the repository's hooks do not run, and the file tools are confined to the working directory.
- `--strict-mcp-config`, so the repository's MCP servers do not load.
- `--tools`, built from the stage's list, so a stage with no `Bash` rule has no shell at all.
- `--max-turns` and `--max-budget-usd`, set for each stage.

The plan stage may use `Read`, `Grep` and `Glob`. The build stage may also use `Edit`, `Write`, a few `git` commands and the tenant's own test commands. `git push` and `gh` are on no list, because the engine pushes and opens the PR itself.

The agent command in the config may hold only the program followed by `-p`, `--print` and `--effort <level>`. The engine adds every other flag after it. The config is refused if the command holds any other argument.

## Consequences

- A command outside a stage's list is refused. A useful command missing from the list makes that run fail until someone adds it to the list.
- The list is not the security boundary. `Bash(uv run *)` lets the agent run any Python it writes, and that Python can do anything the process can. The list is a second layer: it stops the agent from running a command such as `gh pr merge` because a file told it to, and it writes down what each stage is for.
- The build prompt lists the stage's tools and asks the agent to run each shell command on its own. In a test, the agent joined `printf`, `git add` and `git commit` into one command, the whole command was refused, and the agent gave up.
- Each entry in `tools` and every config value that the engine puts in a command or path must have its expected form, and none may start with `-`. So no config can turn these limits off.
- `--bare` stays off. It needs an API key, not a subscription login.

## Alternatives Considered

**`bypassPermissions`.** Used first. Replaced because it allows every tool call.

**A list of refused flags in the agent command.** Tried first. It kept missing flags such as `--plugin-dir`, whose plugins can bring hooks. It also missed two ways an argument can defeat the engine's flags without naming them. `--` makes every argument after it plain text. And Claude Code reads the argument after a flag that takes a value as that value, even when it starts with `-`, so a command that ends in such a flag would take the engine's `--model` as its value. An allow-list knows which of its flags take a value, and the config is refused when one has none.
