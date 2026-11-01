# ADR-0005: The standard library by default, with a written reason for each runtime dependency

**Status:** Accepted

**Date:** October 2026

## Context

Cyclix runs unattended on a host that holds a GitHub login. Each imported package runs with that access and needs updates. The engine's needs are small: TOML, SQLite, subprocesses, JSON lines and argument parsing.

## Decision

The engine imports only the Python standard library at runtime. A new runtime dependency needs a reason written in the design docs and approval in the PR that adds it.

Development tools are dev dependencies and are outside this rule. Host programs such as `git`, `gh` and a container tool are not Python dependencies.

## Consequences

- Installing Cyclix installs no other package.
- A task a library would do, such as an HTTP client, is written against the standard library or left to a host program.
