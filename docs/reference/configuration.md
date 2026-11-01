# Configuration

Each tenant has one TOML file. A tenant is one repository with its project board (see [How Cyclix works](../concepts/how-cyclix-works.md)). Run `cyclix check` after you edit the file. It reports a missing key, an unknown key, or a board option name that is not on the board.

## Where Cyclix finds the file

Cyclix looks in this order and uses the first that applies:

1. The path in `CYCLIX_CONFIG`.
2. `$XDG_CONFIG_HOME/cyclix/<tenant>.toml`, when you pass `--tenant <tenant>`.
3. `~/.config/cyclix/<tenant>.toml`, when you pass `--tenant <tenant>` and `XDG_CONFIG_HOME` is not set.

With none of these, the command stops and says to set `CYCLIX_CONFIG` or pass `--tenant`.

The config holds a tenant's settings. The data Cyclix builds up while it runs lives in the state directory, which is not in the config. It is `CYCLIX_STATE_DIR` when set, else `$XDG_STATE_HOME/cyclix`, else `~/.local/state/cyclix`.

## The full example

Every key is required, except the `[limits.wip]` table and `[agent] instructions`. An unknown key is an error, so a typo never passes silently. The same file is in [`docs/examples/tenant.toml`](../examples/tenant.toml).

```toml
[tenant]
name = "storefront"

[tracker]
kind = "github"
owner = "acme"
project = 1
status_field = "Status"

[tracker.states]           # Cyclix state -> the board's option name
ready = "Ready"
in_progress = "In progress"
in_review = "In review"
parked = "Parked"
needs_decision = "Needs decision"
done = "Done"

[codehost]
kind = "github"
repo = "acme/storefront"
base = "main"

[agent]
# The engine adds the model, the caps and the permission flags for each stage. The
# agent runs in dontAsk mode: a tool call outside the stage's list is refused.
# See docs/reference/configuration.md.
command = ["claude", "-p"]
timeout_minutes = 60
pass_env = []
# instructions = "~/agent-rules/storefront"   # optional: files copied into each run

[agent.plan]
model = "claude-opus-5-5"
max_turns = 30
max_budget_usd = 2.0
tools = ["Read", "Grep", "Glob"]

[agent.build]
model = "claude-sonnet-5-5"
max_turns = 100
max_budget_usd = 5.0
tools = ["Read", "Grep", "Glob", "Edit", "Write",
         "Bash(git add *)", "Bash(git commit *)", "Bash(git status*)",
         "Bash(git diff*)", "Bash(git log*)", "Bash(uv run *)"]

[gate]
commands = [["uv", "run", "ruff", "check"], ["uv", "run", "ruff", "format", "--check"], ["uv", "run", "pytest", "-q"]]
timeout_minutes = 10
pass_env = []

[limits]
runs_per_day = 6

[limits.wip]               # Cyclix state -> the most items it may hold
in_review = 5
```

## `[tenant]`

| Key | Type | Meaning |
| --- | --- | --- |
| `name` | string | The tenant's name. Letters, digits, `.`, `_` and `-`, starting with a letter or digit. It names the lock file, the event log and the systemd units. |

## `[tracker]`

The tracker is where the work items live. Only `github` is supported, and it means a GitHub Projects board.

| Key | Type | Meaning |
| --- | --- | --- |
| `kind` | string | Must be `"github"`. |
| `owner` | string | The GitHub user or organization that owns the board. |
| `project` | whole number, 1 or more | The board's number. |
| `status_field` | string | The name of the board's single-select field that holds an item's state. |

Cyclix keeps only items whose issue belongs to `[codehost] repo`. It ignores a draft, a PR, an issue of another repository, and an item whose option is not listed under `[tracker.states]`.

### `[tracker.states]`

Each key is one of Cyclix's six work states (see [the work states](../concepts/how-cyclix-works.md#the-six-work-states)). Each value is the name of the option on the board's Status field. `cyclix check` reports any name that is not on the board.

| Key | Example value |
| --- | --- |
| `ready` | `"Ready"` |
| `in_progress` | `"In progress"` |
| `in_review` | `"In review"` |
| `parked` | `"Parked"` |
| `needs_decision` | `"Needs decision"` |
| `done` | `"Done"` |

## `[codehost]`

The code host is where the repository and its PRs live.

| Key | Type | Meaning |
| --- | --- | --- |
| `kind` | string | Must be `"github"`. |
| `repo` | string | The repository, written `owner/name`. |
| `base` | string | The branch that PRs target. Cyclix starts each branch from `origin/<base>`. |

## `[agent]`

The agent is the coding agent that plans and builds. Only Claude Code is supported.

| Key | Type | Meaning |
| --- | --- | --- |
| `command` | list of strings | The program, followed only by `-p`, `--print` and `--effort <level>`. Any other argument is refused, because Cyclix sets the model, the caps, the permissions and the output format itself. |
| `timeout_minutes` | whole number, 1 or more | How long one agent call may run. At the limit the agent gets SIGINT, so it can stop its own tools and report what it cost so far. After 30 seconds it is killed. |
| `pass_env` | list of names | Extra environment variables the agent may see. Usually empty. See [What the agent and the gate see](#what-the-agent-and-the-gate-see). |
| `instructions` | string, optional | A folder of instruction files. See below. |

### `[agent.plan]` and `[agent.build]`

Each stage that calls the agent has its own table.

| Key | Type | Meaning |
| --- | --- | --- |
| `model` | string | The model name or alias, passed as `--model`. |
| `max_turns` | whole number, 1 or more | The most turns the agent may take. |
| `max_budget_usd` | number above 0 | The most the call may cost. |
| `tools` | list of strings | The tools the agent may use in this stage. Each entry is a tool name with an optional rule in brackets, such as `Read` or `Bash(git commit *)`. A call outside the list is refused. |

The caps stop a run that has gone wrong. They are not meant to squeeze a normal run. A call that hits a cap ends with the reason "turn cap reached" or "budget cap reached". With a Claude subscription login, the budget is what the tokens would cost at API prices, not a charge, but the tokens still use up the subscription's limits. Claude Code checks the budget when a turn ends, so a call can go past it by the cost of one turn.

A useful command that is missing from `tools` is refused, and the run fails until you add it. The list is not a security boundary: `Bash(uv run *)` lets the agent run any Python it writes. [Isolation](../design/isolation.md) explains.

### `instructions`

`[agent] instructions` names a folder of instruction files, such as `CLAUDE.md`, that you keep outside the repository. Most tenants keep these files in the repository and leave the key out.

The path is absolute or starts with `~`, and the folder must exist. Admission copies each file into the run's worktree at the same relative path, before the plan stage. It copies the content, not a link. No commit includes the copied files. If the repository already tracks a file at one of those paths, admission writes nothing and parks the item, and the comment names the file. The reasons are in [ADR-0014](../adr/0014-copy-private-instruction-files-from-one-configured-folder.md).

## `[gate]`

The gate is the set of commands that a change must pass before Cyclix opens a PR.

| Key | Type | Meaning |
| --- | --- | --- |
| `commands` | list of commands | Each command is a list of strings. They run in order in the run's worktree. The first to fail parks the item. |
| `timeout_minutes` | whole number, 1 or more | How long each command may run. A command past the limit is stopped, with everything it started, and counts as a failed check. |
| `pass_env` | list of names | Extra environment variables the gate may see. Usually empty. |

Make the gate match your CI, so a PR that passes the gate passes CI. The gate has no fix rounds: a failure parks the item.

## `[limits]`

| Key | Type | Meaning |
| --- | --- | --- |
| `runs_per_day` | whole number, 0 or more | The most runs the tenant may begin on one UTC date. With 0, no run begins. |

### `[limits.wip]`

This table is optional. It sets limits on work in progress (WIP): the most items a column may hold. When any column is full, admission waits (see [How Cyclix works](../concepts/how-cyclix-works.md#what-happens-in-one-pass)). A state left out has no limit.

| Key | Meaning |
| --- | --- |
| `in_progress` | Can only be 1. |
| `in_review` | The most PRs that may wait for a person. |
| `parked` | The most parked items. |
| `needs_decision` | The most items waiting for a call. |

Each limit is a whole number of 1 or more. Ready and Done take no limit.

## What the agent and the gate see

The agent and the gate do not get Cyclix's own environment. They get an allow-list:

- Passed through when set: `PATH`, `HOME`, `USER`, `LOGNAME`, `LANG`, `LC_ALL`, `TERM` and `TMPDIR`.
- For the agent only, passed through when set: the Claude login, which is `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_API_KEY` and `CLAUDE_CONFIG_DIR`.
- Set by Cyclix: `GH_CONFIG_DIR` pointing at an empty folder, so `gh` finds no login. `GIT_CONFIG_GLOBAL=/dev/null` and `GIT_CONFIG_NOSYSTEM=1`, so git reads no credential helper. `GIT_TERMINAL_PROMPT=0`. And the author and committer name and email, so commits carry the identity git would have used.
- The names in `pass_env`.

The config is refused if `pass_env` names a GitHub token (`GH_TOKEN`, `GITHUB_TOKEN`, `GH_ENTERPRISE_TOKEN` or `GITHUB_ENTERPRISE_TOKEN`), `GH_CONFIG_DIR`, `SSH_AUTH_SOCK`, a program that git or SSH would ask for a credential (`GIT_ASKPASS`, `SSH_ASKPASS`, `GIT_SSH` or `GIT_SSH_COMMAND`), `GIT_TERMINAL_PROMPT`, or any name that starts with `GIT_CONFIG`. The gate's list also may not name the Claude login. A tenant whose tests need `DATABASE_URL`, for example, lists it in `[gate] pass_env`. [ADR-0013](../adr/0013-keep-code-host-credentials-out-of-the-agent-and-the-gate.md) has the reasons.

## Values Cyclix checks for form

The engine puts some config values into commands and paths. Each must have the form it expects, and none may start with `-`: the tenant name, `tracker.owner`, `codehost.repo`, `codehost.base`, each stage's `model`, and each `pass_env` name. So no config can turn off the limits above.

## Time limits that are not in the config

A `gh` call may take 60 seconds. A git call that uses the network (clone, fetch, push) may take 5 minutes, and a local git call may take 1 minute. The first clone goes through `gh repo clone`, with the 5 minutes. A call past its limit fails, and its whole process group is killed. Cyclix does not retry: the next timer run makes the pass again.
