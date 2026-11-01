# How Cyclix works

Cyclix takes an issue that a person has marked Ready and carries it to a pull request (PR). It plans the change, builds it, runs your checks on it, and opens the PR. It then waits for a person to review and merge it.

A **tenant** is one repository together with its project board and one config file. One Cyclix install can run several tenants, and each has its own timer, state and event log.

## What happens in one pass

A **pass** is one run of `cyclix run` for one tenant. A systemd timer starts a pass every 10 minutes by default. Each pass does four things, in order:

1. It reads the board.
2. It corrects its own state file to match the board. A run that died in an earlier pass is ended and its item is parked. A claim on an item that a person moved is released.
3. It checks every item In review. If the item's PR has merged or closed, it moves the item.
4. It admits the oldest Ready item, if nothing blocks it, and runs it through the stages.

Admission waits when any of these holds:

- An item is already In progress.
- A column has reached its limit on work in progress (the WIP limit, set under `[limits.wip]` in the config). The count includes items that a person moved into the column.
- The tenant has used its `runs_per_day`. A run counts once, whatever number of stages it ran, and a run that crashed still counts. The day is a UTC date.

When admission waits for a full column, the pass logs `admission waits: <option> holds <n> of its WIP limit of <limit>`. A PR that merged since the last pass frees a place in the same pass, because step 3 runs before step 4.

A **run** is one trip of one issue through the stages. It has a run ID, such as `r-20261031-101500-12`, and a folder of its own (see [Where Cyclix keeps its data](#where-cyclix-keeps-its-data)).

## The stages an issue goes through

Each stage ends with an outcome: `passed`, `parked`, `stopped`, `failed` or `crashed`. The run goes on only when a stage passes.

| Stage | What it does |
| --- | --- |
| Admission | Takes the oldest Ready item, in order of issue number. Moves it to In progress, reads the issue, and makes a git worktree for the run: a separate working copy of the repository, on its own branch. If the config names an instruction folder, copies its files in. |
| Plan | Runs the coding agent once, with read-only tools. It reads the issue and the repository and answers with a plan. Cyclix saves the plan as `plan.md`. If the answer starts with `STOP:`, the item is parked and the rest of that line is the reason. |
| Build | Runs the agent once more in the worktree, with the issue and the plan. The agent changes the files and commits its work. Its final answer is the PR body, saved as `pr.md`. If the agent makes no commit, the stage fails. |
| Gate | Runs your gate commands in the worktree, in order, and stops at the first that fails. A failure parks the item. |
| PR | Pushes the branch and opens a PR titled with the issue's title. Moves the item to In review. |
| Reconciler | Acts later, on each item In review. A merged PR moves the item to Done. A PR closed without a merge moves it to Parked. |

The branch is named `cyclix/<issue>-<slug>`. The slug is the issue title in lower case, with each run of other characters turned into one hyphen, cut to 40 characters. "Add the state core" on issue 12 gives `cyclix/12-add-the-state-core`.

If an earlier run on the same issue left its branch, the new run goes on from that branch's commits. Cyclix never force-pushes. When a PR is already open on the branch, the PR stage finds it and does not open a second one. A closed or merged PR is not reused.

### What the agent can do

The plan and build stages run Claude Code with a list of tools for each stage, set in the config. A call outside the list is refused. The agent gets no GitHub login. Cyclix does every push and every PR call itself. [ADR-0009](../adr/0009-run-the-agent-without-approval-prompts-and-with-a-tool-list-per-stage.md) and [ADR-0010](../adr/0010-keep-code-host-credentials-out-of-the-agent-and-the-gate.md) give the reasons, and [Isolation](../design/isolation.md) says what the setup does not stop.

## The six work states

An item on your board is always in one of six work states. These are Cyclix's own names. The config maps each one to an option of the board's Status field, so your board can use other words. See [Configuration](../reference/configuration.md).

| State | What it means |
| --- | --- |
| Ready | A person has said the item may be worked on. Admission takes the oldest. |
| In progress | Cyclix is working on the item. At most one item is In progress for a tenant. |
| In review | The PR is open and waits for a person. |
| Parked | The run stopped and a person has to look. The comment on the issue says why. |
| Needs decision | The item waits for a human call. |
| Done | The PR merged, or the issue was closed. |

Coming soon: a Next state. A person would move work there to say it should be done soon, and admission would promote it to Ready once it is safe to start. Until then, a person moves items straight to Ready, and the engine ignores a Next option on the board.

The engine makes only the moves in the table below. A person can make any move.

## The work states and who moves them

| From | To | Written by | When |
| --- | --- | --- | --- |
| Ready | In progress | Runner (admission) | The item is claimed for a run |
| In progress | In review | PR stage | The PR is open |
| In progress | Parked | Any stage, or the sweep | A STOP, a failed gate, an error, or a crashed run found by the sweep |
| In progress | Needs decision | Plan stage | The plan needs a human call |
| In review | Done | Reconciler | The PR merged |
| In review | Parked | Reconciler | The PR closed without merging |
| Parked, Needs decision | Ready | A human only | |
| Any | Done | A human, or GitHub closing the issue | The reconciler observes it and releases any claim |

"Any stage" means admission, plan, build, gate, PR or the reconciler. The **sweep** is the first half of a pass, where Cyclix corrects its state file. It is not a stage. It may park an item that is In progress when that item's run crashed, and it makes no other move.

The plan stage may move an item to Needs decision, but it does not do so today. Every STOP parks the item.

Each time Cyclix moves an item out of In progress, it posts a comment on the issue: `<state>: <reason>`, such as "Parked: gate command 2 exited 1". A PR closed without a merge parks its item with the comment "Parked: PR closed without merge". A move to Done posts nothing, because the merged PR already says so.

To retry a parked item, move it back to Ready. Cyclix moves nothing out of Parked or Needs decision.

## Where Cyclix keeps its data

Each kind of data has one owner. Cyclix reads a kind of data from its owner, and does not keep a second copy that it trusts.

| Data | Where it is | What it holds | When Cyclix reads it |
| --- | --- | --- | --- |
| Work item states, issues and comments | The project board and the issue tracker | Each item's state, set by Cyclix or by a person | At the start of every pass. Once more for one item whenever a stage must see a change made during the pass. |
| Code, branches and PRs | The code host (GitHub) | The repository, each branch, each PR and its state | When a stage needs a PR's state, and when it pushes. Cyclix keeps no copy of a PR's state. |
| Working state | `state.db`, a SQLite file in the state directory | Claims, the phase each run has reached, the checks run on each commit, and the spend so far | Every pass, to find claims and runs that are still open. |
| Run files | `runs/<tenant>/<issue>/<run ID>/` in the state directory | Prompts, answers, `plan.md`, `pr.md` and gate output | The build stage reads `plan.md`, and the PR stage reads `pr.md`. Otherwise they are for people. |
| Event log | `events/<tenant>.jsonl` in the state directory | One JSON line for each stage run | Never. It is a record for people to query. |

The state directory is `CYCLIX_STATE_DIR` when set, else `$XDG_STATE_HOME/cyclix`, else `~/.local/state/cyclix`.

When the state file and the board disagree about an item, the board is right, and the sweep corrects the state file. People act on the board, so a second copy of their decisions in the state file would drift. The state file holds only facts that the board has no field for and that no person edits. [ADR-0002](../adr/0002-each-kind-of-data-has-one-owner.md) has the reasoning.

The event log is a record of what happened. Cyclix writes to it and never reads it to decide anything ([ADR-0003](../adr/0003-the-loop-writes-the-event-log-but-never-reads-it.md)). Each line is one stage run, with the issue, the stage, the outcome and its reason, the model, tokens and cost, the duration, and each gate check's result. It holds IDs and numbers, never prompts, code or issue text. Any tool that reads JSON lines can query it. [Engine](../design/engine.md) lists every field.

## What a person does

1. Writes an issue that says what to change.
2. Moves it to Ready on the board.
3. Reads the comment on the issue when an item is Parked.
4. Reviews the PR, and merges it or closes it.

Cyclix asks for nothing else. [ADR-0001](../adr/0001-merge-only-after-approval-or-under-a-written-rule.md) covers when Cyclix may merge.
