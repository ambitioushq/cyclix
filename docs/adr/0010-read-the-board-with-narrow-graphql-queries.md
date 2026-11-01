# ADR-0010: Read the board with narrow GraphQL queries

**Status:** Accepted

**Date:** October 2026

## Context

An account gets 5,000 API points an hour, shared by everything that uses it. `gh project item-list` and `gh project field-list` fetch every field of every item. Each costs about 100 points, even for 25 items. A sweep made several of these calls, every 10 minutes, and used the whole limit in about 20 minutes.

## Decision

The tracker adapter reads the board with `gh api graphql` and asks only for the fields it uses. A page of 100 items costs 1 point.

- `BoardFields` reads the project ID and the Status field with its options.
- `BoardItems` reads each item's ID, issue number, title, state, repository and Status, 100 items at a time.
- `BoardItem` reads one item's Status.

One tracker object serves one pass and reads the fields and items once. `item_state` reads its item fresh, because it must see a change made during the pass.

## Consequences

- A pass costs a few points.
- A board renamed, or an item added, during a pass shows up on the next pass.
- `cyclix check` still uses `gh project field-list`, because it runs once, on request.
