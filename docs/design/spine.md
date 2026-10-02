# The spine

The spine is Iteration 0: the smallest engine that takes a real issue to a merged PR. It has the state core, the GitHub adapters, the event log, the station runner, and a thin version of every station. When it is done, Cyclix becomes a tenant of its own loop, and every later arm replaces one thin station through that loop.

This document is the starting design. Each section marked **Open** is settled with the maintainer at the start of the issue that needs it, and this file is updated in that issue's PR.

## Done when

One real Cyclix issue, admitted from Cyclix's own board, reaches a merged PR through the spine running as a systemd timer on the host, and the event log holds one station-run event for each station it passed.

## What "thin" means

A thin station does real work in the simplest way that carries a real issue. A stub that did nothing could not build Cyclix's own issues.

| Station | Thin behaviour | Replaced by |
| --- | --- | --- |
| Admission | Takes the oldest open issue in Ready on the configured board, from the configured repo. Ignores everything not on the board. | The admission arm (the Ready contract, and promotion from Next) |
| Plan | One agent call that reads the issue and writes `plan.md` in the run folder. If the agent's answer starts with `STOP:`, the item is parked with that sentence as the reason. | The plan arm |
| Build | One agent call in the run's worktree, given the issue and the plan, that leaves its work committed on the run's branch. | The build arm |
| Gate | Runs the tenant's gate commands in the worktree. Records each command's exit code against the head SHA. Any failure parks the item: no fix rounds in the spine. | The gate arm |
| Red-team | Records itself as `skipped`. | The red-team arm |
| PR | Pushes the branch and opens a PR whose body says `Closes #<issue>`. Moves the item to In review. | The PR arm |
| Reconciler | For each item In review: merged moves it to Done; closed without merge moves it to Parked. | The reconciler arm |

## Package layout

```
src/cyclix/
  __init__.py        __version__
  __main__.py        python -m cyclix
  cli.py             argparse entry point
  config.py          load and validate the tenant TOML
  workstate.py       the work states and the transition table
  state/
    core.py          the StateCore protocol (the narrow interface)
    sqlite.py        the SQLite implementation
  adapters/
    gh.py            runs gh, parses JSON, raises one error type
    tracker.py       the Tracker protocol
    github_tracker.py
    codehost.py      the CodeHost protocol
    github_codehost.py
    agent.py         the Agent protocol
    claude_code.py
  events/
    schema.py        field names, outcome values, schema version
    log.py           the JSON-lines writer
  runner.py          the sweep and the station sequence
  stations/
    base.py          the Station protocol and the run context
    admission.py plan.py build.py gate.py redteam.py pr.py reconciler.py
  install.py         writes the systemd user units
tests/
  features/          Gherkin feature files, the spec
  steps/             pytest-bdd step definitions
  fakes/bin/gh       the fake gh
  fakes/bin/fake-agent
  fakes/world.py     the fake GitHub world both fakes read and write
  unit/              unit tests, only where a scenario cannot reach a rule
scripts/names_check.py
```

## Work states and who moves them

| From | To | Written by | When |
| --- | --- | --- | --- |
| Ready | In progress | Runner (admission) | The item is claimed for a run |
| In progress | In review | PR station | The PR is open |
| In progress | Parked | Any station | A STOP, a failed gate, an error, or a crashed run found by the sweep |
| In progress | Needs decision | Plan station | The plan needs a human call (not produced by the thin plan) |
| In review | Done | Reconciler | The PR merged |
| In review | Parked | Reconciler | The PR closed without merging |
| Parked, Needs decision | Ready | A human only | |
| Any | Done | A human, or GitHub closing the issue | The reconciler observes it and releases any claim |

The engine never makes a move that is not in this table. A human can make any move. The sweep reads the board each pass and adjusts SQLite to match it.

**Next comes with the admission arm.** Next is a staging state between Backlog and Ready. A human moves an issue there to say the work should be done soon. The admission arm then promotes it to Ready once it is safe to start: it is not a parent issue, it has no open blockers, it touches no files that work in flight touches, the review queue is under its cap, and it meets the Ready contract. An issue that fails the Ready contract goes to Needs decision. So a human decides what gets done, and the engine decides when it starts. The spine leaves this out: a human moves items straight to Ready, and the spine's config does not map the board's Next option, so the engine ignores it.

## The state core

The stations and the runner reach SQLite only through the `StateCore` protocol in `state/core.py`.

```python
class StateCore(Protocol):
    def claim(self, tenant: str, issue: int, run_id: str) -> bool: ...
    def release(self, tenant: str, issue: int) -> None: ...
    def claims(self, tenant: str) -> list[Claim]: ...
    def begin_run(self, run: RunStart) -> None: ...
    def set_phase(self, run_id: str, phase: str) -> None: ...
    def add_fields(self, run_id: str, fields: dict[str, object]) -> None: ...
    def end_run(self, run_id: str, outcome: str, reason: str) -> dict: ...
    def open_runs(self, tenant: str) -> list[RunState]: ...
    def record_check(self, run_id: str, sha: str, check: str, passed: bool) -> None: ...
    def best_verified(self, tenant: str, issue: int) -> str | None: ...
    def add_spend(self, tenant: str, usd: float, tokens: int) -> None: ...
```

```python
@dataclass(frozen=True)
class Claim:
    tenant: str
    issue: int
    run_id: str
    claimed_at: datetime

@dataclass(frozen=True)
class RunStart:
    run_id: str
    tenant: str
    issue: int
    station: str
    round: int = 1

@dataclass(frozen=True)
class RunState:
    run_id: str
    tenant: str
    issue: int
    station: str
    phase: str | None
    round: int
    started_at: datetime
    fields: dict[str, object]
```

The three are kept apart because each is filled by a different side at a different time. `Claim` is a row of `claims`. `RunStart` is what the caller knows when a station starts; the core stamps `started_at`. `RunState` is what the sweep reads back from an open station. Timestamps are in UTC.

**A run is one pass of an issue through the stations.** It keeps one `run_id`, which is also on the claim and names the run folder. Each station in the pass gets its own row in `runs`, unique on `(run_id, station, round)`, so the gate can run again in a later round of the same pass. A run has at most one open row at a time. `set_phase`, `add_fields`, `record_check` and `end_run` act on that open row, and each call on a run with no open row is refused.

**The fields build up into the event.** `begin_run` seeds the fields with `cyclix.tenant`, `cyclix.issue.id`, `cyclix.run.id`, `cyclix.station` and `cyclix.round`. `add_fields` merges more in, and adding `cyclix.round` also moves the `round` column, so the two can't disagree. `end_run` adds `cyclix.outcome` and `cyclix.outcome.reason`, and returns the whole dict for the event writer.

**The best verified commit** is the last commit whose checks all passed, counting only checks in a station row that ended with an outcome other than `crashed`. A row that is still open, or that crashed, may have stopped partway through its checks.

Tables in schema version 1:

- `meta(key, value)`: holds `schema_version`.
- `claims(tenant, issue, run_id, claimed_at)`, unique on `(tenant, issue)`.
- `runs(id, run_id, tenant, issue, station, phase, round, started_at, ended_at, outcome, fields_json)`, unique on `(run_id, station, round)`, and on `run_id` among rows with no `ended_at`. `fields_json` is the station-run event while it builds up.
- `checks(id, run_row, sha, check, passed, at)`. `run_row` is the `runs.id` of the station row that ran the check.
- `spend(tenant, day, usd, tokens)`, unique on `(tenant, day)`. `day` is the UTC date.

The file opens in WAL mode with a busy timeout of five seconds, and every write runs in one `BEGIN IMMEDIATE` transaction. A schema version newer than the code refuses to run. An older one is migrated by numbered SQL steps in code: step `i` takes the file from version `i` to `i + 1`, each in its own transaction.

**Durable phases.** Before an action that changes the outside world (a push, a PR open, a board move), the station calls `set_phase` with the action's name. After a crash, the sweep reads the phase and checks the outside world before acting again: it checks for an existing PR before opening one, and for the remote branch before pushing.

## The adapters

All GitHub calls go through `adapters/gh.py`, which runs `gh` with `--json` output where the command supports it, parses the JSON, and raises `GhError` with the exit code and stderr on failure. Nothing else in the engine calls `gh`.

**Tracker** (`Tracker` protocol): `ready_items()`, `item_state(issue)`, `set_state(issue, state)`, `issue(issue)`. The GitHub implementation uses:

- `gh project view <n> --owner <o> --format json` for the project ID
- `gh project field-list <n> --owner <o> --format json` for the Status field and its option IDs, cached for the pass
- `gh project item-list <n> --owner <o> --format json --limit <k>` for the items and their status
- `gh project item-edit --id <item> --project-id <p> --field-id <f> --single-select-option-id <opt>` to move an item
- `gh issue view <n> -R <repo> --json number,title,body,state,author,labels` to read an issue

**Code host** (`CodeHost` protocol): `push(worktree, branch)`, `open_pr(branch, title, body)`, `find_pr(branch)`, `pr_state(pr)`. The GitHub implementation uses `git push` and:

- `gh pr create -R <repo> --head <branch> --base <base> --title <t> --body-file <f>`
- `gh pr list -R <repo> --head <branch> --state all --json number,state,url`
- `gh pr view <n> -R <repo> --json state,mergedAt,closedAt,headRefOid,url`

**Agent** (`Agent` protocol): `run(prompt, cwd, model) -> AgentResult`, where the result holds the text answer, exit code, model, input and output tokens, cost, duration and turns. The Claude Code implementation runs the configured command (by default `claude -p --output-format json`) with the prompt on stdin and the worktree as its working directory, and parses the JSON result. That JSON has no top-level `model` key: the model's name is the one key of `modelUsage`. The prompt and the full answer are saved in the run folder. Only numbers reach the event.

## The state directory

Cyclix keeps everything it builds up while running in one state directory: the SQLite file, the event log, the run folders and the repo clones. It finds the directory in this order:

1. `CYCLIX_STATE_DIR`, if set.
2. Otherwise `$XDG_STATE_HOME/cyclix`, if `XDG_STATE_HOME` is set.
3. Otherwise `~/.local/state/cyclix`.

This follows the XDG convention, where a program keeps its settings under `~/.config` and the data it builds up under `~/.local/state`. The config file holds settings for one tenant, so the state directory is not in it. Tests set `CYCLIX_STATE_DIR` to a temporary directory for each scenario.

## Run folders and worktrees

Each run gets `runs/<tenant>/<issue>/<run_id>/` under the state directory, holding the prompts, answers, `plan.md` and gate output. The tenant's repo is cloned once into `repos/<tenant>/`. Each run adds a git worktree on the branch `cyclix/<issue>-<slug>`, removed when the item reaches Done or Parked.

## The event log, schema version 0

One JSON object per line in `events/<tenant>.jsonl` under the state directory. Each line is an OpenTelemetry log record:

```json
{
  "schema": "cyclix.event/0",
  "timestamp": "2026-10-02T14:03:11.204Z",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "body": "station_run",
  "resource": {"service.name": "cyclix", "service.version": "0.0.1"},
  "attributes": {
    "cyclix.tenant": "cyclix",
    "cyclix.issue.id": 12,
    "cyclix.run.id": "r-20261002-140211-12",
    "cyclix.station": "gate",
    "cyclix.outcome": "parked",
    "cyclix.outcome.reason": "gate command 2 exited 1",
    "cyclix.round": 1,
    "cyclix.trust_level": "act_alone",
    "cyclix.config.version": "sha256:…",
    "cyclix.duration_ms": 48211,
    "cyclix.cost.usd": 0.0,
    "vcs.repository.url.full": "https://github.com/ambitioushq/cyclix",
    "vcs.ref.head.name": "cyclix/12-add-state-core",
    "vcs.ref.head.revision": "9f1c…",
    "vcs.change.id": null,
    "gen_ai.request.model": null,
    "gen_ai.usage.input_tokens": null,
    "gen_ai.usage.output_tokens": null,
    "cyclix.gate.checks": [{"name": "tests", "passed": false, "duration_ms": 40112}]
  }
}
```

- `cyclix.station` is one of `admission`, `plan`, `build`, `gate`, `redteam`, `pr`, `reconciler`, one for each station in the table at the top.
- `cyclix.outcome` is one of `passed`, `parked`, `stopped`, `failed`, `crashed`, `skipped`.
- One trace per station run: `trace_id` is new for each run, and `span_id` names the station's span.
- A field with no value is written as `null`, so every line has the same keys for its kind.
- The engine version is `resource.service.version`. The config version is a hash of the config file.

The earlier loop starts writing station-run events in this same schema before the spine exists, so the record starts early. Any change to schema 0 is made here first.

## The config file

One TOML file per tenant, read with `tomllib` from the path in `CYCLIX_CONFIG`, else `$XDG_CONFIG_HOME/cyclix/<tenant>.toml`, else `~/.config/cyclix/<tenant>.toml`. This matches how the state directory is found.

```toml
[tenant]
name = "cyclix"

[tracker]
kind = "github"
owner = "ambitioushq"
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
repo = "ambitioushq/cyclix"
base = "main"

[agent]
command = ["claude", "-p", "--output-format", "json"]
model_plan = "claude-opus-5-5"
model_build = "claude-sonnet-5-5"
timeout_minutes = 60

[gate]
commands = [["uv", "run", "ruff", "check"], ["uv", "run", "pytest", "-q"]]

[limits]
runs_per_day = 6
```

`cyclix check` fails on a missing key, an unknown key, or a board option name that is not on the board.

## The sweep

`cyclix run --once` makes one pass for one tenant, under a file lock so two passes never overlap:

1. Read the board's items and their states.
2. Correct SQLite to match the board. A claim on an item a human moved out of In progress is released. An open run with no live process is ended with outcome `crashed`, its event is written, and its item is parked with the reason.
3. Run the reconciler on every item In review.
4. If no item is In progress and the day's run limit is not reached, admit the oldest Ready item and run plan, build, gate, red-team and PR in order. Stop at the first station that does not pass.

One item at a time per tenant in the spine.

## The test footing

The scenarios run against a fake GitHub world. The engine is run as a subprocess, the way systemd runs it.

The fake GitHub is a world model, not replayed recordings (settled in #4). The world model makes scenarios cheap to write and lets a scenario inject a fault into any one call. Recordings would carry real quirks, but every new scenario would need a new recording. The shape check below covers the quirks that matter: the JSON keys.

- **The fake world** (`tests/fakes/world.py`) is a JSON file holding issues, a board with items and states, PRs and their states. A scenario's Given steps write it; its Then steps read it.
- **The fake `gh`** is an executable placed first on `PATH`. It supports the `gh` commands listed under "The adapters", reads and changes the world, prints output in the same JSON shape as real `gh`, and appends each call to a calls file. A scenario can inject a fault for one call (an exit code, a stderr message, a stale read).
- **The fake agent** is an executable named in the test config's `agent.command`. A scenario gives it a script: files to write, commits to make, the text to answer, the exit code, the token and cost numbers to report.
- **The git remote** is a local bare repository, so pushes are real.
- **Keeping the fake honest.** The sandbox run (a real repo and board) records the real JSON shapes of each `gh` command used. A unit test checks that the fake's output has the same keys.

## The names check

CI fails if any tracked file or commit message in a PR contains a name from a private list. The list is held in the Actions secret `CYCLIX_FORBIDDEN_NAMES`, and locally in the environment variable of the same name. The check matches whole words, ignoring case. It reports the file, the line, and the list position of the name, never the name itself, because the CI log is public. With the secret missing, the check fails.

## Open questions for the first session

1. **The fake GitHub.** Settled in #4: the world model. See "The test footing".
2. **One item at a time.** Is one In progress item per tenant right for the spine? It keeps the sweep simple and is all a single maintainer needs at first.
3. **Run limits.** A daily run count stands in for the budget cap until the operations arm. Is six a day right for Cyclix's own tenant?
4. **Branch names.** `cyclix/<issue>-<slug>`, or the earlier loop's `<type>/<issue>-<slug>`?
5. **The models.** Which models the plan and build stations use by default.
