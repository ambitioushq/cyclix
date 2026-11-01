# Engine

This page describes the parts of the engine: the state core, the adapters, the run folders, the event log schema and the sweep. [Architecture](architecture.md) covers the design as a whole. [How Cyclix works](../concepts/how-cyclix-works.md) covers the stages and the work states from the operator's side, and [Configuration](../reference/configuration.md) covers the config keys.

## How the code is laid out

```
src/cyclix/
  __init__.py
  __main__.py        python -m cyclix
  cli.py             argparse entry point
  config.py          load and validate the tenant TOML
  workstate.py       the work states and the transition table
  state/
    core.py          the StateCore protocol (the narrow interface)
    sqlite.py        the SQLite implementation
  adapters/
    gh.py            runs gh, parses JSON, raises one error type
    process.py       runs a command with a time limit and kills its whole process group
    environment.py   the environment the agent and the gate get
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
    admission.py plan.py build.py gate.py pr.py reconciler.py
    prompts/         plan.txt build.txt: the agent prompts, so a prompt changes without code
  install.py         writes the systemd user units
tests/               see Testing
scripts/
  record_gh_shapes.py
```

## The work states and the transition table

`src/cyclix/workstate.py` holds the table of moves from [How Cyclix works](../concepts/how-cyclix-works.md#the-work-states-and-who-moves-them) as data. The function `move` refuses any move that is not in it. A unit test reads the table in that page and fails if the two differ, so a change to one needs the same change to the other. Rows that only a person writes are left out of the code, because the engine never makes them.

Each writer may make only its own moves, so a stage cannot put an item in a state that another writer owns. A stage with no writer of its own (build and gate) moves as "any stage".

## The state core

The stages and the runner reach SQLite only through the `StateCore` protocol in `state/core.py`. A **protocol** is a Python class that lists the methods a caller may use. The SQLite implementation is one class behind it.

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
    def add_spend(self, tenant: str, usd: float, tokens: int) -> None: ...
```

Three small record types go with it: `Claim` (a row of `claims`), `RunStart` (what the caller knows when a stage starts) and `RunState` (an open stage row, as the sweep reads it back after a crash). They are kept apart because each is filled by a different side at a different time. The core stamps `started_at`. Timestamps are in UTC.

**A run is one trip of an issue through the stages.** It keeps one `run_id`, which is also on the claim and names the run folder. Each stage in the run gets its own row in `runs`, unique on `(run_id, stage)`. A run has at most one open row at a time. `set_phase`, `add_fields`, `record_check` and `end_run` act on that open row, and each call on a run with no open row is refused.

**The fields build up into the event.** `begin_run` seeds the fields with `cyclix.tenant`, `cyclix.issue.id`, `cyclix.run.id` and `cyclix.stage`. `add_fields` merges more in. `end_run` adds `cyclix.outcome` and `cyclix.outcome.reason`, and returns the whole dict for the event writer.

**`runs_today`** counts the tenant's runs that began on the current UTC date. A run counts once, however many stages it ran, and a run that crashed still counts. The sweep compares it with `limits.runs_per_day`.

The tables, in schema version 2:

- `meta(key, value)` holds `schema_version`.
- `claims(tenant, issue, run_id, claimed_at)`, unique on `(tenant, issue)`.
- `runs(id, run_id, tenant, issue, stage, phase, started_at, ended_at, outcome, fields_json)`, unique on `(run_id, stage)`, and on `run_id` among rows with no `ended_at`. `fields_json` is the stage-run event while it builds up.
- `checks(id, run_row, sha, check, passed, at)`. `run_row` is the `runs.id` of the stage row that ran the check.
- `spend(tenant, day, usd, tokens)`, unique on `(tenant, day)`. `day` is the UTC date.

The file opens in WAL mode (write-ahead logging, which lets readers work while a write happens) with a busy timeout of five seconds. Every write runs in one `BEGIN IMMEDIATE` transaction. A schema version newer than the code refuses to run. An older one is migrated by numbered SQL steps in code: step `i` takes the file from version `i` to `i + 1`, each in its own transaction.

**Durable phases.** Before an action that changes the outside world (a push, a PR open, a board move), the stage calls `set_phase` with the action's name. The phases are `agent`, `move`, `worktree`, `instructions`, `push` and `open_pr`. After a crash, the next run checks the outside world before it acts again: it looks for an existing PR before it opens one, and the push never forces.

## The adapters

An **adapter** is the module that talks to one outside system behind a narrow interface: `Tracker`, `CodeHost` or `Agent`. Nothing else talks to that system. The adapter parses what it gets back, raises one kind of error, and keeps its credentials to itself. Each adapter picks how it talks to its system, through a command-line program or an HTTP API. The current adapters run `gh` and `claude`, because each program handles login, protocol and output format.

### The `gh` module

All GitHub calls go through `adapters/gh.py`. It runs `gh` with `--json` output where the command supports it, parses the JSON, and raises `GhError` with the exit code and stderr on failure. Nothing else in the engine calls `gh`. A call that runs past its time limit is a `GhError` with exit code 124. There are no retries: the next timer run makes the pass again. [Configuration](../reference/configuration.md#time-limits-that-are-not-in-the-config) lists the limits.

### The tracker

The `Tracker` protocol has five methods: `items()`, `item_state(issue)`, `set_state(issue, state)`, `issue(issue)` and `comment(issue, body)`. The GitHub implementation uses:

- `gh api graphql` with the `BoardFields` query, for the project ID, the Status field ID and its option IDs. Read once per pass.
- `gh api graphql` with the `BoardItems` query, for each item's ID, issue number, title, state, repository and Status value. Read once per pass.
- `gh api graphql` with the `BoardItem` query, for one item's Status value. Read fresh.
- `gh project item-edit --id <item> --project-id <p> --field-id <f> --single-select-option-id <opt>`, to move an item.
- `gh issue view <n> -R <repo> --json number,title,body,state,author,labels`, to read an issue.
- `gh issue comment <n> -R <repo> --body <text>`, to say why an item moved.

The tracker keeps only items whose issue belongs to `[codehost] repo`. A draft, a PR or another repository's issue is ignored, and so is an item whose option is not mapped in `[tracker.states]`.

The board is read with queries that ask for only the fields the tracker uses. GitHub gives an account 5,000 API points an hour, shared by everything that uses it. `gh project item-list` and `gh project field-list` fetch every field of every item and cost about 100 points each, even for 25 items. A sweep that made several of these calls every 10 minutes used the whole limit in about 20 minutes. A page of 100 items from `BoardItems` costs 1 point. `cyclix check` still uses `gh project field-list`, because it runs once, on request. All three start from `repositoryOwner(login: $owner) { ... on ProjectV2Owner { projectV2(number: $number) { ... } } }`, which works for a user or an organization. `BoardItems` reads `items(first: 100, after: $after)` and pages while `pageInfo.hasNextPage` is true, passing `endCursor` as `after` for the next page. `BoardFields` reads the project `id` and `field(name: <status_field>)` as a single-select field with its `options`. A Status field that is missing, or is not single-select, is a `TrackerError`.

One tracker object serves one pass. It reads the board's fields and items once, on first use, and `items()`, `item_state()` and `set_state()` use that read. `set_state()` writes the new option into the tracker's copy after the move succeeds, so a later `items()` on the same tracker agrees with the board. An item added to the board during a pass is seen on the next pass.

`item_state()` is the one call that must see a change that someone else made during the pass, such as a person who moved an item while a stage ran. It finds the item's ID in the pass's read and reads that one item fresh with `BoardItem`. An issue that was not in the pass's read, or an item removed from the board since, has no state.

Moving an item uses `gh project item-edit`, which reads nothing. The field and option IDs are not kept across passes, so a board renamed during a pass is seen on the next one.

**Ready items are taken oldest first, by issue number.** The board query does not return an issue's creation time, and GitHub numbers a repository's issues in the order they are created. The one exception is an issue moved in from another repository, which gets a new, higher number when it is transferred. That issue waits behind the ones numbered before it, which is acceptable.

### The code host

The `CodeHost` protocol has these methods: `ensure_clone()`, `new_worktree(issue, slug, run_dir)`, `remove_worktree(worktree)`, `add_local_files(worktree, files)`, `head_sha(worktree)`, `push(worktree)`, `find_pr(branch)`, `open_pr(branch, title, body)` and `pr_state(number)`. Every failure raises `CodeHostError`. The GitHub implementation runs `git` for the clone's fetches, the worktrees and the push, and uses:

- `gh repo clone <repo> <dir>`, for the one clone, so `gh` picks the protocol and the credentials.
- `gh pr create -R <repo> --head <branch> --base <base> --title <t> --body-file <f>`
- `gh pr list -R <repo> --head <branch> --state all --json number,state,url`
- `gh pr view <n> -R <repo> --json state,mergedAt,closedAt,headRefOid,url`

`push` sets the upstream and never forces, so a push that would drop a commit on the remote branch fails. `find_pr` returns the newest PR on the branch in any state. `open_pr` first looks for an open PR on the branch and returns it, so a run that crashed after it opened its PR never opens a second one. A closed or merged PR on the branch is not reused: a new one is opened. `pr_state` returns `open`, `merged` or `closed`, with the head SHA and the merge and close times.

Every git call has a time limit, and sets `GIT_TERMINAL_PROMPT=0`, so git never waits for a password. A call past its limit has its whole process group killed. Killing only the command is not enough: a test's server, or git's credential helper, would keep the output pipe open, and reading the output would never end.

### The agent

The `Agent` protocol has one method, `run(prompt, cwd, stage, run_dir)`, where `stage` is the stage's model, caps and tools from the config. The result holds the text answer, whether the call failed and why, the exit code, the model, the input and output tokens, the cost, the duration and the number of turns.

The Claude Code implementation runs the configured command (by default `claude -p`) with the prompt on stdin and the worktree as its working directory. The engine adds the flags of [ADR-0005](../adr/0005-run-the-agent-without-approval-prompts-and-with-a-tool-list-per-stage.md) after the command, including `--output-format stream-json --verbose`. In that mode Claude Code prints each assistant message as it comes, with that message's token counts, and a result line at the end. The engine reads the result line.

**A call that runs past its timeout** gets SIGINT, which lets Claude Code stop its own tools and print a result line of subtype `error_during_execution` that holds the cost so far. After 30 seconds the whole process group is killed. Claude Code's plain `--output-format json` prints nothing when it is interrupted, so a timed-out call would lose its cost. This is why the engine uses stream-json.

**A call with no result line**, because it was killed or crashed, still has its assistant lines. The result takes their tokens and turns, and the cost is unknown (null). The day's spend leaves it out. A price table to estimate the cost was considered and left out, because it would need changing with every new model or price. The caps stop a call long before the timeout in normal use, so a null cost should be rare.

**The model.** The result has no top-level `model` key. The model's name is the one key of `modelUsage`. When `modelUsage` names more than one model, because Claude Code used a helper model for small tasks, the result records the model that Cyclix asked for with `--model`.

**A call stopped by a cap** ends with the subtype `error_max_turns` or `error_max_budget_usd`. The engine reports each as its own reason, "turn cap reached" or "budget cap reached".

The prompt and the full answer are saved in the run folder as `prompt-<n>.txt` and `answer-<n>.jsonl`. Only numbers reach the event.

## The state directory

Cyclix keeps everything it builds up while running in one state directory (how it is found: [How Cyclix works](../concepts/how-cyclix-works.md#where-cyclix-keeps-its-data)). It holds:

| Path | Contents |
| --- | --- |
| `state.db` | The SQLite file. |
| `events/<tenant>.jsonl` | The event log. |
| `runs/<tenant>/<issue>/<run ID>/` | The run folders. |
| `repos/<tenant>/` | The tenant's clone. |
| `<tenant>.lock` | The lock file that keeps two passes apart. |

This follows the XDG convention, where a program keeps its settings under `~/.config` and the data it builds up under `~/.local/state`. The config file holds settings for one tenant, so the state directory is not in it. Tests set `CYCLIX_STATE_DIR` to a temporary directory for each scenario.

## Run folders and worktrees

Each run gets `runs/<tenant>/<issue>/<run ID>/` under the state directory. It holds the prompts, the answers, `plan.md`, `pr.md`, the gate output (`gate-<n>.txt`) and an empty `gh-config/` folder that the agent and the gate use as their `gh` config. The tenant's repository is cloned once into `repos/<tenant>/`. Each run adds a git worktree at `worktree/` inside its run folder. A **worktree** is a second working copy of the same repository, on its own branch. The worktree is removed when the run's claim is released. The runner passes the run folder to `new_worktree`, because the code host does not know the run ID.

The worktree is on the branch `cyclix/<issue>-<slug>`, made from the remote base right after a fetch, so it starts from the base as it is now. The slug is the issue title in lower case, with each run of characters other than `a-z` and `0-9` turned into one hyphen, hyphens trimmed from both ends, and cut to 40 characters. A hyphen left at the end by the cut is dropped. The `cyclix/` prefix marks every branch that Cyclix made. A `<type>/` prefix would need a type that the issue does not carry.

**A later run on the same issue reuses its branch.** When a person moves an item back to Ready after an earlier run, that run's local branch is still in the clone, because removing a worktree keeps its branch. `new_worktree` checks out the existing branch when there is one, and makes it from `origin/<base>` only when there is none. The new run goes on from the earlier run's commits. Its PR stage finds the PR already open on the branch through `open_pr`, and nothing is force-pushed.

## The event log schema

The engine writes the event log and never reads it. It decides from the tracker, the code host and the state file, so anyone can query, copy, rotate or delete the log without changing what the loop does next.

Each event is one JSON object per line in `events/<tenant>.jsonl`, shaped as an OpenTelemetry log record ([ADR-0003](../adr/0003-one-wide-event-per-stage-run-in-opentelemetry-shape.md)). The schema version is 1. Any change to the schema is made here first, and then in `src/cyclix/events/schema.py`.

```json
{
  "schema": "cyclix.event/1",
  "timestamp": "2026-10-02T14:03:11.204Z",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "body": "stage_run",
  "resource": {"service.name": "cyclix", "service.version": "0.0.1"},
  "attributes": {
    "cyclix.tenant": "storefront",
    "cyclix.issue.id": 12,
    "cyclix.run.id": "r-20261002-140211-12",
    "cyclix.stage": "gate",
    "cyclix.outcome": "parked",
    "cyclix.outcome.reason": "gate command 2 exited 1",
    "cyclix.config.version": "sha256:…",
    "cyclix.agent.instructions.version": null,
    "cyclix.duration_ms": 48211,
    "cyclix.cost.usd": 0.0,
    "vcs.repository.url.full": "https://github.com/acme/storefront",
    "vcs.ref.head.name": "cyclix/12-add-state-core",
    "vcs.ref.head.revision": "9f1c…",
    "vcs.change.id": null,
    "gen_ai.request.model": null,
    "gen_ai.usage.input_tokens": null,
    "gen_ai.usage.output_tokens": null,
    "cyclix.agent.turns": null,
    "cyclix.gate.checks": [{"name": "tests", "passed": false, "duration_ms": 40112}]
  }
}
```

- `cyclix.stage` is one of `admission`, `plan`, `build`, `gate`, `pr`, `reconciler`, one for each stage in [How Cyclix works](../concepts/how-cyclix-works.md#the-stages-an-issue-goes-through).
- `cyclix.outcome` is one of `passed`, `parked`, `stopped`, `failed`, `crashed`.
- `trace_id` is new for each stage run, and `span_id` names the stage's span. An issue can take days to reach a merge, so every event also carries `cyclix.issue.id`, and grouping by it rebuilds an issue's life.
- A field with no value is written as `null`, so every line has the same keys. `cyclix.gate.checks` is on every line, and is `null` for stages other than the gate.
- The writer refuses a key that is not in the list above, and writes nothing.
- The writer refuses any string attribute over 500 characters, including strings inside `cyclix.gate.checks`. A string that long is most likely prompt or code text, which belongs in the run folder.
- The engine version is `resource.service.version`. The config version, `cyclix.config.version`, is a hash of the config file.
- `cyclix.agent.instructions.version` is a hash of the instruction folder that `[agent] instructions` names, or null when the config names none. It is `sha256:` and a hex digest over each file under the folder, in order of its path relative to the folder: the path in UTF-8, a NUL byte, the content's length in bytes as decimal digits, a NUL byte, then the content. It changes when any file's name or content changes, so each run records which rules its agent was given. It is on every line, including the stages that make no agent call.
- `cyclix.agent.turns` is the number of turns the agent took, as Claude Code reports it in `num_turns`, so the turn caps can be checked against real runs. OpenTelemetry's GenAI names have no field for it, so it sits under `cyclix.*`. It is null for stages that make no agent call.
- `cyclix.cost.usd` is null for a stage that makes no agent call, and for an agent call that printed no result line. It is rounded to 6 decimal places, a millionth of a dollar, before it is written. The agent reports costs such as `0.36616580000000004`, and the digits past the sixth are float noise. Cents would be too coarse for the cost of one call.

## The sweep

`cyclix run` makes one pass for one tenant, under a file lock so two passes never overlap. [How Cyclix works](../concepts/how-cyclix-works.md#what-happens-in-one-pass) lists the four steps. `src/cyclix/runner.py` holds the sweep and the order of the stages. This section gives the rules behind them.

**The lock decides which runs crashed.** The lock is an `flock` on `<state directory>/<tenant>.lock`. Only the pass that holds it runs stages for the tenant, so any run still open when a pass takes the lock was left by a pass that died. The sweep ends it as `crashed`, writes its event, and parks its item with the reason "run crashed in phase <phase>". A pass that is alive but hung keeps the lock, and later passes exit without doing anything until it ends.

**A claim lasts while the engine holds the item.** The engine holds an item while it is In progress or In review. A claim on an item in any other state is released, with the run's worktree. This covers a person's move and the engine's own move to Parked or Needs decision. The reconciler releases the claim when it moves an item out of In review.

**A full column stops admission.** A column is full when it holds as many items as its WIP limit, or more. The count takes every item in the column, including items a person moved there. While any column is full, the sweep admits nothing and writes no event.

**The reconciler writes an event only when it acts.** The sweep runs on every timer tick, so an open PR is seen many times. An item whose PR is still open, or has no PR on its branch, stays In review and writes nothing. When the PR has merged or closed, the reconciler moves the item and writes one `reconciler` event under the run ID of the item's claim. An item with no claim, such as one a person moved to In review, gets a new run ID, and that run counts toward `limits.runs_per_day`. The claim is released after the reconciler's row, whether it passed or failed, so a failed reconciler tries again on the next pass under a new run.

**A stage run.** The runner begins the stage's row, calls the stage, and adds the config version, the duration and the branch to the stage's fields. A stage that raises an error ends as `failed`, with the error as the reason. Each stage returns a `StageResult`: an outcome, a reason, fields for its event, and the state to move to if it stops the run. The default is Parked. When a stage stops the run, the runner first moves the item if it is still In progress, then ends the row and writes the event. A failed move leaves the row open, so the next pass finds it as crashed. A reason longer than 500 characters is cut to fit the event.

**Admission writes its own event.** The runner claims the item, begins an `admission` row, moves the item to In progress, reads the issue and makes the worktree. Each step after the claim sets a phase first: `move`, then `worktree`, then `instructions` when the config names an instruction folder.

**Admission and the reconciler are stages like the others.** Each is a class with a `name` and a `run(ctx)` method, and the runner runs every stage the same way. When the runner claims an item, it makes one `RunContext` for the run: the adapters, the run ID, the issue number and the run folder. Admission fills in the issue's details and the worktree, and plan, build, gate and PR read them, so the context is not frozen. The reconciler is made for one item and its ended PR, and its context has no worktree. Two frozen contexts were considered and left out: a small one for admission and the reconciler, with admission returning the full one in its result. That needs a second context type, and a result field that only admission sets.

**The PR body comes from the build stage.** The build prompt includes the repository's `.github/pull_request_template.md` and asks the agent to end its answer with the template filled in. With no template, the agent writes `Closes #<issue>` and a short summary. The build stage saves the answer as `pr.md`. The PR stage reads `pr.md`, makes sure its first line is `Closes #<issue>`, and opens the PR with the issue's title. The plan does not go into the PR. The agent writes the body because it knows why it made each change, and the engine sees only what changed. A separate agent call in the PR stage would cost one more call per run.
