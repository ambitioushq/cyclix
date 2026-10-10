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
- Python 3.14, `uv` for everything: `uv run ruff check`, `uv run ruff format`, `uv run pytest`.
