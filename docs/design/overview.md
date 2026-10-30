# Cyclix: design overview

Cyclix is an engine that runs an unattended issue-to-PR loop. It takes a well-formed issue, plans the change, builds it, runs the quality gate, reviews it adversarially, opens a pull request, and carries that PR to a human merge. A person reviews and merges every PR. Cyclix never merges.

This document is the design of record for the engine as a whole. Each part of the engine gets its own design document in this folder as it is built. [v0.0.md](v0.0.md) is the first.

## Status

Pre-release. The code here is being written in public from the first commit, and it is not ready for anyone to run. Expect every interface to change.

## Who owns each fact

Cyclix does not pick one source of truth. Each fact has one owner.

| Fact | Owner |
| --- | --- |
| Work item status, human decisions, comments | The tracker (GitHub Projects), through a tracker adapter |
| Code, branches, PRs, reviews, checks | The code host (GitHub first), through a code-host adapter |
| The loop's own working state: claims, the phase inside a stage, round counts, the best verified commit SHA, budget spent | A local SQLite file, one per install |
| What happened, in order | The event log: append-only, never read to make a decision |

- **Cyclix speaks its own work states**: Ready, In progress, In review, Parked, Needs decision, Done. A human moves work to Ready, and admission takes the oldest Ready item. Coming soon: a Next state, where a human moves work to say it should be done soon, and admission promotes it to Ready once it is safe to start. In review holds an item while its PR waits for a human. Each tracker adapter maps them to that tracker's fields. Nothing in the engine names a tracker's own fields.
- **The tracker wins.** When SQLite and the tracker disagree about a work item, the tracker is right and the sweep corrects SQLite. People act in the tracker, so a second copy of their decisions would drift. SQLite holds only facts no tracker has a field for and no human edits.

## The event log

The event log is a ledger of wide events. It serves review and debugging. The loop never reads it to decide what to do next.

Each event covers one unit of work and holds everything needed to understand it. It is written once, when the work ends. It records what happened to the work and leaves out the steps the code took. There are three kinds:

1. **One per stage run**: admission, plan, build, gate, adversarial review, PR or a reconciler pass, on one issue. It holds the issue, PR, commit SHA, stage, outcome and reason, each gate check's result, the round, model, tokens, cost, duration, the trust level, and the engine and config versions.
2. **One per human act** (Coming soon): a merge, a close with its reason, a review round, a card move. It carries, at write time, which stage produced the work and how long the work waited on a person.
3. **One when an issue closes** (Coming soon): the issue's whole life summed up.

Rules:

- **OpenTelemetry-shaped, local first.** Each event is a log record in the OpenTelemetry data model, written to a local JSON-lines file.
- **One trace per stage run.** An issue can take days to merge, and tracing tools handle spans open for days badly. Every event carries `cyclix.issue.id`, and grouping by it rebuilds an issue's life.
- **Field names** follow OpenTelemetry where names exist (`gen_ai.*`, `vcs.*`, `cicd.*`). Everything specific to Cyclix goes under `cyclix.*`. Every line records the schema version.
- **A crash cannot lose an event.** The stage-run event builds up in SQLite while the run goes. If the run dies, the next sweep writes it with outcome `crashed`.
- **No sampling.** Cyclix handles tens of issues a week, so it keeps every event.
- **IDs and numbers, never content.** Code, prompts and issue text stay in the run's own files.
- **No query engine.** Any tool that reads JSON lines (DuckDB, for one) can query it.

## Two principles

1. **Everything the loop does or hears is recorded** in one append-only, OpenTelemetry-shaped log of wide events. The loop never reads it to decide anything.
2. **Human attention is the scarce resource.**

## How it is built

- **Python 3.14.** The state core sits behind a narrow interface.
- **The standard library by default.** Every runtime dependency needs a written reason in these design docs and is approved by PR. Development tools (pytest, pytest-bdd, ruff, coverage) are dev dependencies.
- **Adapters wrap the vendor's own tool.** Cyclix builds no HTTP layer. The GitHub adapters call the `gh` CLI, which is required only when GitHub is the chosen tracker or code host. `cyclix check` confirms it is installed and signed in.
- **The main host is a Linux VM.** `cyclix install` writes systemd units, so systemd does the scheduling.
- **The agent and the gate get no GitHub credential through their environment.** The engine holds the GitHub credential and does every push itself. The agent and the gate get a short allow-list of environment variables, `gh` finds no login, and git reads no credential helper. They still run as the host user with the real `HOME`, so code they run can read a credential file there, such as `~/.config/gh/hosts.yml`, by its full path. Coming soon: each agent call and each gate run gets a fresh rootless Podman container that holds the run's own clone and the Claude login, and nothing else from the host, which closes that gap. Podman is a host requirement, not a Python dependency. [isolation.md](isolation.md) is the design, and says which parts are built.
- **Agents.** Claude Code.

## How the work is done

An issue goes through the **stages** of the pipeline in order: admission, plan, build, gate, adversarial review and PR. The reconciler stage acts later, when the PR is merged or closed.

**The feature files are the functional spec.** They are versioned with the engine. A scenario that changes or is removed is a behaviour change, and the changelog names it.

**v0.0 comes first.** It is a minimal version of every stage, so a real issue can travel to a merged PR. Once it works, Cyclix becomes a tenant of its own loop. Design stays supervised, and the maintainer reviews and merges every PR.

## Contributing

Bug reports are welcome as issues. The maintainer writes the code.
