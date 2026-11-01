# ADR-0004: Wide events, shaped like OpenTelemetry, written to local JSON lines

**Status:** Accepted

**Date:** October 2026

## Context

Cyclix needs a record that a person can query afterwards, such as which stage costs the most or why runs stop at the gate. It handles tens of issues a week, and an issue can take days to reach a merge.

## Decision

- One wide event for each stage run. A wide event holds everything needed to understand one unit of work, and is written once, when the work ends.
- Each event is a log record in the OpenTelemetry data model. Field names follow OpenTelemetry where a name exists (`gen_ai.*`, `vcs.*`, `cicd.*`). Cyclix's own fields go under `cyclix.*`. Every line records its schema version.
- Events are written as JSON lines to a local file under the state directory. Cyclix ships no query engine.
- Each stage run is its own trace. Every event carries `cyclix.issue.id`, so grouping by it rebuilds an issue's life.
- No sampling.
- Events hold IDs and numbers, never content. The writer refuses a string longer than 500 characters.

## Consequences

- One query follows an issue through the stages.
- Tools built for OpenTelemetry read the events with little change.
- The writer refuses a key outside the schema. A new key is added to [Engine](../design/engine.md#the-event-log-schema) first, then to `events/schema.py`.
- A schema change bumps the version.

## Alternatives Considered

**Many small events, one for each step the code takes.** Rejected. The log answers what happened to the work, not what the code did.

**One trace for each issue.** Rejected. Tracing tools handle spans that stay open for days badly.

**Sampling.** Rejected. At tens of issues a week, keeping every event costs little.
