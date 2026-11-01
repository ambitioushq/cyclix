# ADR-0007: The build agent writes the PR body

**Status:** Accepted

**Date:** October 2026

## Context

Each PR needs a body that follows the repository's template and says what changed and why.

## Decision

The build agent writes the body as its final answer. The build prompt includes the repository's PR template and asks the agent to end with it filled in. If there is no template, the agent writes a line that closes the issue and a short summary. On GitHub the template is `.github/pull_request_template.md` and the line is `Closes #<issue>`.

The PR stage makes sure the first line is that closing line. The plan does not go into the PR. The PR title is the issue's title.

## Consequences

- The body is the agent's own account of its work, in the tenant's template.
- The body is saved as `pr.md` in the run folder.
- A tenant changes the body's shape by changing its template.

## Alternatives Considered

**The engine writes the body from the plan and the diff.** Rejected. The engine sees what changed, but not why the agent made each change. The body would mostly restate the plan, and the plan stays out of the PR.

**A separate agent call in the PR stage.** Rejected. It costs one more call per run.
