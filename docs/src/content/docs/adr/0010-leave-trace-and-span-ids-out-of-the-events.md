---
title: "ADR-0010: Leave trace and span IDs out of the events"
---

**Status:** Accepted

**Date:** November 2026

## Context

[ADR-0003](/adr/0003-one-wide-event-per-stage-run-in-opentelemetry-shape/) made each stage run its own trace. A trace is the set of spans that one piece of work produced, and a span is one timed step inside it. Tracing tools use a trace ID and a span ID to join the spans of one trace. Each event carried a `trace_id` and a `span_id`, and the writer drew both at random for every event.

Cyclix writes log records and no spans. Both IDs pointed at spans that did not exist, and two stages of one run shared no trace, so a reader could not use the IDs to join anything. The events already carry `cyclix.run.id`, which groups a run's events, and `cyclix.issue.id`, which groups an issue's. OpenTelemetry's log data model makes both trace fields optional.

## Decision

Events carry no trace or span ID until they are exported to a tracing tool. The exporter derives the trace ID from the run ID, and the span ID from the run ID and the stage, when it builds the spans.

## Consequences

- A tracing tool cannot read the raw log and join a run's events into one trace. That needs the exporter, which Cyclix does not ship.
- A reader groups a run's events by `cyclix.run.id`, and an issue's by `cyclix.issue.id`.
- The schema keeps version 1. No install has events written under the old shape, so no reader has to tell the two shapes apart.

## Alternatives Considered

**One trace per run, with the trace ID derived from the run ID and one span ID for each stage.** Rejected. The reconciler writes its event under the run's ID when the PR merges, so a run's trace would stretch across the days a PR waits for review. ADR-0003 rejected one trace per issue for the same reason: tracing tools are built for spans that last seconds or minutes, not days.
