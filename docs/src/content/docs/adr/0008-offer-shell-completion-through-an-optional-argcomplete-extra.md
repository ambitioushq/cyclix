---
title: "ADR-0008: Offer shell completion through an optional argcomplete extra"
---

**Status:** Accepted

**Date:** November 2026

## Context

An operator types `cyclix` commands and flags by hand, and shell completion saves them from looking each one up. The standard library's `argparse` cannot complete in a shell. Each shell needs its own completion script, and bash, zsh and fish each use a different format. [ADR-0004](/adr/0004-use-only-the-standard-library-unless-a-dependency-has-a-written-reason/) allows a runtime dependency only with a written reason, because every package that Cyclix imports runs on a host that is signed in to the tracker and the code host.

argcomplete is a small package that completes from an `argparse` parser in bash, zsh and fish. It reads the parser that Cyclix already builds, so the completions follow every change to the commands.

## Decision

Cyclix offers shell completion through an optional dependency group named `extras`, which holds argcomplete. A plain install of Cyclix installs no other package. `cli.py` imports argcomplete when it is installed and registers the parser with it. When argcomplete is missing, Cyclix runs as before, with no completion. The parser stays `argparse`.

## Consequences

- A plain install still imports only the standard library, so ADR-0004 holds for every host that does not ask for completion.
- An operator who wants completion installs the `extras` group and adds one line to the shell's startup file. [Commands](/reference/commands/#turn-on-shell-completion) gives the line for each shell.
- On a host with the extra installed, every `cyclix` run imports argcomplete, the unattended runs from the timer included. argcomplete does its work only when the shell asks for completions.
- Cyclix's tests run with argcomplete installed, and one test hides it to show that Cyclix still runs without it.

## Alternatives Considered

**Completion scripts written by hand.** Cyclix would ship one script for each shell. That keeps the standard library rule with no extra, but each script must change with every command or flag, and three formats drift apart from the parser.

**A command-line framework, such as Click or Typer.** These complete in every shell, but they replace `argparse` and make a runtime dependency of every install, which ADR-0004 asks to avoid when the standard library does the job.

**No completion.** This keeps the code smallest, and the operator looks up each flag in `--help` or this documentation.
