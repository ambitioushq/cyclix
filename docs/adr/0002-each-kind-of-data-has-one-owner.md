# ADR-0002: Each kind of data has one owner

**Status:** Accepted

**Date:** October 2026

## Context

Cyclix handles work item status, code and PRs, its own working state, and a history of events. People change some of these directly, such as by moving a card on the board. When two places hold the same fact, they end up disagreeing.

## Decision

Each fact has one owner, and Cyclix asks the owner.

| Fact | Owner |
| --- | --- |
| Work item status, human decisions, comments | The tracker, through a tracker adapter |
| Code, branches, PRs, reviews, checks | The code host, through a code-host adapter |
| The loop's working state: claims, the phase inside a stage, checks run on each commit, spend | The loop's local store, one for each install |
| What happened, in order | The event log |

If the local store and the tracker disagree about a work item, the tracker is right. The sweep fixes the local store at the start of each pass. The local store holds only what the tracker has no field for and no person edits.

Cyclix has its own names for work states: Ready, In progress, In review, Parked, Needs decision and Done. Each tracker adapter maps them to that tracker's fields.

## Consequences

- A person's move on the board always takes effect.
- The engine keeps no copy of a PR's state. It asks the code host each time.
- A second tracker needs a new adapter and a mapping from the six states.
- If the local store is lost, the loop loses its claims and open runs. The tracker and the code host still hold the work.

## Alternatives Considered

**Keep a full copy of each item's state in the local store and update both.** Rejected. People act in the tracker, so the copy would drift.
