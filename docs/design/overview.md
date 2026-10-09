# Cyclix: design overview

Cyclix is an engine that runs an unattended issue-to-PR loop. It takes a well-formed issue, plans the change, builds it, runs the quality gate, reviews it adversarially, opens a pull request, and carries that PR to a human merge. A person reviews and merges every PR. Cyclix never merges.

This document is the design of record for the engine as a whole. Each part of the engine gets its own design document in this folder as it is built. [iteration-0.md](iteration-0.md) is the first.

## Status

Pre-release. The code here is being written in public from the first commit, and it is not ready for anyone to run. The first public release is v0.1. Until then, expect every interface to change.

## Who owns each fact

Cyclix does not pick one source of truth. Each fact has one owner.

| Fact | Owner |
| --- | --- |
| Work item status, human decisions, comments | The tracker (GitHub Projects first; Jira and others later), through a tracker adapter |
| Code, branches, PRs, reviews, checks | The code host (GitHub first), through a code-host adapter |
| The loop's own working state: claims, the phase inside a stage, round counts, the best verified commit SHA, budget spent | A local SQLite file, one per install |
| What happened, in order | The event log: append-only, never read to make a decision |

- **Cyclix speaks its own work states**: Next, Ready, In progress, In review, Parked, Needs decision, Done. A human moves work to Next to say it should be done soon, and admission promotes it to Ready once it is safe to start. In review holds an item while its PR waits for a human. Each tracker adapter maps them to that tracker's fields. Nothing in the engine names a tracker's own fields.
- **The tracker wins.** When SQLite and the tracker disagree about a work item, the tracker is right and the sweep corrects SQLite. People act in the tracker, so a second copy of their decisions would drift. SQLite holds only facts no tracker has a field for and no human edits.

## The event log

The event log is a ledger of wide events. It serves review, debugging, stats, feedback, and the evidence behind earned trust. The loop never reads it to decide what to do next.

Each event covers one unit of work and holds everything needed to understand it. It is written once, when the work ends. It records what happened to the work and leaves out the steps the code took. There are three kinds:

1. **One per stage run**: admission, plan, build, gate, adversarial review, PR or a reconciler pass, on one issue. It holds the issue, PR, commit SHA, stage, outcome and reason, each gate check's result, the round, model, tokens, cost, duration, the trust level, and the engine and config versions.
2. **One per human act**: a merge, a close with its reason, a review round, a card move. It carries, at write time, which stage produced the work and how long the work waited on a person.
3. **One when an issue closes**: the issue's whole life summed up.

Rules:

- **OpenTelemetry-shaped, local first.** Each event is a log record in the OpenTelemetry data model, written to a local JSON-lines file. If a collector is configured, the same data is also exported over OTLP. A collector that is down never costs a line of the local record.
- **One trace per stage run.** An issue can take days to merge, and tracing tools handle spans open for days badly. Every event carries `cyclix.issue.id`, and grouping by it rebuilds an issue's life.
- **Field names** follow OpenTelemetry where names exist (`gen_ai.*`, `vcs.*`, `cicd.*`). Everything specific to Cyclix goes under `cyclix.*`. Every line records the schema version.
- **A crash cannot lose an event.** The stage-run event builds up in SQLite while the run goes. If the run dies, the next sweep writes it with outcome `crashed`.
- **No sampling.** Cyclix handles tens of issues a week, so it keeps every event.
- **IDs and numbers, never content.** Code, prompts and issue text stay in the run's own files.
- **No query engine.** `cyclix stats` reads the file with plain Python. Any tool that reads JSON lines (DuckDB, for one) can query it too.

## Three principles

1. **Everything the loop does or hears is recorded** in one append-only, OpenTelemetry-shaped log of wide events. The loop never reads it to decide anything.
2. **Trust is set per action in config and earned with evidence.** Each action class moves through four levels: shadow (post the plan and review as comments, push nothing), propose, act with a human check, act alone. When the log shows enough clean outcomes for a class, Cyclix proposes moving it up one level, and a human approves the move.
3. **Human attention is the scarce resource.** The measures are how long work waits in human-owned states, human acts per merge, and follow-up fixes within 30 days.

## How it is built

- **Python 3.14**, installed from PyPI with `uv tool install` or `pipx`. The state core sits behind a narrow interface, so it can be reimplemented later without touching the stages.
- **The standard library by default.** Every runtime dependency needs a written reason in these design docs and is approved by PR. Heavy integrations are optional extras, such as `cyclix[otel]` for OTLP export. Development tools (pytest, pytest-bdd, ruff, coverage, pyright, import-linter) are dev dependencies.
- **Types are checked by pyright in strict mode**, in CI. Strict mode fails on any function that is missing a parameter or return type. Astral's `ty` is not used yet: it is a 0.0.x beta, and behind pyright on the typing spec.
- **Import rules are checked by import-linter**, in CI. Each rule is a contract in `pyproject.toml`, such as "stages never import `adapters.github`". A rule about direct imports only, such as "only adapters import `subprocess`", sets `allow_indirect_imports`, because the runner reaches `subprocess` through the adapters. Rules that are not about imports are tests in `tests/unit/test_tenets.py`.
- **Adapters wrap the vendor's own tool.** Cyclix builds no HTTP layer. The GitHub adapters call the `gh` CLI, which is required only when GitHub is the chosen tracker or code host. `cyclix check` confirms it is installed and signed in.
- **The main host is a Linux VM.** `cyclix install` writes systemd units, so systemd does the scheduling. Containers come later, to isolate each agent session.
- **Webhooks for speed, a periodic sweep for truth.** GitHub never retries a failed webhook delivery, so the sweep stays the source of truth.
- **Agents.** Claude Code first, others later.

## How the work is done

An issue goes through the **stages** of the pipeline in order: admission, plan, build, gate, adversarial review and PR. The reconciler stage acts later, when the PR is merged or closed.

The engine is built one **area** at a time. An area is one stage (admission and the Ready contract, plan, build, gate, adversarial review, PR, reconciler) or one concern that crosses stages (operations, config, identity, trust, feedback, stats, docs). Each area goes through four steps:

1. **Study.** A list of the defects the earlier loop actually met in this area, kept privately by the maintainer, plus the area's numbers and prior art.
2. **Design.** The area's open questions are settled one at a time. The result is a design doc in this folder, `docs/design/<area>.md`, plus the area's acceptance criteria as Gherkin scenarios in `tests/features/`. Each defect from the study that can still happen maps to a scenario.
3. **Build.** The scenarios go in first, failing. Then small PRs make them pass. Unit tests are added only where a scenario cannot reach a rule cheaply.
4. **Learnings.** Notes on what was surprising.

Work done by hand outside the loop, such as a foundations pass, follows a plan in `docs/plans/`.

**The feature files are the functional spec.** They are versioned with the engine. A scenario that changes or is removed is a behaviour change, and the changelog names it.

**Iteration 0 comes first.** It is a minimal version of every stage, so a real issue can travel to a merged PR. Once it works, Cyclix becomes a tenant of its own loop, and later areas are built through it. Design stays supervised, and the maintainer reviews and merges every PR.

## The release order

**Release 1, internal.** What an earlier loop already does, plus the properties that are hard to add later:

- the event log, and the SQLite state core with its GitHub adapters
- full instrumentation, with meter fields named after the OpenTelemetry GenAI conventions
- gate results tied to commit SHAs, with the best verified commit kept, so a round that breaks a passing check rolls back
- a hard cap on rounds behind the progress-based bound
- the Ready contract as a versioned spec in readable text: what an issue must contain to be admitted
- feedback read from what people already do (merged or closed, review rounds, edits before merge, follow-up fixes)
- one config file and `cyclix check --strict`
- a one-time converter from the earlier loop's config

**Release 2, public v0.1.** What matters to someone other than the maintainer:

- a GitHub App as the identity and event source
- `cyclix init`, `cyclix edit`, `cyclix explain`, and `cyclix policy` (a one-page team policy rendered from the config)
- team-based admission and configurable human gates
- one-click feedback: a close reason from a fixed list, and "did this do what you asked?" at merge
- the Ready contract as a diagram, with the docs
- private opt-in stats

**v0.2:** shadow mode, Jira, and the refinement stage that turns a rough issue into a Ready one.

## Contributing

Bug reports are welcome as issues. The maintainer writes the code. GitHub Discussions open with v0.1.
