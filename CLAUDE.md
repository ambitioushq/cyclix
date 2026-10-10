# Working on Cyclix

Cyclix is built in supervised sessions. The maintainer settles design, and reviews and merges every PR. Read `docs/design/overview.md` first, then the design doc for the part you are working on.

## Rules for every change

- **One issue, one PR.** The PR body follows `.github/pull_request_template.md` in full, and its first line is `Closes #<issue>`.
- **Work from a plan uses `Refs`.** A PR that works from a plan in `docs/plans/` starts with `Refs #<umbrella issue>` in place of `Closes #<issue>`. It names the plan section it covers, and ticks that section's boxes in the same PR.
- **Scenarios first.** Write the issue's acceptance scenarios into `tests/features/` before the code, and confirm they fail. Unit tests only where a scenario cannot reach a rule cheaply.
- **Tag every scenario with the issue that introduced it**, such as `@issue-7`. A later PR that changes a scenario keeps the original tag and adds its own.
- **Never edit an issue's body after it is filed.** Record any difference from it under "Changed from the issue" in the PR.
- **A design question goes to the maintainer.** Do not settle it alone. Record the answer in the design doc in the same PR, and list it under "Decisions".
- **The repository is public.** No private project, client or account names, no private paths, no tokens. No CI job checks names or paths, so that is on you.
- **Standard library only at runtime.** A new runtime dependency needs a written reason in the design docs and the maintainer's approval in the PR.
- **Never merge, never force-push to `main`.** The maintainer merges, by squash, so `main` has one commit per PR.
- **Docs-only changes go straight to `main`, with no PR.** A docs-only change touches only Markdown files outside `.github/` and `tests/`: the design docs, the plans, the README, `SECURITY.md` and this file. Rebase on `main` first, because `main` keeps a linear history, and push one commit per change. The commit message does the PR body's job: the subject says what changed, the body says why and lists any decisions, and work from a plan starts the body with `Refs #<umbrella issue>`. Never write a closing keyword in that commit message, because a commit on `main` closes the issue it names. Design answers still come from the maintainer before they are written down. Code, tests, feature files, CI, config and anything under `.github/` always go through a PR.
- Python 3.14, `uv` for everything: `uv run ruff check`, `uv run ruff format`, `uv run pytest`.
