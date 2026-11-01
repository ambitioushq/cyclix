# Cyclix

[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/ambitioushq/cyclix/badge)](https://scorecard.dev/viewer/?uri=github.com/ambitioushq/cyclix)

Cyclix turns issues into pull requests (PRs) without a person at the keyboard. It takes an issue from a GitHub Projects board and runs it through its stages: a coding agent plans and builds the change, and your checks test it. Cyclix then opens a PR. When a person merges or closes the PR, Cyclix moves the item on the board.

**Status: pre-release.** Commands, config keys and output can change between versions.

## How it works

1. A person writes an issue and moves it to Ready on the board.
2. On each pass (one run of `cyclix run`), Cyclix takes the oldest Ready item, unless a limit in the config holds it back. It runs the item through four stages in order: plan, build, gate and PR. The gate is the list of check commands you set, such as your linter and tests.
3. When every stage passes, the item moves to In review with its PR. When a stage stops, the item moves to Parked, and a comment on the issue says why.
4. A person reviews the PR and merges or closes it. A later pass moves the item to Done or Parked.

[How Cyclix works](docs/concepts/how-cyclix-works.md) covers each stage, the work states and where Cyclix keeps its data.

## What you need

- Python 3.14 or later.
- git.
- The GitHub CLI, `gh`, signed in with the `project` scope. Cyclix reads and moves board items through it.
- Claude Code 2.1.259 or later, signed in. It is the coding agent.
- A GitHub repository. Its base branch must be protected by a ruleset (see step 5 of [Get started](#get-started)). GitHub offers rulesets on a free plan only for public repositories.
- A GitHub Projects board for the repository. Its Status field needs one option for each of Cyclix's six work states.
- For `cyclix install`: Linux with a systemd user session.
- A separate user account on the host, holding only the tokens Cyclix needs. Run Cyclix as that user. The agent and the gate run as the same user, and code they run can read any file that user can read, such as a saved GitHub login. A passing `cyclix check` does not change this. [Isolation](docs/design/isolation.md) explains.

## Install Cyclix

Cyclix is not on PyPI. Install it from this repository with `uv`:

```sh
uv tool install git+https://github.com/ambitioushq/cyclix
```

Or with `pipx`. Add `--python python3.14` if your default Python is older:

```sh
pipx install git+https://github.com/ambitioushq/cyclix
```

`cyclix --version` then prints the version, such as `cyclix 0.0.1`.

## Get started

A **tenant** is one repository, its board and one config file. These steps set up a tenant named `storefront` for the repository `acme/storefront`.

1. Download the example config to the place Cyclix looks for it:

   ```sh
   curl -fsSL --create-dirs -o ~/.config/cyclix/storefront.toml \
     https://raw.githubusercontent.com/ambitioushq/cyclix/main/docs/examples/tenant.toml
   ```

   If you set `XDG_CONFIG_HOME`, use that folder in place of `~/.config`. To keep the file elsewhere, set `CYCLIX_CONFIG` to its path.

2. Edit the file. Change these keys, and leave the rest as they are for now:

   - `[tracker] owner` and `project`: the board's owner and number.
   - `[codehost] repo` and `base`: the repository and its base branch.
   - `[gate] commands`: the checks a change must pass, such as your tests.

   [Configuration](docs/reference/configuration.md) explains every key.

3. On the board, give the Status field these six options: Ready, In progress, In review, Parked, Needs decision and Done. To use other names, change them under `[tracker.states]` in the config.

4. Give `gh` the `project` scope:

   ```sh
   gh auth refresh -s project
   ```

5. In the repository's settings, add a branch ruleset for the base branch. Set it to Active, and turn on "Require a pull request before merging", "Block force pushes" and "Restrict deletions".

6. Check the tenant:

   ```sh
   cyclix check --tenant storefront
   ```

   When every line ends in `ok`, the tenant is ready.

7. Move one issue to Ready on the board.

8. Make one pass:

   ```sh
   cyclix run --tenant storefront
   ```

   The pass prints nothing when it goes well. The item moves to In review, with a PR. For issue 12, "Add the state core", the branch is `cyclix/12-add-the-state-core`.

9. On Linux, run a pass every 10 minutes on a systemd timer:

   ```sh
   cyclix install --tenant storefront
   ```

   The timer does not use your shell's `PATH`. It gets systemd's default `PATH` for user services. So `gh`, `git`, `claude` and your gate commands must be in a directory on that path, or a pass that works by hand can fail on the timer. [Commands](docs/reference/commands.md#cyclix-install) explains.

## When `cyclix check` fails

Each failed check prints a `FAIL:` line, then a `fix:` line that says what to do. Here the board has no "Blocked" option, but the config names it for the Needs decision state:

```text
board option "Parked" for parked: ok
FAIL: board option "Blocked" for needs_decision: not on the Status field
  fix: add "Blocked" to the board's Status field, or change [tracker.states] needs_decision in ~/.config/cyclix/storefront.toml
board option "Done" for done: ok
```

The `fix:` line names the full path of your config file. Do what it says, then run `cyclix check` again. [Commands](docs/reference/commands.md#the-checks-with-the-fix-for-each-failure) lists every check and its fix.

## What each command does

Each command takes `--tenant NAME`. Cyclix reads `~/.config/cyclix/NAME.toml`, or the file in `CYCLIX_CONFIG`.

- `cyclix check --tenant storefront` checks that the tenant is ready to run. `--verbose` logs each step.
- `cyclix run --tenant storefront` makes one pass. `--verbose` logs each step.
- `cyclix install --tenant storefront` runs a pass every 10 minutes on a systemd user timer. `--every` sets another interval, `--dry-run` prints the units and changes nothing, and `--force` replaces units that differ.
- `cyclix uninstall --tenant storefront` stops the timer and removes its units.

[Commands](docs/reference/commands.md) gives each command's output and exit codes.

## Where it runs

- Linux runs every command.
- On macOS, `check` and `run` work. `install` and `uninstall` are coming soon, because they need systemd.
- Windows is not supported.

## Read more

- To run Cyclix: [how it works](docs/concepts/how-cyclix-works.md), [the config](docs/reference/configuration.md) and [the commands](docs/reference/commands.md).
- To work on its code: [the architecture](docs/design/architecture.md), [the engine](docs/design/engine.md), [the tests](docs/design/testing.md) and [isolation](docs/design/isolation.md).
- [The decisions](docs/adr/README.md): one record for each settled call.
- [All the documentation](docs/README.md).

## Contribute or report a vulnerability

- To contribute, read [CONTRIBUTING.md](CONTRIBUTING.md).
- To report a vulnerability, follow [SECURITY.md](SECURITY.md).

## Licence

Apache-2.0. See [LICENSE](LICENSE).
