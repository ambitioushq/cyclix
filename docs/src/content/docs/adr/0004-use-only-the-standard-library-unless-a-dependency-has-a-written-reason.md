---
title: "ADR-0004: Use only the standard library unless a dependency has a written reason"
---

**Status:** Accepted

**Date:** October 2026

## Context

Cyclix runs unattended on a host that is logged in to the tracker and the code host. Every package it imports runs with that access and needs updates. What the engine needs is small: TOML, a database, subprocesses, JSON lines and argument parsing.

## Decision

At runtime the engine imports only the Python standard library. A new runtime dependency needs a reason written in the design docs, and approval in the PR that adds it.

Development tools are not covered by this rule. Programs on the host, such as `git`, `gh` and a container tool, are not Python dependencies.

## Consequences

- Installing Cyclix installs no other package.
- A job that a library would do, such as an HTTP client, is written with the standard library.
