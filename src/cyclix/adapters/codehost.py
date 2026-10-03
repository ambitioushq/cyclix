"""The CodeHost protocol: how the engine reaches code, branches and PRs.

The code host owns these facts. The engine never keeps its own copy of a PR's
state; it asks the code host each time.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol


class CodeHostError(Exception):
    """A git or code-host call failed. The message says which call and why."""


@dataclass(frozen=True)
class Worktree:
    issue: int
    branch: str
    path: Path


@dataclass(frozen=True)
class PR:
    number: int
    url: str
    state: str  # "open", "merged" or "closed"


@dataclass(frozen=True)
class PRState:
    number: int
    url: str
    state: str  # "open", "merged" or "closed"
    head_sha: str
    merged_at: datetime | None
    closed_at: datetime | None


class CodeHost(Protocol):
    def ensure_clone(self) -> None: ...
    def new_worktree(self, issue: int, slug: str, run_dir: Path) -> Worktree: ...
    def remove_worktree(self, worktree: Worktree) -> None: ...
    def head_sha(self, worktree: Worktree) -> str: ...
    def push(self, worktree: Worktree) -> None: ...
    def find_pr(self, branch: str) -> PR | None: ...
    def open_pr(self, branch: str, title: str, body: str) -> PR: ...
    def pr_state(self, number: int) -> PRState: ...
