# ADR-0005: The standard library by default, with a written reason for each runtime dependency

**Status:** Accepted

**Date:** October 2026

## Context

Cyclix runs unattended on a host with access to a GitHub login. Each package it imports is code that runs with that access, and each one is a version to keep current. The engine's needs are modest: read TOML, keep state in SQLite, run subprocesses, write JSON lines and parse arguments.

## Decision

The engine imports only the Python standard library at runtime. A new runtime dependency needs a reason written in the design docs and approval in the PR that adds it.

Development tools (pytest, pytest-bdd, ruff, coverage and zizmor) are dev dependencies and are not part of this rule.

Host programs are not Python dependencies. Cyclix needs `git`, and needs `gh` when GitHub is the tracker or the code host, as [ADR-0006](0006-adapters-wrap-the-vendors-cli.md) explains. The container tool in [Isolation](../design/isolation.md) would be a host program too.

## Consequences

- The engine uses `tomllib`, `sqlite3`, `argparse`, `logging`, `subprocess`, `fcntl` and `hashlib`.
- Installing Cyclix pulls in no other package.
- A task that a library would do well, such as an HTTP client, is either written against the standard library or done by a host program.
