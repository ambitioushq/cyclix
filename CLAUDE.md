# Working on Cyclix

Cyclix is built in supervised sessions. The maintainer settles design, and reviews and merges every PR. Read `docs/design/overview.md` first, then the design doc for the part you are working on.

## Rules for every change

- **The PR body follows `.github/pull_request_template.md` in full.** When a PR resolves an issue, its first line is `Closes #<issue>`. A PR without an issue needs no issue line.
- **Scenarios first.** Write the change's acceptance scenarios before the code, and confirm they fail. Each goes in the file in `tests/features/` for the capability it describes. Unit tests only where a scenario cannot reach a rule cheaply.
- **Never edit an issue's body after it is filed.** Record any difference from it under "Changed from the issue" in the PR.
- **A design question goes to the maintainer.** Do not settle it alone. Record the answer in the design doc in the same PR, and list it under "Decisions".
- **The repository is public.** No private project, client or account names, no private paths, no tokens. No CI job checks names or paths, so that is on you.
- **Standard library only at runtime.** A new runtime dependency needs a written reason in the design docs and the maintainer's approval in the PR.
- **Never merge, never force-push to `main`.** The maintainer merges, by squash, so `main` has one commit per PR.
- **Markdown-only changes go straight to `main`, with no PR.** A Markdown-only change touches only Markdown files: the design docs, the README, `SECURITY.md`, this file, `.github/copilot-instructions.md`, the PR template, `tests/README.md` and skills under `.claude/`. Rebase on `main` first, because `main` keeps a linear history, and push one commit per change. The commit message does the PR body's job: the subject says what changed, and the body says why and lists any decisions. Never write a closing keyword in that commit message, because a commit on `main` closes the issue it names. Design answers still come from the maintainer before they are written down. Everything else goes through a PR: code, tests, feature files, CI, config, and any file that can run commands, such as `.claude/settings.json` and the workflows.
- Python 3.14, `uv` for everything: `uv run ruff check`, `uv run ruff format`, `uv run pytest`.
