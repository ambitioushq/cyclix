# ADR-0011: The build agent writes the PR body

**Status:** Accepted

**Date:** October 2026

## Context

Each PR needs a body that follows the repository's template and says what changed and why.

## Decision

The build agent writes the body as its final answer. The build prompt includes the repository's `.github/pull_request_template.md` and asks the agent to end with it filled in. If there is no template, the agent writes `Closes #<issue>` and a short summary.

The PR stage makes sure the first line is `Closes #<issue>`. The plan does not go into the PR. The PR title is the issue's title.

## Consequences

- The body is the agent's own account of its work, in the tenant's template.
- The body is saved as `pr.md` in the run folder.
- A tenant changes the body's shape by changing its template.

## Alternatives Considered

**A separate agent call in the PR stage.** Rejected. It costs one more call per run.
