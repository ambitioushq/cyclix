# Architecture decision records

An architecture decision record (ADR) is one short file about one decision. It says what the options were, what Cyclix chose, and what follows from the choice. Read one when you want to reopen a decision: it holds the reasons that were weighed.

Files are named `NNNN-kebab-title.md`, numbered from `0000`. [TEMPLATE.md](TEMPLATE.md) is the shape of a record. A decision gets a record when it chose between options that a contributor might reasonably reopen. A decision with nothing reasonable against it keeps its reason in the design text.

A record is not edited to change a decision. A new record replaces it, and the old one's status becomes `Superseded by ADR-NNNN`.

| ADR | Decision | Status |
| --- | --- | --- |
| [0000](0000-guiding-principles.md) | Guiding principles | Accepted |
| [0001](0001-merge-only-after-approval-or-under-a-written-rule.md) | Cyclix merges a PR only after a person approves it or a written rule allows it | Accepted |
| [0002](0002-each-kind-of-data-has-one-owner.md) | Each kind of data has one owner | Accepted |
| [0003](0003-the-loop-writes-the-event-log-but-never-reads-it.md) | The loop writes the event log but never reads it | Accepted |
| [0004](0004-one-wide-event-per-stage-run-in-opentelemetry-shape.md) | Write one wide event per stage run, in OpenTelemetry shape, as local JSON lines | Accepted |
| [0005](0005-use-only-the-standard-library-unless-a-dependency-has-a-written-reason.md) | Use only the standard library unless a dependency has a written reason | Accepted |
| [0006](0006-test-against-fake-outside-systems-that-keep-state.md) | Test against fake outside systems that keep state, not recorded answers | Accepted |
| [0007](0007-the-build-agent-writes-the-pr-body.md) | The build agent writes the PR body | Accepted |
| [0008](0008-run-the-agent-without-approval-prompts-and-with-a-tool-list-per-stage.md) | Run the agent without approval prompts, with a tool list for each stage, and allow only listed flags in its command | Accepted |
| [0009](0009-keep-code-host-credentials-out-of-the-agent-and-the-gate.md) | Keep code host credentials out of the agent's and the gate's environment | Accepted |
