---
title: Commands
---

`cyclix` has four commands: `check`, `run`, `install` and `uninstall`. `cyclix --version` prints the version, such as `cyclix 0.0.1`.

Every command exits with one of three codes:

| Code | Meaning |
| --- | --- |
| 0 | It succeeded. |
| 1 | A check or a run failed. |
| 2 | The command was used wrongly, such as an unknown command or a missing flag. |

`--tenant NAME` picks the tenant. Cyclix then reads `~/.config/cyclix/NAME.toml`, or the file in `CYCLIX_CONFIG`. See [Configuration](/reference/configuration/).

## Turn on shell completion

Shell completion lets the Tab key complete `cyclix`'s commands and flags in bash, zsh and fish. It needs the optional `extras` group, which installs [argcomplete](https://github.com/kislyuk/argcomplete). A plain install of Cyclix leaves it out (see [ADR-0008](/adr/0008-offer-shell-completion-through-an-optional-argcomplete-extra/)).

1. Install Cyclix with the `extras` group, and put argcomplete's `register-python-argcomplete` command on your `PATH`:

   ```sh
   uv tool install --with-executables-from argcomplete "cyclix[extras] @ git+https://github.com/ambitioushq/cyclix"
   ```

   With `pipx`, run `pipx install --include-deps "cyclix[extras] @ git+https://github.com/ambitioushq/cyclix"`.

2. Register `cyclix` with your shell:

   | Shell | What to do |
   | --- | --- |
   | bash | Add `eval "$(register-python-argcomplete cyclix)"` to `~/.bashrc`. |
   | zsh | Add `eval "$(register-python-argcomplete cyclix)"` to `~/.zshrc`, after the line that runs `compinit`. |
   | fish | Run `register-python-argcomplete --shell fish cyclix > ~/.config/fish/completions/cyclix.fish` once. |

3. Open a new shell.

## `cyclix check`

```sh
cyclix check [--tenant NAME] [--verbose]
```

Checks that a tenant is ready to run. It changes nothing, except that it creates the state directory when it is missing.

It prints one line to stdout for each check, in the order below. A check that passes prints `<what was checked>: ok`. A check that fails prints `FAIL: <what was checked>: <reason>`, then a second line, `  fix: <what to do>`. A check that needs an earlier check that failed prints `skipped: <what was checked>: needs <the earlier check>`. A skipped check does not change the exit code. The exit code is 1 when any check fails.

`--verbose` also logs each step at DEBUG to stderr.

### The checks, with the fix for each failure

**1. The config loads.**

| Line | Fix |
| --- | --- |
| `config for tenant <name>: ok` | |
| `FAIL: config: <reason>` | The fix line is one of: `pass --tenant NAME, or set CYCLIX_CONFIG to the config file's path`, when Cyclix has no path to read; `write the tenant config at <path>`, when the file does not exist; or `edit <path>`, when the file is wrong. The reason names the key. |

**2. `gh` is installed and signed in.**

| Line | Fix |
| --- | --- |
| `gh is signed in: ok` | |
| `FAIL: gh: not on PATH` | `install gh, the GitHub CLI, and put it on PATH` |
| `FAIL: gh: not signed in` | `run "gh auth login"` |

**3. The state directory can be written.**

| Line | Fix |
| --- | --- |
| `state directory <path>: ok` | |
| `FAIL: state directory <path>: not writable: <error>` | `make <path> writable, or set CYCLIX_STATE_DIR to a directory you can write` |

**4. The agent command is on `PATH`.** It checks the first word of `[agent] command`.

| Line | Fix |
| --- | --- |
| `agent command <program>: ok` | |
| `FAIL: agent command <program>: not on PATH` | `install it, or change [agent] command in <config path>` |
| `skipped: agent command: needs the config` | Fix the config first. |

**5. The board has an option for every work state.** It prints one line for each of the six states.

| Line | Fix |
| --- | --- |
| `board option "<name>" for <state>: ok` | |
| `FAIL: board <owner>/<project>: cannot read it: <gh error>` | `check [tracker] owner and project in <config path>; if they are right, run "gh auth refresh -s read:project"` |
| `FAIL: board <owner>/<project>: no single-select field "<status_field>"` | `add a single-select field "<status_field>" to the board, or change [tracker] status_field in <config path>` |
| `FAIL: board option "<name>" for <state>: not on the <status_field> field` | `add "<name>" to the board's <status_field> field, or change [tracker.states] <state> in <config path>` |

**6. The base branch is protected.** The branch must require a pull request and refuse force-pushes and deletion. A rule counts whether it comes from classic branch protection or from a ruleset. Reading classic protection needs admin rights, so a ruleset that holds all three rules is enough on its own.

| Line | Fix |
| --- | --- |
| `protection of the base branch "<base>": ok` | |
| `FAIL: protection of the base branch "<base>": <gaps>` | `in the settings of <repo>, add a ruleset for "<base>" with <rules>`. The gaps are `lets a change skip a pull request`, `allows force-pushes` and `allows deletion`, and the rules are `"Require a pull request before merging"`, `"Block force pushes"` and `"Restrict deletions"`. |
| `FAIL: protection of the base branch "<base>": cannot read it: <gh error>` | `protect "<base>" with a ruleset in the settings of <repo>, or sign gh in as an admin of <repo>` |

GitHub shows neither protection nor rulesets for a private repository on a free plan. There the fix is `make <repo> public, or move its owner to a paid GitHub plan; then add a ruleset for "<base>" in the settings of <repo>`.

### When a check is skipped

The board check and the branch check need both the config and a signed-in `gh`. The agent check needs the config. When what they need fails, they print `skipped: <what>: needs <the failed checks>`, such as `skipped: board acme/1: needs gh signed in`. When the config fails, the label has no owner and project, because the config is not known: `skipped: board: needs the config`.

## `cyclix run`

```sh
cyclix run [--tenant NAME] [--verbose]
```

Makes one pass for one tenant (see [How Cyclix works](/concepts/how-cyclix-works/#what-happens-in-one-pass)). A file lock at `<state directory>/<tenant>.lock` keeps two passes from overlapping. A pass that finds the lock held logs `another pass is running` and exits 0.

**What it prints.** Nothing to stdout. It writes log records to stderr, one line each. At the default level, INFO, a line is the message alone, and a pass that carries an item to a PR writes nothing. The messages you may see are:

| Message | Meaning |
| --- | --- |
| `another pass is running` | The lock is held. This pass did nothing. |
| `admission waits: <option> holds <n> of its WIP limit of <limit>` | A column is full, so nothing was admitted. |
| `the day's limit of <n> runs is reached` | The tenant has used `runs_per_day`. |
| `cyclix run: <error>` | The pass stopped on an error outside a stage, such as a failed board read. |
| `config: <reason>` | The config did not load. |

`--verbose` sets the level to DEBUG. Each line then starts with the level and the logger's name, as in `DEBUG cyclix.runner: admitted #12 as r-20261031-101500-12`. At DEBUG, Cyclix logs what the board read returned, each crashed run it ended, each claim it released, the item it admitted, and each stage's outcome, reason and duration. The `gh` adapter logs the first three words of each call, its exit code and its duration.

No log record holds a whole command line, a prompt, the body of an issue or comment, or the environment. A stage's reason is cut to 500 characters and its line breaks become spaces, so each record is one line. The event log is the record of what a run did. No log record goes into it.

**Exit code.** 0 when the pass completes, whatever the run's outcome. A parked item is not a failed pass. 1 when the config does not load or the pass stops on an error outside a stage.

## `cyclix install`

```sh
cyclix install --tenant NAME [--every SPAN] [--dry-run] [--force]
```

Runs the loop on a systemd user timer. It needs systemd on the host.

| Flag | Meaning |
| --- | --- |
| `--tenant NAME` | Required. The tenant's config must load and must name this tenant. |
| `--every SPAN` | How often the timer starts a pass. A systemd time span, such as `10min` or `1h`. The default is `10min`. |
| `--dry-run` | Prints the units and the commands it would run, and changes nothing. |
| `--force` | Replaces a unit that differs from the one Cyclix would write. |

**What it puts in the service.** `cyclix install` writes two files to `$XDG_CONFIG_HOME/systemd/user`, else `~/.config/systemd/user`:

- `cyclix-<tenant>.service`, a one-shot service. Its `ExecStart` is the absolute path of the `cyclix` command that ran `install`, then `run --tenant <tenant>`. Its `Environment` sets `CYCLIX_CONFIG` to the absolute path of the tenant's config.
- `cyclix-<tenant>.timer`. It starts the service 2 minutes after boot and then every `SPAN` after the service last started. The unit also sets `Persistent=true`, which has no effect, because systemd applies it only to timers that use `OnCalendar`. A pass missed while the host was off is not made up. The timer starts again 2 minutes after boot. It is wanted by `timers.target`.

The service sets no `PATH`, so it gets systemd's default for user services, not your shell's. `gh`, `git`, the agent command and the gate commands must be in a directory on that path.

Then it runs `systemctl --user daemon-reload` and `systemctl --user enable --now cyclix-<tenant>.timer`, and prints a line for each file written and each command run.

When a unit already exists and differs, `install` prints the difference and stops with exit 1, unless you pass `--force`. Errors go to stderr as `install: <reason>`.

systemd stops a user's timers at logout unless lingering is on for that user. To keep the timer running after logout, run `loginctl enable-linger <user>` as root.

## `cyclix uninstall`

```sh
cyclix uninstall --tenant NAME
```

Stops and disables the timer, removes both units, and reloads systemd. It prints `removed <path>` for each file removed, or `no units installed for tenant "<name>"` when there were none. Errors go to stderr as `uninstall: <reason>`.
