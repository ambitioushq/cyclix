"""The Readiness protocol: how `cyclix check` asks an adapter whether its outside system is ready."""

from typing import NamedTuple, Protocol


class Result(NamedTuple):
    """What a check looked at; on a failure, the reason and how to fix it."""

    what: str
    failure: str | None = None
    fix: str | None = None
    needs: str | None = None  # the earlier checks that failed, when this one did not run


class Readiness(Protocol):
    def readiness(self, config_path) -> list[Result]:
        """Check the outside system, with one Result for each thing checked.

        A fix that changes the config names config_path.
        """
        ...
