# ADR-0014: A tenant's private instruction files come from one folder named in its config, copied into each run's worktree

**Status:** Accepted

**Date:** October 2026

## Context

Claude Code reads instruction files such as `CLAUDE.md` from the folder it works in. Most tenants keep these files in their repository. A tenant with a public repository may not want its agent's rules there, so it needs a place outside the repository that the agent still reads.

## Decision

The optional key `[agent] instructions` names a folder, as an absolute path or a path that starts with `~`. The folder must exist. Cyclix reads every file under it when it loads the config, following symlinks, and hashes them for the event log.

Admission copies each file into the run's worktree at the same relative path, after it makes the worktree and before the plan stage. It copies the file's content, not a link. Admission adds each copied path, anchored at the top of the worktree, to the exclude file the worktree uses (the path `git rev-parse --git-path info/exclude` gives), so no commit includes the files, even after `git add -A`.

When the repository tracks a file at one of those paths, admission writes nothing and parks the item, and the reason names the file. Cyclix never overwrites a tracked file.

## Consequences

- Each stage-run event records `cyclix.agent.instructions.version`, a hash over the folder's files, so a run shows which rules its agent was given.
- A change to a file in the folder takes effect on the next run, with no change to the repository.
- A tenant whose repository already tracks a file at one of those paths must rename one of them.

## Alternatives Considered

**A symlink to the folder.** Rejected because Claude Code does not read a `CLAUDE.md` that is symlinked from outside its working folder, and a container could not follow a link to the host.

**Keeping the files in the repository.** Still the normal choice, and needs no config. It does not suit a tenant that wants its agent's rules kept out of its repository.
