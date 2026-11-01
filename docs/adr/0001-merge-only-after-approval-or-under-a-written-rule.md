# ADR-0001: Cyclix merges a PR only after a person approves it or a written rule allows it

**Status:** Accepted

**Date:** October 2026

## Context

The loop writes code with nobody watching, from text that others can influence. A merge puts that code on the base branch. A person's attention is the scarce resource ([ADR-0000](0000-guiding-principles.md)), so routine PRs should not all wait for one.

## Decision

Cyclix merges a PR in two cases:

1. A designated person has approved it.
2. A written rule covers it. The rule names a class of PR, such as a lockfile refresh or a dependency bot's PR, and its conditions, such as CI green and the review approved.

Every other PR waits for a person to merge it. Only the engine merges. The agent and the gate never do ([ADR-0013](0013-keep-code-host-credentials-out-of-the-agent-and-the-gate.md)).

## Consequences

- Branch protection on the base branch is the backstop. `cyclix check` confirms that it requires a pull request and refuses force-pushes and deletion.
- Each merge is recorded with the approval or the rule that allowed it.
- A PR that no rule covers waits In review. A limit on In review caps how many wait ([ADR-0008](0008-work-on-one-item-at-a-time-per-tenant.md)).
- A change to a rule is reviewed like a change to code, because it widens what the loop merges.

## Alternatives Considered

**A person merges every PR.** Rejected as the only path. Routine PRs would use the attention that [ADR-0000](0000-guiding-principles.md) protects.
