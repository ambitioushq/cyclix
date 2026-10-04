# Iteration 0

Iteration 0 is the smallest engine that takes a real issue to a merged PR. It has the state core, the GitHub adapters, the event log, the stage runner, and a minimal version of every stage. When it is done, Cyclix becomes a tenant of its own loop, and each later area replaces one minimal stage through that loop.

This document started as the design and now records what was built. Iteration 0 closed in #18, with every open question settled. Each later area replaces a minimal stage, and its own design doc records what changed.

## Done when

One real Cyclix issue, admitted from Cyclix's own board, reaches a merged PR through Iteration 0 running as a systemd timer on the host, and the event log holds one stage-run event for each stage it passed.

## What "minimal" means

A minimal stage does real work in the simplest way that carries a real issue. A stub that did nothing could not build Cyclix's own issues.

| Stage | Minimal behaviour | Replaced by |
| --- | --- | --- |
| Admission | Takes the oldest open issue in Ready on the configured board, from the configured repo. Ignores everything not on the board. | The admission area (the Ready contract, and promotion from Next) |
| Plan | One agent call that reads the issue. The stage saves the answer as `plan.md` in the run folder. If the agent's answer starts with `STOP:`, the item is parked with that sentence as the reason. | The plan area |
| Build | One agent call in the run's worktree, given the issue and the plan, that leaves its work committed on the run's branch. The stage saves the agent's answer as `pr.md` in the run folder. | The build area |
| Gate | Runs the tenant's gate commands in the worktree. Records each command's exit code against the head SHA. Any failure parks the item: no fix rounds in Iteration 0. | The gate area |
| Adversarial review | Records itself as `skipped`. | The adversarial review area |
| PR | Pushes the branch and opens a PR titled with the issue's title, with `pr.md` as its body. Moves the item to In review. | The PR area |
| Reconciler | For each item In review: merged moves it to Done; closed without merge moves it to Parked. | The reconciler area |

**The build agent writes the PR body** (settled for #50). The build prompt includes the tenant repository's `.github/pull_request_template.md`, read from the worktree, and asks the agent to end with that template filled in as its answer. A repository without the template gets `Closes #<issue>` and a short plain summary of what changed. The PR stage makes sure the body's first line is `Closes #<issue>`, and adds it when it is missing. The plan stays in the run folder and does not go into the PR. The PR title is the issue's title alone: `Closes #<issue>` already links the issue, and GitHub adds the PR number when it squashes. A separate agent call in the PR stage was considered and left out, because it costs one more call per run.

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
  runner.py          the sweep and the stage sequence
  stages/
    base.py          the Stage protocol and the run context
    admission.py plan.py build.py gate.py adversarial_review.py pr.py reconciler.py
    prompts/         plan.txt build.txt: the agent prompts, so a prompt changes without code
  install.py         writes the systemd user units
tests/
  features/          Gherkin feature files, the spec
  steps/             pytest-bdd step definitions
  fakes/bin/gh       the fake gh
  fakes/bin/fake-agent
  fakes/world.py     the fake GitHub world both fakes read and write
  fakes/bin/systemctl
  fakes/runner.py    runs cyclix as a subprocess against the fake world
  fixtures/gh-shapes/  the key paths of real gh output, recorded from the sandbox
  sandbox/           the steps of the @sandbox scenario
  unit/              unit tests, only where a scenario cannot reach a rule
scripts/
  names_check.py
  record_gh_shapes.py
```

## Work states and who moves them

| From | To | Written by | When |
| --- | --- | --- | --- |
| Ready | In progress | Runner (admission) | The item is claimed for a run |
| In progress | In review | PR stage | The PR is open |
| In progress | Parked | Any stage, or the sweep | A STOP, a failed gate, an error, or a crashed run found by the sweep |
| In progress | Needs decision | Plan stage | The plan needs a human call (not produced by the minimal plan) |
| In review | Done | Reconciler | The PR merged |
| In review | Parked | Reconciler | The PR closed without merging |
| Parked, Needs decision | Ready | A human only | |
| Any | Done | A human, or GitHub closing the issue | The reconciler observes it and releases any claim |

The engine never makes a move that is not in this table. A human can make any move. The sweep reads the board each pass and adjusts SQLite to match it.

`src/cyclix/workstate.py` holds the same table as data, and `move` refuses any move that is not in it. A unit test reads the table above and fails if the two differ, so a change to one needs the same change to the other. Rows written only by a human are left out of the code, because the engine never makes them.

"Any stage" means any writer that is a stage: admission, plan, PR, the reconciler, or a stage with no writer of its own (build, gate, adversarial review), which moves as "any stage". The sweep is not a stage. It may park an item in progress whose run crashed, and it makes no other move.

**Next comes with the admission area.** Next is a staging state between Backlog and Ready. A human moves an issue there to say the work should be done soon. The full admission stage then promotes it to Ready once it is safe to start: it is not a parent issue, it has no open blockers, it touches no files that work in flight touches, the review queue is under its cap, and it meets the Ready contract. An issue that fails the Ready contract goes to Needs decision. So a human decides what gets done, and the engine decides when it starts. Iteration 0 leaves this out: a human moves items straight to Ready, and its config does not map the board's Next option, so the engine ignores it.

## The state core

The stages and the runner reach SQLite only through the `StateCore` protocol in `state/core.py`.

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
    def runs_today(self, tenant: str) -> int: ...
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
    stage: str
    round: int = 1


@dataclass(frozen=True)
class RunState:
    run_id: str
    tenant: str
    issue: int
    stage: str
    phase: str | None
    round: int
    started_at: datetime
    fields: dict[str, object]
```

The three are kept apart because each is filled by a different side at a different time. `Claim` is a row of `claims`. `RunStart` is what the caller knows when a stage starts; the core stamps `started_at`. `RunState` is what the sweep reads back from an open stage. Timestamps are in UTC.

**A run is one pass of an issue through the stages.** It keeps one `run_id`, which is also on the claim and names the run folder. Each stage in the pass gets its own row in `runs`, unique on `(run_id, stage, round)`, so the gate can run again in a later round of the same pass. A run has at most one open row at a time. `set_phase`, `add_fields`, `record_check` and `end_run` act on that open row, and each call on a run with no open row is refused.

**The fields build up into the event.** `begin_run` seeds the fields with `cyclix.tenant`, `cyclix.issue.id`, `cyclix.run.id`, `cyclix.stage` and `cyclix.round`. `add_fields` merges more in, and adding `cyclix.round` also moves the `round` column, so the two can't disagree. `end_run` adds `cyclix.outcome` and `cyclix.outcome.reason`, and returns the whole dict for the event writer.

**`runs_today`** counts the tenant's runs that began on the current UTC date. A run counts once, however many stages it ran, and a run that crashed still counts. The sweep compares it with `limits.runs_per_day` (settled in #13).

**The best verified commit** is the last commit whose checks all passed, counting only checks in a stage row that ended with an outcome other than `crashed`. A row that is still open, or that crashed, may have stopped partway through its checks.

Tables in schema version 1:

- `meta(key, value)`: holds `schema_version`.
- `claims(tenant, issue, run_id, claimed_at)`, unique on `(tenant, issue)`.
- `runs(id, run_id, tenant, issue, stage, phase, round, started_at, ended_at, outcome, fields_json)`, unique on `(run_id, stage, round)`, and on `run_id` among rows with no `ended_at`. `fields_json` is the stage-run event while it builds up.
- `checks(id, run_row, sha, check, passed, at)`. `run_row` is the `runs.id` of the stage row that ran the check.
- `spend(tenant, day, usd, tokens)`, unique on `(tenant, day)`. `day` is the UTC date.

The file opens in WAL mode with a busy timeout of five seconds, and every write runs in one `BEGIN IMMEDIATE` transaction. A schema version newer than the code refuses to run. An older one is migrated by numbered SQL steps in code: step `i` takes the file from version `i` to `i + 1`, each in its own transaction.

**Durable phases.** Before an action that changes the outside world (a push, a PR open, a board move), the stage calls `set_phase` with the action's name. After a crash, the sweep reads the phase and checks the outside world before acting again: it checks for an existing PR before opening one, and for the remote branch before pushing.

## The adapters

All GitHub calls go through `adapters/gh.py`, which runs `gh` with `--json` output where the command supports it, parses the JSON, and raises `GhError` with the exit code and stderr on failure. Nothing else in the engine calls `gh`. One call may take 60 seconds. A call that runs longer is a `GhError` with exit code 124 (settled in #9). There are no retries: the next timer tick runs the pass again.

**Tracker** (`Tracker` protocol): `ready_items()`, `items()`, `item_state(issue)`, `set_state(issue, state)`, `issue(issue)`, `comment(issue, body)`. The GitHub implementation uses:

- `gh api graphql` with the `BoardFields` query for the project ID, the Status field ID and its option IDs, read once per pass
- `gh api graphql` with the `BoardItems` query for each item's ID, issue number, title, state, repository and Status value, read once per pass
- `gh api graphql` with the `BoardItem` query for one item's Status value, read fresh
- `gh project item-edit --id <item> --project-id <p> --field-id <f> --single-select-option-id <opt>` to move an item
- `gh issue view <n> -R <repo> --json number,title,body,state,author,labels` to read an issue
- `gh issue comment <n> -R <repo> --body <text>` to say why an item moved

The tracker keeps only items whose issue belongs to `[codehost] repo`. A draft, a PR or another repo's issue is ignored, and so is an item whose option is not mapped in `[tracker.states]`.

**The board is read with narrow GraphQL queries** (settled in #47). `gh project item-list` and `gh project field-list` fetch every field of every item. Each costs about 100 points of the 5,000 an hour that the maintainer's account shares across everything that uses it, even on a board of 25 items. A sweep made several of these calls, and the timer ran the sweep every 10 minutes, which used the whole limit in about 20 minutes. A query that asks only for the fields the tracker uses costs 1 point for a page of 100 items.

All three queries start from `repositoryOwner(login: $owner) { ... on ProjectV2Owner { projectV2(number: $number) { ... } } }`, which works for a user or an organization. Each has an operation name, so the fake `gh` can tell them apart. `BoardItems` reads `items(first: 100, after: $after)` and pages while `pageInfo.hasNextPage` is true, passing `endCursor` as `after` for the next page. `BoardFields` reads the project `id` and `field(name: <status_field>)`, as a single-select field with its `options`. It replaces `gh project view` and `gh project field-list`. A Status field that is missing, or is not single-select, is a `TrackerError`.

One tracker object serves one pass. It reads the board's fields and items once, on first use, and `items()`, `ready_items()`, `item_state()` and `set_state()` use that read. `set_state()` writes the new option into the tracker's copy after the move succeeds, so a later `items()` on the same tracker agrees with the board. An item added to the board during a pass is seen on the next pass.

`item_state()` is the one call that must see a change made by someone else during the pass, such as a human who moved an item while a stage ran. It finds the item's ID in the pass's read and reads that one item fresh with `BoardItem`. An issue that was not in the pass's read, or an item removed from the board since, has no state.

Moving an item stays on `gh project item-edit`, which reads nothing. The field and option IDs are not kept across passes, so a board renamed during a pass is seen on the next one.

**Ready items are taken oldest first, by issue number** (settled in #9). The board query does not return an issue's creation time, and GitHub numbers a repo's issues in the order they are created. The one exception is an issue moved in from another repo, which gets a new, higher number when it is transferred. That issue waits behind the ones numbered before it, which is acceptable.

**Code host** (`CodeHost` protocol): `ensure_clone()`, `new_worktree(issue, slug, run_dir) -> Worktree`, `remove_worktree(worktree)`, `head_sha(worktree)`, `push(worktree)`, `find_pr(branch) -> PR | None`, `open_pr(branch, title, body) -> PR`, `pr_state(number) -> PRState`. Every failure raises `CodeHostError`. The GitHub implementation runs `git` for the clone's fetches, the worktrees and the push, and uses:

- `gh repo clone <repo> <dir>` for the one clone, so `gh` picks the protocol and the credentials (settled in #10)
- `gh pr create -R <repo> --head <branch> --base <base> --title <t> --body-file <f>`
- `gh pr list -R <repo> --head <branch> --state all --json number,state,url`
- `gh pr view <n> -R <repo> --json state,mergedAt,closedAt,headRefOid,url`

`push` sets the upstream and never forces, so a push that would drop a commit on the remote branch fails. `find_pr` returns the newest PR on the branch in any state. `open_pr` first looks for an open PR on the branch and returns it, so a run that crashed after opening its PR never opens a second one. A closed or merged PR on the branch is not reused: a new one is opened (settled in #10). `pr_state` returns `open`, `merged` or `closed`, with the head SHA and the merge and close times.

**Agent** (`Agent` protocol): `run(prompt, cwd, model) -> AgentResult`, where the result holds the text answer, exit code, model, input and output tokens, cost, duration and turns. The Claude Code implementation runs the configured command (by default `claude -p --output-format json`) with the prompt on stdin and the worktree as its working directory, and parses the JSON result. That JSON has no top-level `model` key: the model's name is the one key of `modelUsage`. When `modelUsage` names more than one model, because Claude Code used a helper model for small tasks, the result records the model Cyclix asked for with `--model` (settled in #11). The prompt and the full answer are saved in the run folder. Only numbers reach the event.

## The state directory

Cyclix keeps everything it builds up while running in one state directory: the SQLite file, the event log, the run folders and the repo clones. It finds the directory in this order:

1. `CYCLIX_STATE_DIR`, if set.
2. Otherwise `$XDG_STATE_HOME/cyclix`, if `XDG_STATE_HOME` is set.
3. Otherwise `~/.local/state/cyclix`.

This follows the XDG convention, where a program keeps its settings under `~/.config` and the data it builds up under `~/.local/state`. The config file holds settings for one tenant, so the state directory is not in it. Tests set `CYCLIX_STATE_DIR` to a temporary directory for each scenario.

## Run folders and worktrees

Each run gets `runs/<tenant>/<issue>/<run_id>/` under the state directory, holding the prompts, answers, `plan.md` and gate output. The tenant's repo is cloned once into `repos/<tenant>/`. Each run adds a git worktree at `worktree/` inside its run folder. The worktree is removed when the run's claim is released. The runner passes the run folder to `new_worktree`, because the code host does not know the run ID.

The worktree is on the branch `cyclix/<issue>-<slug>`, made from the remote base right after a fetch, so it starts from the base as it is now.

**A later run on the same issue reuses its branch** (settled in #14). When a human moves an item back to Ready after an earlier run, that run's local branch is still in the clone, because removing a worktree keeps its branch. `new_worktree` checks out the existing branch when there is one, and makes it from `origin/<base>` only when there is none. The new run goes on from the earlier run's commits. Its PR stage finds the PR already open on the branch through `open_pr`, so a run that crashed after opening its PR never leads to a second PR, and nothing is force-pushed. The slug is the issue title lower-cased, with each run of characters other than `a-z` and `0-9` turned into one hyphen, hyphens trimmed from both ends, and cut to 40 characters. A hyphen left at the end by the cut is dropped. "Add the state core" on #12 gives `cyclix/12-add-the-state-core`. Branch names were settled in #10: the `cyclix/` prefix marks every branch Cyclix made, and the earlier loop's `<type>/` prefix would need a type the issue does not carry.

## The event log, schema version 0

One JSON object per line in `events/<tenant>.jsonl` under the state directory. Each line is an OpenTelemetry log record:

```json
{
  "schema": "cyclix.event/0",
  "timestamp": "2026-10-02T14:03:11.204Z",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "body": "stage_run",
  "resource": {"service.name": "cyclix", "service.version": "0.0.1"},
  "attributes": {
    "cyclix.tenant": "cyclix",
    "cyclix.issue.id": 12,
    "cyclix.run.id": "r-20261002-140211-12",
    "cyclix.stage": "gate",
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

- `cyclix.stage` is one of `admission`, `plan`, `build`, `gate`, `adversarial_review`, `pr`, `reconciler`, one for each stage in the table at the top.
- `cyclix.outcome` is one of `passed`, `parked`, `stopped`, `failed`, `crashed`, `skipped`.
- One trace per stage run: `trace_id` is new for each run, and `span_id` names the stage's span.
- A field with no value is written as `null`, so every line has the same keys for its kind. `cyclix.gate.checks` is on every stage-run line, and is `null` for stages other than the gate (settled in #12).
- The writer refuses a key that is not in the list above, and writes nothing (settled in #12). A new key is added here first, then to `events/schema.py`.
- The writer refuses any string attribute over 500 characters, including strings inside `cyclix.gate.checks`. A string that long is most likely prompt or code text, which belongs in the run folder.
- The engine version is `resource.service.version`. The config version is a hash of the config file.
- `cyclix.cost.usd` is rounded to 6 decimal places, a millionth of a dollar, before it is written (settled for #40). The agent reports costs such as `0.36616580000000004`, and the digits past the sixth are float noise. Cents would be too coarse for the cost of one call.

The earlier loop starts writing stage-run events in this same schema before Iteration 0 exists, so the record starts early. Any change to schema 0 is made here first.

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
# Print mode cannot ask before it edits a file or runs git, so the agent acts
# without asking. The gate and the maintainer's review are the checks.
command = ["claude", "-p", "--output-format", "json", "--permission-mode", "bypassPermissions"]
model_plan = "claude-opus-5-5"
model_build = "claude-sonnet-5-5"
timeout_minutes = 60

[gate]
commands = [["uv", "run", "ruff", "check"], ["uv", "run", "ruff", "format", "--check"], ["uv", "run", "pytest", "-q"]]

[limits]
runs_per_day = 6

[limits.wip]               # Cyclix state -> the most items it may hold
in_review = 5
```

`cyclix check` fails on a missing key, an unknown key, or a board option name that is not on the board.

**WIP limits** (settled in #44). The `[limits.wip]` table is the one optional part of the file. It maps a Cyclix state to the most items that column may hold. A state left out has no limit, and a file without the table has no limits. Only `in_progress`, `in_review`, `parked` and `needs_decision` take a limit: nothing in the engine adds items to Ready yet, and Done is the end. Each limit is a whole number of 1 or more. `in_progress` can only be 1, until the engine runs items side by side.

## The command

`cyclix` has `--version` and four subcommands in Iteration 0: `check`, `run --once`, `install` and `uninstall`. It exits 0 on success, 1 when a check or a run fails, 2 on bad usage, and 3 for a subcommand that is not built yet. Errors go to stderr.

`cyclix check [--tenant NAME]` prints one line per check to stdout. A check that passes prints `<what was checked>: ok`. A check that fails prints `FAIL: <reason>`, so a failure starts with the same word wherever it is. It checks, in order:

1. The config loads.
2. `gh` is on `PATH` and `gh auth status` succeeds.
3. The state directory exists or can be made, and a file can be written in it.
4. The first word of `agent.command` is on `PATH`.
5. The board's Status field has an option for every name in `[tracker.states]`, one line per state.

A check that needs an earlier one is left out when that one fails: no config means no agent or board check, and no signed-in `gh` means no board check. `check` reads the board with `gh project field-list` through `adapters/gh.py`, before the tracker adapter exists.

**What `install` puts in the service** (settled for #41). systemd's user manager does not read the shell's `PATH`, so `cyclix install` writes one into the service unit. It finds each command the service runs on the `PATH` of the shell it runs in: `gh`, `git`, the first word of `agent.command`, and the first word of each command in `gate.commands`. The unit's `PATH` holds the directories of those commands, in that order and without repeats, then `/usr/local/bin:/usr/bin:/bin`. It does not copy the shell's whole `PATH`. If one of the commands is not on `PATH`, `install` writes nothing, exits 1, and names the command. A timer whose every pass fails is worse than no timer. A tool moved later means running `install --force` again.

**Lingering.** A user's timers stop when the user logs out, unless lingering is on. When it is off, `install` prints to stderr that the timer stops at logout, and gives the command `loginctl enable-linger <user>`. It does not run that command, because it needs root. The units are still written and the timer started, and `install` exits 0: the timer runs while the user is logged in.

## The sweep

`cyclix run --once` makes one pass for one tenant, under a file lock so two passes never overlap:

1. Read the board's items and their states.
2. Correct SQLite to match the board. An open run with no live process is ended with outcome `crashed`, its event is written, and its item is parked with the reason "run crashed in phase <phase>". Then a claim on an item that is in neither In progress nor In review is released.
3. Run the reconciler on every item In review.
4. If no item is In progress, no column is at its WIP limit, and the day's run limit is not reached, admit the oldest Ready item and run plan, build, gate, adversarial review and PR in order. Stop at the first stage that does not pass.

**A full column stops admission** (settled in #44). This follows flow practice (Reinertsen's flow principles, Kanban): when a column is full, stop starting and finish what is there. A column is full when it holds as many items as its WIP limit, or more. The count takes every item in the column, including items a human moved there. While any column is full, the sweep admits nothing, writes no event, and prints `admission waits: <option> holds <n> of its WIP limit of <limit>`. The reconciler runs before admission, so a PR merged since the last pass frees a place in the same pass.

**The reconciler writes an event only when it acts** (settled in #14). The sweep runs on every timer tick, so an open PR is seen many times. An item whose PR is still open, or has no PR on its branch, stays In review and writes nothing. When the PR has merged or closed, the reconciler moves the item and writes one `reconciler` event. The event goes under the run ID of the item's claim. An item with no claim, such as one a human moved to In review, gets a new run ID, and that run counts toward `limits.runs_per_day`. The claim is released after the reconciler's row, whether it passed or failed, so a failed reconciler tries again on the next pass under a new run.

**A park from In review says why in a comment too** (settled in #14). A PR closed without merging parks its item with the comment "Parked: PR closed without merge". A move to Done posts nothing, because the merged PR already says so.

**One item at a time per tenant** (settled in #18). A Ready item is admitted only when no item is In progress. Items In review block admission only through a WIP limit on In review, so up to that limit, PRs can wait for the maintainer while the next item builds. `src/cyclix/runner.py` holds the sweep and the order of the stages.

**The lock decides which runs crashed** (settled in #13). The lock is a `flock` on `<state_dir>/<tenant>.lock`. A pass that finds it held prints "another pass is running" and exits 0. Only the pass holding the lock runs stages for the tenant. So any run still open when a pass takes the lock was left by a pass that died, and the sweep ends it as `crashed`. The state core keeps no process ID. A pass that is alive but hung keeps the lock, and later passes wait behind it.

**A claim lasts while the engine holds the item** (settled in #13). The engine holds an item while it is In progress or In review. A claim on an item in any other state is released, with the run's worktree. This covers a human's move, and the engine's own move to Parked or Needs decision. The reconciler releases the claim when it moves an item from In review.

**Each move out of In progress says why in a comment on the issue** (settled in #13). The comment reads `<state>: <reason>`, such as "Parked: gate command 2 exited 1". A human sees the reason where they act on the item. The same reason is in the stage-run event.

**A stage run.** The runner begins the stage's row, calls the stage, and adds the config version, the duration and the branch to the stage's fields. A stage that raises an error ends as `failed`, with the error as the reason. Each stage returns a `StageResult`: an outcome, a reason, fields for its event, and the state to move to if it stops the run. The default is Parked. When a stage stops the run, the runner first moves the item if it is still In progress, then ends the row and writes the event. A failed move leaves the row open, so the next pass finds it as crashed. A reason longer than 500 characters is cut to fit the event.

**Admission writes its own event.** The runner claims the item, begins an `admission` row, moves the item to In progress, reads the issue and makes the worktree. Each step after the claim sets a phase first: `move`, then `worktree`.

`cyclix run --once` exits 0 when the pass completes, whatever the run's outcome. It exits 1 when the pass stops on an error outside a stage, such as a failed board read.

## The test footing

The scenarios run against a fake GitHub world. The engine is run as a subprocess, the way systemd runs it.

The fake GitHub is a world model, not replayed recordings (settled in #4). The world model makes scenarios cheap to write and lets a scenario inject a fault into any one call. Recordings would carry real quirks, but every new scenario would need a new recording. The shape check below covers the quirks that matter: the JSON keys.

- **The fake world** (`tests/fakes/world.py`) is a JSON file holding issues, a board with items and states, PRs and their states. A scenario's Given steps write it; its Then steps read it.
- **The fake `gh`** is an executable placed first on `PATH`. It supports the `gh` commands listed under "The adapters", reads and changes the world, prints output in the same JSON shape as real `gh`, and appends each call to a calls file. A scenario can inject a fault for one call (an exit code, a stderr message, a stale read).
- **The fake agent** is an executable named in the test config's `agent.command`. A scenario gives it a script: files to write, commits to make, the text to answer, the exit code, the token and cost numbers to report.
- **The git remote** is a local bare repository, so pushes are real.
- **Keeping the fake honest.** The sandbox run (a real repo and board) records the real JSON shapes of each `gh` command used. A scenario checks that the fake's output has the same keys.

**The sandbox** (settled in #15) is the private repo `ambitioushq/cyclix-sandbox` and the private board `ambitioushq` project 2, whose Status field holds the six option names. Its tenant config is `docs/examples/sandbox.toml`. Scenarios tagged `@sandbox` run against it with the real `gh` and the real agent, and only when `CYCLIX_SANDBOX=1`. The workflow `sandbox.yml` runs them by hand and weekly, never on a PR.

- **The sandbox scenario merges the PR itself.** Where the spine waits for a person to merge, the scenario runs `gh pr merge --squash`, so the weekly run needs nobody.
- **The real agent runs with `--permission-mode bypassPermissions`.** Print mode cannot ask before it edits a file or runs `git`. The run is on a throwaway CI machine, against a throwaway repo.
- **The shapes.** `scripts/record_gh_shapes.py` runs each command the adapters read against the sandbox, and writes `tests/fixtures/gh-shapes/<command>.json`. For a JSON command the file holds the sorted key paths of the output, with a list's elements under `<list>[]`. `pr create` prints a URL that the code host parses, so its file holds that line with the repo and number masked. Nothing reads the output of `project item-edit` or `issue comment`, so neither is recorded. The three board queries are recorded as `graphql-board-fields`, `graphql-board-items` and `graphql-board-item`. Each file holds a placeholder for the query text, not the text, so a changed query is caught only when the shapes are recorded again. The workflow records the shapes again after the scenarios, and fails if they changed.
- **The sandbox is throwaway.** Each scenario first closes every open issue and PR in the sandbox and empties the board, in case an earlier run died. At the end it closes and deletes what it made.

## The names check

CI fails if any tracked file or commit message in a PR contains a name from a private list. The list is held in the Actions secret `CYCLIX_FORBIDDEN_NAMES`, and locally in the environment variable of the same name. The check matches whole words, ignoring case. It reports the file, the line, and the list position of the name, never the name itself, because the CI log is public. With the secret missing, the check fails.

## Cyclix as its own tenant

Settled in #17. Cyclix runs its own loop from the tenant config above, which is also `docs/examples/tenant.toml`. The maintainer keeps the live copy outside this repository, on the host.

- **The host.** The timer runs on a Linux host the maintainer runs, under `cyclix install --tenant cyclix`. The maintainer runs the host steps.
- **The agent acts without asking.** Print mode cannot ask before it edits a file or runs `git`, so the agent runs with `--permission-mode bypassPermissions`, as in the sandbox. The gate and the maintainer's review are the checks on what it does.
- **The models.** The plan stage uses `claude-opus-5-5` and the build stage uses `claude-sonnet-5-5`.
- **The run limit.** Six runs a day.
- **The gate matches CI**, apart from the names check, which needs the private list.
- **Branch protection on `main`.** Changes reach `main` only through a PR. The CI jobs `test` and `names` must pass. Force pushes and deleting `main` are refused. No approving review is required, because the loop opens its PRs under the maintainer's own GitHub identity, and GitHub does not let an author approve their own PR. Admins may bypass the rules, so the maintainer can still push a fix to `main` in an emergency.
- **The live scenario.** `tests/features/self_tenant.feature` is tagged `@live`. It was checked by hand once, and the PR for #17 records the result. No steps file binds it.

## Open questions for the first session

1. **The fake GitHub.** Settled in #4: the world model. See "The test footing".
2. **One item at a time.** Settled in #18: one item In progress per tenant. See "The sweep".
3. **Run limits.** Settled in #17: six a day. See "Cyclix as its own tenant".
4. **Branch names.** Settled in #10: `cyclix/<issue>-<slug>`. See "Run folders and worktrees".
5. **The models.** Settled in #17: Opus plans, Sonnet builds. See "Cyclix as its own tenant".
