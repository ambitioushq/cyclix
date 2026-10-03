"""The Stage protocol and what the runner hands each stage.

The runner begins and ends each stage's row in the state core and writes its
event. A stage does its work, calls set_phase before any action that changes
the outside world, and returns a StageResult.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from cyclix.adapters.agent import Agent
from cyclix.adapters.codehost import CodeHost, Worktree
from cyclix.adapters.tracker import Issue, Tracker
from cyclix.config import Config
from cyclix.state.core import StateCore
from cyclix.workstate import State

# The outcomes that let the run go on to the next stage.
GO_ON = frozenset({"passed", "skipped"})


@dataclass(frozen=True)
class RunContext:
    config: Config
    state: StateCore
    tracker: Tracker
    codehost: CodeHost
    agent: Agent
    run_id: str
    issue: Issue
    worktree: Worktree
    run_dir: Path
    round: int = 1


@dataclass(frozen=True)
class StageResult:
    """How a stage ended.

    outcome is one of the event schema's outcomes. fields are merged into the
    stage's event. A result that stops the run moves the item to move_to, or to
    Parked when move_to is not set.
    """

    outcome: str
    reason: str = ""
    fields: dict[str, object] = field(default_factory=dict)
    move_to: State | None = None


class Stage(Protocol):
    name: str  # one of the event schema's stages

    def run(self, ctx: RunContext) -> StageResult: ...
