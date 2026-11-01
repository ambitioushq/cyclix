# Architecture decision records

An architecture decision record (ADR) is one short file about one decision. It says what the options were, what Cyclix chose, and what follows from the choice. Read one when you want to reopen a decision: it holds the reasons that were weighed.

Files are named `NNNN-kebab-title.md`, numbered from `0000`. [TEMPLATE.md](TEMPLATE.md) is the shape of a record. A decision gets a record when it chose between options that a contributor might reasonably reopen. A decision with nothing reasonable against it keeps its reason in the design text.

A record is not edited to change a decision. A new record replaces it, and the old one's status becomes `Superseded by ADR-NNNN`.

| ADR | Decision | Status |
| --- | --- | --- |
| [0000](0000-guiding-principles.md) | Everything the loop does is recorded, and a person's attention is the scarce resource | Accepted |
| [0001](0001-cyclix-never-merges.md) | Cyclix never merges, and a person merges every PR | Accepted |
| [0002](0002-each-kind-of-data-has-one-owner.md) | Each kind of data has one owner, and the board wins over the state file | Accepted |
| [0003](0003-the-event-log-is-never-read-to-decide.md) | The event log is a record the loop never reads to decide | Accepted |
| [0004](0004-wide-events-in-opentelemetry-shape.md) | Wide events, shaped like OpenTelemetry, written to local JSON lines | Accepted |
| [0005](0005-the-standard-library-by-default.md) | The standard library by default, with a written reason for each runtime dependency | Accepted |
| [0006](0006-adapters-wrap-the-vendors-cli.md) | Adapters wrap the vendor's CLI, with no HTTP layer | Accepted |
| [0007](0007-the-service-manager-runs-one-pass-at-a-time.md) | The host's service manager runs one pass at a time, with no long-running process | Accepted |
| [0008](0008-one-item-in-progress-per-tenant.md) | One item in progress per tenant | Accepted |
| [0009](0009-the-fake-github-is-a-world-model.md) | The fake GitHub is a world model built for the tests, with no replayed recordings | Accepted |
| [0010](0010-the-board-is-read-with-narrow-graphql-queries.md) | The board is read with narrow GraphQL queries | Accepted |
| [0011](0011-the-build-agent-writes-the-pr-body.md) | The build agent writes the PR body | Accepted |
| [0012](0012-the-agent-runs-in-dontask-mode-with-stage-tool-lists.md) | The agent runs in `dontAsk` mode with a tool list for each stage, and its command takes only allow-listed flags | Accepted |
| [0013](0013-the-agent-and-the-gate-get-no-github-credential.md) | The agent and the gate get no GitHub credential through their environment | Accepted |
| [0014](0014-private-instruction-files-come-from-one-config-folder.md) | A tenant's private instruction files come from one folder named in its config, copied into each run's worktree | Accepted |
