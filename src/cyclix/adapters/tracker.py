"""The Tracker protocol: the only way the engine reaches work item status and issues.

The tracker owns each item's state. The engine reads it and makes the moves in
workstate.TRANSITIONS, and a human may make any move.
"""

from dataclasses import dataclass
from typing import Protocol

from cyclix.workstate import State


class TrackerError(Exception):
    """The board does not hold what the engine needs, such as an issue or a state's option."""


@dataclass(frozen=True)
class Item:
    """An issue on the board in one of Cyclix's states."""

    issue: int
    title: str
    state: State


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    body: str
    state: str
    author: str
    labels: tuple[str, ...]


class Tracker(Protocol):
    def ready_items(self) -> list[Item]:
        """Items in Ready, oldest issue first."""

    def items(self) -> list[Item]:
        """Every item in a Cyclix state. An item in any other state is left out."""

    def item_state(self, issue: int) -> State | None:
        """The issue's state, or None when it is not on the board or not in a Cyclix state."""

    def set_state(self, issue: int, state: State) -> None:
        """Move the issue's item to the state."""

    def issue(self, issue: int) -> Issue:
        """Read the issue itself."""
