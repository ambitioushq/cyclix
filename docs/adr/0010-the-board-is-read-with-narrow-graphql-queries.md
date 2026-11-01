# ADR-0010: The board is read with narrow GraphQL queries

**Status:** Accepted

**Date:** October 2026

## Context

An account has 5,000 API points an hour, shared by everything that uses it. `gh project item-list` and `gh project field-list` fetch every field of every item and cost about 100 points each, even for 25 items. A sweep made several such calls every 10 minutes and used the limit in about 20 minutes.

## Decision

The tracker adapter reads the board with `gh api graphql` and asks only for the fields it uses. A page of 100 items costs 1 point.

- `BoardFields` reads the project ID and the Status field with its options.
- `BoardItems` reads each item's ID, issue number, title, state, repository and Status, in pages of 100.
- `BoardItem` reads one item's Status.

One tracker object serves one pass and reads fields and items once. `item_state` reads its item fresh, because it must see a change made during the pass.

## Consequences

- A pass costs a few points.
- A board renamed or an item added during a pass is seen on the next pass.
- `cyclix check` still uses `gh project field-list`, because it runs once, on request.
