# ADR-0009: Read the tracker with queries that ask for only the fields Cyclix uses

**Status:** Accepted

**Date:** October 2026

## Context

A tracker limits how much one account can read, and everything that uses the account shares the limit. A call that fetches every field of every item is costly. On GitHub the limit is 5,000 API points an hour, and `gh project item-list` and `gh project field-list` cost about 100 points each, even for 25 items. A sweep made several of these calls every 10 minutes and used the whole limit in about 20 minutes.

## Decision

The tracker adapter asks for only the fields it uses, and reads items a page at a time. For GitHub it does this with `gh api graphql`, and a page of 100 items costs 1 point. It makes three reads:

- `BoardFields` reads the project ID and the Status field with its options.
- `BoardItems` reads each item's ID, issue number, title, state, repository and Status, 100 items at a time.
- `BoardItem` reads one item's Status.

One tracker object serves one pass and reads the fields and items once. `item_state` reads its item fresh, because it must see a change made during the pass.

## Consequences

- A pass costs a few points.
- A board renamed, or an item added, during a pass shows up on the next pass.
- `cyclix check` still uses the broad call, because it runs once, on request.
