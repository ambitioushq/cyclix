# Reviewing Cyclix

Cyclix is an engine for an unattended issue-to-PR loop, written in Python 3.14 with the standard library only. One maintainer settles design, and reviews and merges every PR.

Read these before reviewing:

- `CLAUDE.md`: the rules every change follows. Where this file and `CLAUDE.md` differ, `CLAUDE.md` wins.
- `docs/design/overview.md`: what Cyclix is, who owns each fact, and how the work is done.
- `docs/design/iteration-0.md`: the design of the parts built so far.
- `tests/README.md`: how the tests are laid out and tagged.

## Check every PR for these

- The PR body follows `.github/pull_request_template.md`. Its first line is `Closes #<issue>`, or `Refs #<umbrella issue>` for work from a plan in `docs/plans/`.
- The runtime imports only the standard library. A new runtime dependency needs a written reason in the design docs.
- No private project, client or account names, private paths or tokens, in files or commit messages. The repository is public.
- New behaviour has a scenario in `tests/features/`, tagged with the issue that introduced it, such as `@issue-7`. A unit test is used only where a scenario cannot reach a rule cheaply.
- A design choice the PR makes is listed under "Decisions" in the PR body and recorded in a design doc. Flag a design choice made silently.
- Any difference from the issue is listed under "Changed from the issue".
- A code comment says why the code does something a reader could not work out from the code. Flag a comment that describes the change, or names an issue, PR or line number.

## Workflow files

- Every action is pinned to a full commit SHA, with its version in a comment.
- `permissions: {}` sits at the top of each workflow, and each job is granted only what it needs.
- Every checkout sets `persist-credentials: false`.
- harden-runner is the first step of every job.
