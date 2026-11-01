# Testing

This page describes what the tests run against: a fake GitHub, a fake agent, a check on the fake's output shapes, and a sandbox on real GitHub. [tests/README.md](../../tests/README.md) describes how the test folders are laid out and the shared steps.

The scenarios in `tests/features/` are Cyclix's functional spec (see [Architecture](architecture.md#the-feature-files-are-the-functional-spec)). They run through pytest-bdd, which reads Gherkin feature files. A **scenario** is one example of behaviour written as Given, When and Then steps. The engine runs as a subprocess, the way systemd runs it.

## The fake GitHub is a world model

The fake GitHub is a model of GitHub's state, not a set of replayed recordings. A new scenario needs no new recording, and a scenario can make any one call fail.

- **The fake world** (`tests/fakes/world.py`) is a JSON file that holds issues, a board with items and states, and PRs and their states. A scenario's Given steps write it, and its Then steps read it.
- **The fake `gh`** is an executable placed first on `PATH`. It supports only the `gh` commands that [Engine](engine.md#the-adapters) lists, reads and changes the world, prints output in the same JSON shape as the real `gh`, and appends each call to a calls file. A scenario can inject a fault for one call: an exit code, a stderr message or a stale read.
- **The fake agent** is an executable named in the test config's `agent.command`. A scenario gives it a script: files to write, commits to make, the text to answer, the exit code, and the token and cost numbers to report. It prints the lines that `claude -p --output-format stream-json --verbose` prints.
- **The fake `systemctl`** accepts only the calls that `cyclix install` and `uninstall` make, and changes nothing.
- **The git remote** is a local bare repository, so pushes are real.

## The shape check keeps the fake honest

A fake that returns the wrong keys would pass tests that the real `gh` fails. The shape check prevents that.

`scripts/record_gh_shapes.py` runs each command that the adapters read against the sandbox. It writes `tests/fixtures/gh-shapes/<command>.json`. For a JSON command, the file holds the sorted key paths of the output, with a list's elements under `<list>[]`. `pr create` prints a URL that the code host parses, so its file holds that line with the repository and number masked. Nothing reads the output of `project item-edit` or `issue comment`, so neither is recorded. The three board queries are recorded as `graphql-board-fields`, `graphql-board-items` and `graphql-board-item`. Each file holds a placeholder for the query text, so a changed query is caught only when the shapes are recorded again.

A scenario runs the fake `gh` on the same commands and fails if its output has other keys. When the real `gh` changes, record the shapes again, commit them, and change the fake until the scenario passes.

## The sandbox runs against real GitHub

The sandbox is a private repository, `ambitioushq/cyclix-sandbox`, and a private board, `ambitioushq` project 2, whose Status field holds the six option names. Its tenant config is [`docs/examples/sandbox.toml`](../examples/sandbox.toml).

Scenarios tagged `@sandbox` run against it with the real `gh` and the real agent, and only when `CYCLIX_SANDBOX=1`. The workflow `sandbox.yml` runs them by hand and weekly, never on a PR.

- **The scenario merges the PR itself.** A real run waits for a person to merge. The scenario runs `gh pr merge --squash`, so the weekly run needs nobody.
- **The real agent runs as the tenant config says**, in `dontAsk` mode with the stage's tools. The sandbox's build stage may run `python3 -m unittest`, which is its gate.
- **The sandbox is throwaway.** Each scenario first closes every open issue and PR in the sandbox and empties the board, in case an earlier run died. At the end it closes and deletes what it made.
- **The workflow records the shapes again** after the scenarios, and fails if they changed.
