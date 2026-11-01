---
title: Cyclix documentation
---

## For people who run Cyclix

- [How Cyclix works](/concepts/how-cyclix-works/): what Cyclix does, the stages an issue goes through, the work states, and where Cyclix keeps its data.
- [Configuration](/reference/configuration/): every key of the tenant config. [`examples/tenant.toml`](https://github.com/ambitioushq/cyclix/blob/main/docs/examples/tenant.toml) is the full example.
- [Commands](/reference/commands/): each command and its flags, what it prints, its exit codes, every `cyclix check` line with its fix, and what `cyclix install` puts in the service.

## For people who work on Cyclix's code

- [Architecture](/design/architecture/): the principles, which part owns which data, and how the engine is built.
- [Engine](/design/engine/): the package layout, the state core, the adapters, the state directory, run folders and worktrees, the event log schema, and the sweep.
- [Testing](/design/testing/): the fake GitHub, the fake agent, the shape check and the sandbox. [tests/README.md](https://github.com/ambitioushq/cyclix/blob/main/tests/README.md) covers the test layout.
- [Isolation](/design/isolation/): what the agent and the gate can reach, what is built, and what is coming soon.
- [The docs site](https://github.com/ambitioushq/cyclix/blob/main/docs/README.md): where the pages live in the repository, and how to preview the site.

## The decisions

- [Architecture decision records](/adr/): one short file for each settled call, with the options that were weighed.
