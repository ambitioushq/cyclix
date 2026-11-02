---
title: Design
sidebar:
  order: 0
---

A design page describes how Cyclix's code is built and why: its parts, the rules each part keeps, and how it is tested. Design pages are for people who work on Cyclix's code. Each page describes the code as it is, and marks a designed but unbuilt part "Coming soon".

- [Architecture](/design/architecture/): the principles, which part owns which data, and how the engine is built.
- [Engine](/design/engine/): the package layout, the state core, the adapters, the state directory, run folders and worktrees, the event log schema, and the sweep.
- [Testing](/design/testing/): the fake GitHub, the fake agent, the shape check and the sandbox. [tests/README.md](https://github.com/ambitioushq/cyclix/blob/main/tests/README.md) covers the test layout.
- [Isolation](/design/isolation/): what the agent and the gate can reach, what is built, and what is coming soon.

[The docs site's README](https://github.com/ambitioushq/cyclix/blob/main/docs/README.md) says where the pages live in the repository, and how to preview the site.
