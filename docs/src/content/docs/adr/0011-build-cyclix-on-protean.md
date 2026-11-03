---
title: "ADR-0011: Build Cyclix on Protean"
---

**Status:** Accepted

**Date:** November 2026

## Context

[ADR-0004](/adr/0004-use-only-the-standard-library-unless-a-dependency-has-a-written-reason/) kept the runtime to the Python standard library. That fit an engine that makes one pass, keeps its state in one SQLite file and exits. Several planned changes take Cyclix past that shape.

Cyclix becomes a long-running process. Its store moves from one SQLite file to Postgres, and several workers take work from that store. The state Cyclix owns grows. Today it owns claims, stage runs, checks and spend. Later it owns trust levels earned for each class of action, model versions, experiments and learned rules. Each of these has a lifecycle, and a person approves its changes. Cyclix works with several trackers and code hosts through adapters. The operator view reads run history, spend and evidence from Cyclix's own store, because no tracker shows them.

Each of these changes needs the same machinery. Two workers that save the same record need an optimistic version check, so one of them fails instead of overwriting the other. A saved change and the event it raises need an outbox, so neither is lost when the process dies between them. Failed work needs retries. A claim on an item must be one that two workers cannot both take. The schema needs migrations, and the kinds of event need versions so that old events still load.

Protean is a Python framework for domain-driven design (DDD), written by the same maintainer as Cyclix. It already ships and tests version checks, an outbox, a broker, retries, workers and versioned events. Written by hand in Cyclix, these would be a second copy of what Protean provides. The engine is already due to be rewritten around `decide()`, the function that picks an item's next step. Moving onto Protean in that rewrite avoids a second rewrite later.

## Decision

Cyclix is built on Protean.

- The state Cyclix owns is built as Protean aggregates, commands and events. Protean's repositories store it, and Protean's outbox and broker deliver its events.
- `decide()` stays the only function that picks an item's next step. An event handler builds the item's observation, calls `decide()` and sends the command it returns. No other handler or process manager picks a next step.
- [ADR-0002](/adr/0002-each-kind-of-data-has-one-owner/) holds. The tracker owns work states and human decisions, and the code host owns PRs and checks. No aggregate holds a fact that either of them owns.
- Protean's events are kept in a durable event store, such as MessageDB, and never in the in-memory one.
- The database and the broker are Protean settings. Schema changes run through Alembic, which works from the SQLAlchemy tables that Protean's database adapter uses. This record is Alembic's written reason.
- Cyclix pins a released Protean version.
- The event log keeps the format that [ADR-0003](/adr/0003-one-wide-event-per-stage-run-in-opentelemetry-shape/) chose. An event handler writes it.
- Tenant config stays a TOML file.
- Any other runtime dependency, beyond Protean and its own dependencies, still needs a written reason, as [ADR-0008](/adr/0008-offer-shell-completion-through-an-optional-argcomplete-extra/) gave one for argcomplete.

## Consequences

- An install brings Protean and its dependencies, among them SQLAlchemy and pydantic, onto a host that holds tracker and code-host credentials. A lock file with hashes and a dedicated Unix user for the loop limit what a compromised package can reach.
- Cyclix has two kinds of event: Protean's domain events, and its own wide events in the event log.
- Protean lets a handler either save state or call an outside system, never both. So a stage splits into a step that saves and a step that calls out, and the agent session runs outside any handler.
- Spend is recorded as one added row for each stage run, so parallel runs do not conflict on one record.
- A contributor learns Protean's terms: aggregate, command handler, unit of work and outbox.
- A change that Cyclix needs in Protean is made in Protean, and reaches Cyclix in a Protean release.

## Alternatives Considered

**Plain Python.** The engine would be a control loop with a pure decision function, ports and adapters, and decision tables. This keeps the standard library rule, but Cyclix would write the storage, outbox, workers, claims, migrations and event versions by hand.

**Plain Python now, and Protean when several workers share one store.** This defers the dependency, but it rewrites the engine twice: once around `decide()` now, and once onto Protean later.
