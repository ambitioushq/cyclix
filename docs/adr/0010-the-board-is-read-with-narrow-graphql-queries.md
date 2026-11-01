# ADR-0010: The board is read with narrow GraphQL queries

**Status:** Accepted

**Date:** October 2026

## Context

GitHub gives an account 5,000 points of API rate limit an hour, shared by everything that uses the account. `gh project item-list` and `gh project field-list` fetch every field of every item. Each costs about 100 points, even for a board of 25 items. A sweep made several of these calls, and the timer ran the sweep every 10 minutes, so the limit was used up in about 20 minutes.

## Decision

The tracker adapter reads the board with `gh api graphql` and asks only for the fields it uses. A query for a page of 100 items costs 1 point.

There are three queries, each with an operation name so the fake `gh` can tell them apart:

- `BoardFields` reads the project ID and the Status field with its options.
- `BoardItems` reads each item's ID, issue number, title, state, repository and Status value, in pages of 100.
- `BoardItem` reads one item's Status value.

One tracker object serves one pass. It reads the fields and items once, on first use. The one call that must see a change a person made during the pass, `item_state`, reads that single item fresh.

## Consequences

- A pass costs a few points, and the rate limit stays free for the operator's other uses of the account.
- A board renamed or an item added during a pass is seen on the next pass.
- `cyclix check` still uses `gh project field-list`, because it runs once, on request.
- The shape check records each query's result under its own name. It stores a placeholder for the query text, so a changed query is caught only when the shapes are recorded again.
