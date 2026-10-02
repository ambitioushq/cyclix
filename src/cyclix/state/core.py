"""The StateCore protocol: the only way stages and the runner reach the loop's state.

A run is one pass of an issue through the stages. It keeps one run_id, which is
also on the claim and names the run folder. Each stage in the pass gets its own
row, so one run has one row per stage and round, and at most one open row at a
time. set_phase, add_fields, record_check and end_run act on the run's open row.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class StateError(Exception):
    """A state problem: an unreadable state file, or a call the state does not allow."""


@dataclass(frozen=True)
class Claim:
    tenant: str
    issue: int
    run_id: str
    claimed_at: datetime


@dataclass(frozen=True)
class RunStart:
    """What the caller knows when a stage starts. The core stamps the start time."""

    run_id: str
    tenant: str
    issue: int
    stage: str
    round: int = 1


@dataclass(frozen=True)
class RunState:
    """An open stage row, as the sweep reads it back after a crash."""

    run_id: str
    tenant: str
    issue: int
    stage: str
    phase: str | None
    round: int
    started_at: datetime
    fields: dict[str, object]


class StateCore(Protocol):
    def claim(self, tenant: str, issue: int, run_id: str) -> bool: ...
    def release(self, tenant: str, issue: int) -> None: ...
    def claims(self, tenant: str) -> list[Claim]: ...
    def begin_run(self, run: RunStart) -> None: ...
    def set_phase(self, run_id: str, phase: str) -> None: ...
    def add_fields(self, run_id: str, fields: dict[str, object]) -> None: ...
    def end_run(self, run_id: str, outcome: str, reason: str) -> dict: ...
    def open_runs(self, tenant: str) -> list[RunState]: ...
    def record_check(self, run_id: str, sha: str, check: str, passed: bool) -> None: ...
    def best_verified(self, tenant: str, issue: int) -> str | None: ...
    def add_spend(self, tenant: str, usd: float, tokens: int) -> None: ...
