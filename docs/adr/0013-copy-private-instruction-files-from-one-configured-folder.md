# ADR-0013: Copy a tenant's private instruction files from one configured folder into each run's worktree

**Status:** Accepted

**Date:** October 2026

## Context

An agent reads instruction files from the folder it works in. Claude Code reads `CLAUDE.md`, for example. Most tenants keep them in the repository. A tenant with a public repository may want its agent's rules kept out of it.

## Decision

`[agent] instructions` names a folder, as an absolute path or a path that starts with `~`. Cyclix reads every file under it when it loads the config, and hashes them for the event log.

Admission copies each file into the run's worktree at the same relative path, before the plan stage. It copies the content, not a link. It adds each path to the worktree's git exclude file, so no commit includes the files.

If the repository already tracks a file at one of those paths, admission writes nothing and parks the item, and the reason names the file.

## Consequences

- Each event records `cyclix.agent.instructions.version`, so you can see which rules the agent had for a run.
- A change in the folder applies from the next run.
- If a repository tracks a file at one of those paths, one of the two must be renamed.

## Alternatives Considered

**A symlink to the folder.** Rejected. Some agents, Claude Code among them, do not read an instruction file that is symlinked from outside the working folder, and a container could not follow the link.
