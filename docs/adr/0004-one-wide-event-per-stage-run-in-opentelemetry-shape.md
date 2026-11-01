# ADR-0004: Write one wide event per stage run, in OpenTelemetry shape, as local JSON lines

**Status:** Accepted

**Date:** October 2026

## Context

People need to query the record afterwards, for example to see which stage costs the most or why runs stop at the gate. Cyclix handles tens of issues a week, and an issue can take days to reach a merge.

## Decision

- Each stage run writes one wide event. A wide event holds everything needed to understand one piece of work, and is written once, when the work ends.
- Each event is a log record in the OpenTelemetry data model. Field names follow OpenTelemetry where it has one (`gen_ai.*`, `vcs.*`, `cicd.*`). Cyclix's own fields start with `cyclix.`. Every line records the schema version.
- Events go to a local file under the state directory, one JSON object per line. Cyclix ships no query tool.
- Each stage run is its own trace. Every event carries `cyclix.issue.id`, so grouping by it shows an issue's whole life.
- Keep every event. Do not sample.
- Events hold IDs and numbers, never content. The writer refuses a string over 500 characters.

## Consequences

- One query follows an issue through the stages.
- Tools built for OpenTelemetry can read the events with little change.
- The writer refuses a key that is not in the schema. Add a new key to [Engine](../design/engine.md#the-event-log-schema) first, then to `events/schema.py`.
- A change to the schema raises the version.

## Alternatives Considered

**Many small events, one per step the code takes.** Rejected. The log should say what happened to the work, not what the code did.

**One trace per issue.** Rejected. Tracing tools handle spans that stay open for days badly.

**Sampling.** Rejected. At tens of issues a week, keeping every event costs little.
