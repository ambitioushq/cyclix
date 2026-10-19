"""The Agent protocol: how a stage asks a coding agent to do one piece of work."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AgentResult:
    """One agent call. A failed call has is_error set and says why in reason."""

    answer: str
    is_error: bool
    reason: str
    exit_code: int
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    duration_ms: int
    turns: int


class Agent(Protocol):
    def run(self, prompt, cwd, stage, run_dir) -> AgentResult:
        """Run one prompt in cwd as the given stage. The prompt and answer go in run_dir.

        stage is the stage's config.AgentStage: its model, its caps and its tools.
        """
        ...
