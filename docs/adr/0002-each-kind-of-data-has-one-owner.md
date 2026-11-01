# ADR-0002: Each kind of data has one owner, and the board wins over the state file

**Status:** Accepted

**Date:** October 2026

## Context

Cyclix reads and writes several kinds of data: the status of a work item, code and pull requests, the loop's own working state, and the history of what happened. A person acts on some of them, usually by moving a card on the board. If two stores each hold a copy of the same fact, they will disagree sooner or later, and the loop has to know which one to believe.

## Decision

Each fact has one owner.

| Fact | Owner |
| --- | --- |
| Work item status, human decisions, comments | The tracker (GitHub Projects), through a tracker adapter |
| Code, branches, PRs, reviews, checks | The code host (GitHub), through a code-host adapter |
| The loop's working state: claims, the phase inside a stage, the checks run on each commit, the spend so far | A local SQLite file, one per install |
| What happened, in order | The event log, which is append-only |

When the SQLite file and the board disagree about a work item, the board is right. At the start of each pass the sweep reads the board and corrects the SQLite file to match.

The SQLite file holds only facts that the tracker has no field for and that no person edits.

Cyclix has its own names for work states: Ready, In progress, In review, Parked, Needs decision and Done. Each tracker adapter maps them to that tracker's fields. Nothing else in the engine names a tracker's own fields.

## Consequences

- A person's move on the board always takes effect. A claim on an item that a person moved out of the engine's hands is released on the next pass.
- The engine never keeps its own copy of a PR's state. It asks the code host each time.
- A second tracker needs only a new adapter and a mapping from the six states.
- If the SQLite file is lost, the loop loses its claims and open runs. The board and the code host still hold the work.

## Alternatives Considered

**A full copy of each work item's state in SQLite, kept in step both ways.** Rejected because people act in the tracker, so a second copy of their decisions would drift.
