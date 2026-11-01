# Architecture

Cyclix is an engine that runs an unattended issue-to-PR loop. It takes a well-formed issue, plans the change, builds it, runs the quality gate, and opens a pull request (PR). It then carries that PR until a person merges it. This page describes how the engine is built as a whole. [Engine](engine.md) describes its parts, and [Testing](testing.md) describes how it is tested. [How Cyclix works](../concepts/how-cyclix-works.md) is the same engine seen from the operator's side.

Cyclix is pre-release. Expect every interface to change.

## Principles

Two principles settle the design calls that follow ([ADR-0000](../adr/0000-guiding-principles.md)):

1. Everything the loop does or hears is recorded, in one append-only log. The loop never reads the log to decide anything.
2. A person's attention is the scarce resource.

A third rule follows from them. A PR merges only on a person's approval or under a written rule ([ADR-0001](../adr/0001-merges-need-approval-or-a-written-rule.md)).

## Which part owns which data

Each kind of data has one owner, and Cyclix asks the owner each time ([ADR-0002](../adr/0002-each-kind-of-data-has-one-owner.md)). In the code, one module is the only way to reach each owner:

| Data | The only way to reach it |
| --- | --- |
| Work item status, issues and comments | The `Tracker` protocol, with a GitHub Projects adapter |
| Code, branches and PRs | The `CodeHost` protocol, with a GitHub adapter |
| The loop's working state | The `StateCore` protocol, with a SQLite implementation |
| What happened, in order | The event log writer, `events/log.py` |

The stages and the runner reach SQLite only through `StateCore`. Nothing in the engine names a tracker's own fields. Each tracker adapter maps Cyclix's six work states to that tracker's fields, as [Engine](engine.md) describes.

When the SQLite file and the board disagree, the board wins and the sweep corrects the file.

## The event log

The event log is a record of wide events. A **wide event** covers one unit of work and holds everything needed to understand it. It is written once, when the work ends. [ADR-0004](../adr/0004-wide-events-in-opentelemetry-shape.md) gives the rules, and [Engine](engine.md#the-event-log-schema) gives the fields. There are three kinds of event:

1. **One for each stage run:** admission, plan, build, gate, PR or the reconciler, on one issue. It holds the issue, the PR, the commit SHA, the stage, the outcome and its reason, each gate check's result, the model, tokens, cost, duration, and the engine and config versions. This kind is built.
2. **One for each human act** (coming soon): a merge, a close with its reason, a review round, a card move. It would carry which stage produced the work and how long the work waited on a person.
3. **One when an issue closes** (coming soon): a summary of the issue's whole life.

A crash cannot lose an event. The stage-run event builds up in the SQLite file while the run goes. If the run dies, the next sweep writes it with the outcome `crashed` ([ADR-0003](../adr/0003-the-event-log-is-never-read-to-decide.md)).

## How Cyclix is built

- **Python 3.14, and the standard library by default.** A new runtime dependency needs a written reason in these docs and approval in the PR that adds it ([ADR-0005](../adr/0005-the-standard-library-by-default.md)). The development tools (pytest, pytest-bdd, ruff, coverage and zizmor) are dev dependencies.
- **Adapters wrap the vendor's own tool.** An adapter is the module that talks to one outside system behind a narrow interface. Cyclix builds no HTTP layer. The GitHub adapters call the `gh` command-line program, and the agent adapter runs `claude` ([ADR-0006](../adr/0006-adapters-wrap-the-vendors-cli.md)).
- **The host's service manager does the scheduling.** `cyclix run` makes one pass and exits. On Linux, `cyclix install` writes systemd units that start it on a timer ([ADR-0007](../adr/0007-the-service-manager-runs-one-pass-at-a-time.md)).
- **One item in progress for each tenant** ([ADR-0008](../adr/0008-one-item-in-progress-per-tenant.md)).
- **The agent is Claude Code.** It runs with a tool list for each stage ([ADR-0012](../adr/0012-the-agent-runs-in-dontask-mode-with-stage-tool-lists.md)). It and the gate get no GitHub credential through their environment ([ADR-0013](../adr/0013-the-agent-and-the-gate-get-no-github-credential.md)). [Isolation](isolation.md) describes what that does not stop and the container that is coming soon.

## The feature files are the functional spec

The scenarios in `tests/features/` describe what Cyclix does. They are versioned with the engine. A scenario that changes or is removed is a behaviour change, and the changelog names it. See [Testing](testing.md).

## Decisions

The calls behind this design are in [docs/adr](../adr/README.md).
