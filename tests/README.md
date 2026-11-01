# Tests

The `.feature` files in `features/` are Cyclix's functional spec. Each file covers one thing Cyclix does, and its `Feature:` title names that behaviour. A new scenario goes in the file for the capability it describes. Each feature file's steps are in the file of the same name in `steps/`, such as `steps/test_config.py` for `features/config.feature`. The sandbox feature is the exception: see "The sandbox".

`harness/` holds the checks of the test footing and the repository, not of Cyclix's behaviour: the fakes, the recorded `gh` output shapes, the installed package, the README and the links in the docs. Each feature file there sits beside its steps file, which names the feature by its path.

`unit/` holds unit tests, kept for rules a scenario cannot reach cheaply.

Every test file needs a basename unique across `steps/`, `harness/` and `unit/`, because the test folders are not packages. Name a unit file after the rules it checks, such as `unit/test_config_rules.py` beside `steps/test_config.py`.

## Tags

A scenario tagged `@sandbox` runs against real GitHub. See "The sandbox" below.

A feature tagged `@live` is checked by hand against Cyclix's own repo and board, and recorded in the PR that adds it. No steps file binds it, so pytest never runs it.

## The fake world

Each scenario gets a `world` fixture (`fakes/world.py`): a temporary directory holding the fake GitHub world, a state directory, a bare git remote with one commit on `main`, and a test config. Steps read and change it through methods such as `world.add_issue(...)`, `world.board_state(n)` and `world.add_fault(...)`.

- `fakes/bin/gh` supports only the `gh` commands listed in `docs/src/content/docs/design/engine.md`, "The adapters". Anything else exits 2 with "fake gh: unsupported command". Every call is appended to `calls.jsonl`.
- `fakes/bin/fake-agent` follows `agent-script.json`, one entry per call, and prints the lines of `claude -p --output-format stream-json --verbose`: an init line, one assistant line per turn, then the result line. It records each call's arguments and environment in `agent-calls.jsonl`, with a value only for the `GIT_*` and `GH_CONFIG_DIR` names the engine sets, so no real login lands in the file. The agent sees only an allowed environment, so the test config lists `CYCLIX_FAKES_DIR` in `[agent] pass_env` for the fake to find its world.
- `fakes/bin/systemctl` accepts only `--user daemon-reload`, `--user enable --now <unit>` and `--user disable --now <unit>`, and changes nothing. Every call is appended to `systemctl.jsonl`.
- `fakes/runner.py` runs `cyclix` with `run_cyclix(world, *args)`. `PATH` finds the fakes first. `CYCLIX_CONFIG`, `CYCLIX_STATE_DIR` and `XDG_CONFIG_HOME` point into the world, so systemd units land in `xdg-config/systemd/user/`.

## Shared steps

These steps are defined in `conftest.py`, so any feature can use them.

| Phrase | Kind | What it does |
| --- | --- | --- |
| `an issue #N titled "T" in state "S" on the board` | Given | Adds an open issue and a board item in state S, which is a board option name such as "Ready". |
| `an issue #N in state "S" on the board` | Given | The same, with the title "Issue N". |
| `a PR for #N is open` | Given | Adds an open PR on the branch `cyclix/<N>-<slug of the title>` with the body `Closes #N`. |
| `a PR for #N is open` | Then | Checks that an open PR exists on a `cyclix/<N>-` branch. |
| `gh call "C" fails with exit E once` | Given | Makes the next call whose arguments start with C exit E. The leading `gh call` is optional. |
| `"C" fails with exit E and stderr "M" once` | Given | The same, and prints M on stderr. |
| `the agent answers "A"` | Given | Adds a fake agent step that answers A and exits 0. |
| `the agent writes a plan, then commits a change` | Given | Adds a plan answer, then a build step that commits `change.txt` and answers with a PR body: the template's five sections, with no `Closes` line. |
| `the agent writes a plan, then stages every file and commits a change` | Given | The same, but the build step stages every file in the worktree, as `git add -A` does. |
| `the config names an instruction folder holding "A" and "B"` | Given | Writes each named file in the world's `instructions/` folder and names that folder in `[agent] instructions`. |
| `the engine's environment holds A, B and C` | Given | Sets each named variable in the engine's environment, so a scenario can check that the agent or the gate does not see it. |
| `one pass runs` | When | Runs `cyclix run` and keeps it as `result`. |
| `I run "cyclix ARGS"` | When | Runs `cyclix` with ARGS as a subprocess against the world. Its result is `result`. |
| `the board shows #N in "S"` | Then | Checks the item's state on the board. |
| `the event log holds a stage_run event for #N at stage "S" with outcome "O"` | Then | Reads `events/test.jsonl` in the state directory. |
| `the S event's outcome is "O"` | Then | Checks that the event log holds exactly one event at stage S, with outcome O. |
| `it exits N` | Then | Checks the exit code of `result`. |
| `it prints "T"` | Then | Checks that T is a whole line of `result`'s stdout. Write a quote inside T as `\"`. |
| `it logs "T"` | Then | Checks that T is a whole line of `result`'s stderr, where `cyclix run` writes its log records. Write a quote inside T as `\"`. |
| `a log line starts with "T"` | Then | Checks that a line of `result`'s stderr starts with T. |
| `it writes nothing` | Then | Checks that `result`'s stdout and stderr are both empty. |

## The sandbox

`features/sandbox.feature` runs against real GitHub: a private repository and board, named in the tenant config `docs/examples/sandbox.toml`. Its steps are in `sandbox/test_sandbox.py`. Scenarios tagged `@sandbox` are skipped unless `CYCLIX_SANDBOX=1`. They use the real `gh` and the real `claude`, so they need a `gh` login (or `GH_TOKEN`) with access to the sandbox repo and board, and a signed-in `claude`. Each one clears what an earlier run left, and closes and deletes what it made.

```
CYCLIX_SANDBOX=1 uv run pytest -m sandbox
```

`scripts/record_gh_shapes.py` records the shape of each `gh` command's output from the sandbox into `fixtures/gh-shapes/`. `harness/gh_shapes.feature` runs the fake gh on the same commands and fails if its output has another shape. When real `gh` changes, run the script, commit the new recordings, and change the fake until the scenario passes.

The workflow `.github/workflows/sandbox.yml` does both, by hand and weekly. It needs two secrets in the `sandbox` environment, which only runs from `main` can read: `CYCLIX_SANDBOX_TOKEN` (a token that can read and write the sandbox repo's contents, issues and PRs, the organization's projects, and the administration settings of `ambitioushq/cyclix`, read-only, because the script records the branch protection of Cyclix's own `main`) and `CLAUDE_CODE_OAUTH_TOKEN` (made with `claude setup-token`, so the agent runs on a Claude subscription, not the API).
