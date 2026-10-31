# Reviewing Cyclix

Cyclix is an engine for an unattended issue-to-PR loop, written in Python 3.14 with the standard library only. One maintainer settles design, and reviews and merges every PR.

Read these before reviewing:

- `docs/design/overview.md`: what Cyclix is, who owns each fact, and how the work is done.
- `docs/design/v0.0.md`: the design of the parts built so far.
- `tests/README.md`: how the tests are laid out.

## Check every PR for these

This list holds every rule a change follows that a review can check.

- The PR body follows `.github/pull_request_template.md`. When the PR resolves an issue, its first line is `Closes #<issue>`. A PR without an issue needs no issue line.
- A PR from someone outside `@ambitioushq/maintainers` that changes behaviour links the issue where its approach was agreed. Flag one that does not. The rule above, that a PR without an issue needs no issue line, covers only maintainer PRs.
- The runtime imports only the standard library. A new runtime dependency needs a written reason in the design docs.
- No private project, client or account names, private paths or tokens, in files or commit messages. The repository is public.
- New behaviour has a scenario in the file in `tests/features/` for the capability it describes. A unit test is used only where a scenario cannot reach a rule cheaply.
- A design choice the PR makes is listed under "Design notes" in the PR body and recorded in a design doc. Flag a design choice made silently.
- Any difference from the issue is explained in the Summary.
- The PR body states the change and its reason directly. Flag a body that says who asked for, decided or approved a change, or that mentions the maintainer.
- A code comment says why the code does something a reader could not work out from the code. Flag a comment that describes the change, or names an issue, PR or line number.

## Workflow files

- Every action is pinned to a full commit SHA, with its version in a comment.
- `permissions: {}` sits at the top of each workflow, and each job is granted only what it needs.
- Every checkout sets `persist-credentials: false`.
- harden-runner is the first step of every job.
