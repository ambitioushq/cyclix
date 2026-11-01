# ADR-0001: A PR merges only on a person's approval or under a written rule

**Status:** Accepted

**Date:** October 2026

## Context

The loop writes code unattended, from text that others can influence. A merge puts that code on the base branch. A person's attention is the scarce resource ([ADR-0000](0000-guiding-principles.md)), so routine PRs should not all wait for one.

## Decision

Cyclix merges a PR in two cases only:

1. A designated person has approved it.
2. It belongs to a class that a written rule names, such as a lockfile refresh or a dependency bot's PR, and it meets that rule's conditions, such as CI green and the review approved.

Every other PR waits for a person to merge it. The agent and the gate never merge ([ADR-0013](0013-the-agent-and-the-gate-get-no-github-credential.md)). Only the engine does, and only in these two cases.

## Consequences

- Branch protection on the base branch stays the backstop. `cyclix check` confirms that it requires a pull request and refuses force-pushes and deletion.
- Each merge is recorded with the approval or the rule that allowed it.
- A PR outside every rule waits In review. A limit on In review caps how many wait ([ADR-0008](0008-one-item-in-progress-per-tenant.md)).
- A rule is a way to widen what the loop merges, so a change to a rule is reviewed like a change to code.

## Alternatives Considered

**A person merges every PR.** Rejected as the only path. Routine PRs would use the attention that [ADR-0000](0000-guiding-principles.md) protects.
