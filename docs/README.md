# Cyclix documentation

## For people who run Cyclix

- [How Cyclix works](concepts/how-cyclix-works.md): what Cyclix does, the stages an issue goes through, the work states, and where Cyclix keeps its data.
- [Configuration](reference/configuration.md): every key of the tenant config. [`examples/tenant.toml`](examples/tenant.toml) is the full example.
- [Commands](reference/commands.md): each command and its flags, what it prints, its exit codes, every `cyclix check` line with its fix, and what `cyclix install` puts in the service.

## For people who work on Cyclix's code

- [Architecture](design/architecture.md): the principles, which part owns which data, and how the engine is built.
- [Engine](design/engine.md): the package layout, the state core, the adapters, the state directory, run folders and worktrees, the event log schema, and the sweep.
- [Testing](design/testing.md): the fake GitHub, the fake agent, the shape check and the sandbox. [tests/README.md](../tests/README.md) covers the test layout.
- [Isolation](design/isolation.md): what the agent and the gate can reach, what is built, and what is coming soon.

## The decisions

- [Architecture decision records](adr/README.md): one short file for each settled call, with the options that were weighed.
