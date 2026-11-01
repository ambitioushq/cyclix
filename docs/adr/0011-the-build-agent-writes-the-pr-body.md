# ADR-0011: The build agent writes the PR body

**Status:** Accepted

**Date:** October 2026

## Context

Each PR needs a body that follows the repository's template and says what changed and why. The agent that built the change knows that best. Something has to write the body, and a person reads it first when reviewing.

## Decision

The build agent writes the PR body as the final answer of its call. The build prompt includes the repository's `.github/pull_request_template.md`, read from the worktree, and asks the agent to end with that template filled in. A repository without the template gets `Closes #<issue>` and a short plain summary.

The PR stage makes sure the body's first line is `Closes #<issue>` and adds it when it is missing. The plan stays in the run folder and does not go into the PR. The PR title is the issue's title alone, because `Closes #<issue>` already links the issue and GitHub adds the PR number when it squashes.

## Consequences

- The PR body is the agent's own words about its own work, in the tenant's template.
- The body is saved as `pr.md` in the run folder, so a person can compare it with the PR.
- A tenant changes the body's shape by changing its template, with no change to Cyclix.

## Alternatives Considered

**A separate agent call in the PR stage to write the body.** Left out because it costs one more call for each run.
