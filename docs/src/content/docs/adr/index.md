---
title: Architecture decision records
---

An architecture decision record (ADR) is one short file about one decision. It says what the options were, what Cyclix chose, and what follows from the choice. Read one when you want to reopen a decision: it holds the reasons that were weighed.

Files are named `NNNN-kebab-title.md`, numbered from `0000`. [`_template.md`](https://github.com/ambitioushq/cyclix/blob/main/docs/src/content/docs/adr/_template.md) is the shape of a record. Its name starts with an underscore, so the site leaves it out. A decision gets a record when it chose between options that a contributor might reasonably reopen. A decision with nothing reasonable against it keeps its reason in the design text.

A record is not edited to change a decision. A new record replaces it, and the old one's status becomes `Superseded by ADR-NNNN`.

| ADR | Decision | Status |
| --- | --- | --- |
| [0000](/adr/0000-guiding-principles/) | Guiding principles | Accepted |
| [0001](/adr/0001-merge-only-after-approval-or-under-a-written-rule/) | Cyclix merges a PR only after a person approves it or a written rule allows it | Accepted |
| [0002](/adr/0002-each-kind-of-data-has-one-owner/) | Each kind of data has one owner | Accepted |
| [0003](/adr/0003-one-wide-event-per-stage-run-in-opentelemetry-shape/) | Write one wide event per stage run, in OpenTelemetry shape, as local JSON lines | Accepted |
| [0004](/adr/0004-use-only-the-standard-library-unless-a-dependency-has-a-written-reason/) | Use only the standard library unless a dependency has a written reason | Accepted |
| [0005](/adr/0005-confine-the-agent-and-the-gate/) | Confine the agent and the gate | Accepted |
| [0006](/adr/0006-build-the-docs-site-with-astro-and-starlight/) | Build the docs site with Astro and Starlight | Accepted, deploy replaced by 0007 |
| [0007](/adr/0007-deploy-the-docs-site-through-the-hosts-git-integration/) | Deploy the docs site through the host's Git integration | Accepted |
