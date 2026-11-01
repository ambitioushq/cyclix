# ADR-0004: Wide events, shaped like OpenTelemetry, written to local JSON lines

**Status:** Accepted

**Date:** October 2026

## Context

Cyclix needs a record that a person can query after the fact, for example to ask which stage costs the most or why runs stop at the gate. The loop handles tens of issues a week, and an issue can take days to reach a merge.

## Decision

- **One wide event for each unit of work.** A wide event holds everything needed to understand one unit of work, and is written once, when the work ends. It records what happened to the work and leaves out the steps the code took. There is one event for each stage run.
- **The OpenTelemetry log record shape.** Each event is a log record in the OpenTelemetry data model. Field names follow OpenTelemetry where a name exists (`gen_ai.*`, `vcs.*`, `cicd.*`). Everything specific to Cyclix goes under `cyclix.*`. Every line records its schema version.
- **Local JSON lines.** Each event is one line in a file under the state directory. Any tool that reads JSON lines, such as DuckDB, can query it. Cyclix ships no query engine.
- **One trace for each stage run.** Every event also carries the issue's number, so grouping by it rebuilds the life of an issue.
- **No sampling.** Cyclix keeps every event.
- **IDs and numbers, never content.** Code, prompts and issue text stay in the run's own folder. The writer refuses a string longer than 500 characters, because a string that long is most likely prompt or code text.

## Consequences

- A person can follow one issue through the stages with one query.
- A tool built for OpenTelemetry can read the events with little change.
- The writer refuses any key outside the schema, so a new key is added to [Engine](../design/engine.md) first and then to `events/schema.py`.
- A change to the schema bumps its version, because a reader of older lines expects the old keys.

## Alternatives Considered

**Many small events, one for each step the code takes.** Rejected because the log serves a person asking what happened to the work, and the steps of the code are not the work.

**One trace for each issue.** Rejected because an issue can take days to merge, and tracing tools handle spans that stay open for days badly.

**Sampling.** Rejected because Cyclix handles tens of issues a week, so keeping every event costs little.
