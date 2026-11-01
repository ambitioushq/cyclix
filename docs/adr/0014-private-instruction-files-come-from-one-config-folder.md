# ADR-0014: A tenant's private instruction files come from one folder named in its config, copied into each run's worktree

**Status:** Accepted

**Date:** October 2026

## Context

Claude Code reads instruction files such as `CLAUDE.md` from its working folder. Most tenants keep them in the repository. A tenant with a public repository may want its agent's rules kept out of it.

## Decision

`[agent] instructions` names a folder, as an absolute path or a path starting with `~`. Cyclix reads every file under it when it loads the config and hashes them for the event log.

Admission copies each file into the run's worktree at the same relative path, before the plan stage. It copies content, not a link. It adds each path to the worktree's git exclude file, so no commit includes the files.

If the repository tracks a file at one of those paths, admission writes nothing and parks the item, naming the file.

## Consequences

- Each event records `cyclix.agent.instructions.version`, so a run shows which rules its agent was given.
- A change to the folder takes effect on the next run.
- A repository that tracks a file at one of those paths must rename one of them.

## Alternatives Considered

**A symlink to the folder.** Rejected. Claude Code does not read a `CLAUDE.md` symlinked from outside its working folder, and a container could not follow the link.
