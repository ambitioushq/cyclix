# Reviewing Cyclix

Cyclix is an engine for an unattended issue-to-PR loop, written in Python 3.14 with the standard library only. One maintainer settles design, and reviews and merges every PR.

Read these before reviewing:

- `docs/src/content/docs/index.md`: lists every document.
- `docs/src/content/docs/design/architecture.md` and `docs/src/content/docs/design/engine.md`: how the engine is built, and its parts.
- `docs/src/content/docs/adr/`: the settled design calls, with the options that were weighed.
- `tests/README.md`: how the tests are laid out.

## Check every PR for these

This list holds every rule a change follows that a review can check.

- The PR body follows `.github/pull_request_template.md`. When the PR resolves an issue, its first line is `Closes #<issue>`. A PR without an issue needs no issue line.
- Every PR from someone outside `@ambitioushq/maintainers` links the issue where its approach was agreed, however small the change. Flag one that does not. The rule above, that a PR without an issue needs no issue line, covers only maintainer PRs.
- The runtime imports only the standard library. A new runtime dependency needs a written reason in the design docs.
- No private project, client or account names, private paths or tokens, in files or commit messages. The repository is public.
- New behaviour has a scenario in the file in `tests/features/` for the capability it describes. A unit test is used only where a scenario cannot reach a rule cheaply.
- A design choice the PR makes is listed under "Design notes" in the PR body and recorded in a design doc. Flag a design choice made silently.
- Any difference from the issue is explained in the Summary.
- The PR body states the change and its reason directly. Flag a body that says who asked for, decided or approved a change, or that mentions the maintainer.
- A docstring states the contract a caller relies on: what the code does, returns, raises or changes. Flag a docstring that walks through how the code works, or states a behaviour promise no test checks.
- A code comment says why the code does something a reader could not work out from the code. Flag a comment that describes the change, or names a line number, a count or version history. Flag commented-out code. The version beside a pinned action's SHA is required (see "Workflow files").
- Flag an issue or PR number in a comment or docstring, except in `TODO(#123): reason` or in a regression test's docstring that states the behaviour in words first. An issue in another repo uses the full name (`owner/repo#123`).

## Workflow files

- Every action is pinned to a full commit SHA, with its version in a comment.
- `permissions: {}` sits at the top of each workflow, and each job is granted only what it needs.
- Every checkout sets `persist-credentials: false`.
- harden-runner is the first step of every job.
