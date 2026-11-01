"""The Readiness protocol: how `cyclix check` asks an adapter whether its outside system is ready."""

from collections.abc import Callable
from typing import ClassVar, NamedTuple, Protocol


class Result(NamedTuple):
    """What a check looked at; on a failure, the reason and how to fix it."""

    what: str
    failure: str | None = None
    fix: str | None = None
    needs: str | None = None  # the earlier checks that failed, when this one did not run


class Prerequisite(NamedTuple):
    """A check that more than one adapter needs. `cyclix check` runs each one once."""

    name: str  # how a skipped check names it, such as "gh signed in"
    check: Callable[[], Result]


class Readiness(Protocol):
    # The shared checks that must pass before readiness can run.
    needs: ClassVar[tuple[Prerequisite, ...]]

    @staticmethod
    def readiness_label(table=None) -> str:
        """What readiness checks, as the line that reports it skipped names it.

        table is the adapter's table of the config, or None when the config did not load.
        """
        ...

    def readiness(self, config_path) -> list[Result]:
        """Check the outside system, with one Result for each thing checked.

        A fix that changes the config names config_path.
        """
        ...
