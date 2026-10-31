"""One pass of the loop for one tenant.

1. Read the board.
2. Correct the state core to match it. The tracker wins every disagreement.
3. Run the reconciler on every item In review.
4. If no item is In progress, no column is at its WIP limit, and the day's run
   limit is not reached, admit the oldest Ready item and run it through STAGES.
   Stop at the first stage whose outcome is not passed.

A file lock at <state_dir>/<tenant>.lock keeps two passes from overlapping. So a
run still open when a pass holds the lock was left by a pass that died.
"""

import fcntl
import logging
import time
from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime

from cyclix.adapters import gh
from cyclix.adapters.claude_code import ClaudeCode
from cyclix.adapters.codehost import CodeHostError, Worktree
from cyclix.adapters.github_codehost import GitHubCodeHost
from cyclix.adapters.github_tracker import GitHubTracker
from cyclix.adapters.tracker import TrackerError
from cyclix.events import log, schema
from cyclix.events.log import EventError
from cyclix.stages.admission import Admission
from cyclix.stages.base import RunContext, StageResult
from cyclix.stages.build import Build
from cyclix.stages.gate import Gate
from cyclix.stages.plan import Plan
from cyclix.stages.pr import PR
from cyclix.stages.reconciler import Reconciler, ended_pr
from cyclix.state.core import RunStart, StateError
from cyclix.state.sqlite import SqliteStateCore
from cyclix.workstate import IllegalMove, State, Writer, move

logger = logging.getLogger(__name__)

OK, FAILED = 0, 1

# The stages after admission, in order.
STAGES = (Plan(), Build(), Gate(), PR())

# While an item is in one of these states the engine holds it, so its claim stays.
HELD = frozenset({State.IN_PROGRESS, State.IN_REVIEW})

# A failure outside a stage stops the pass. A failure inside a stage fails that stage.
PASS_ERRORS = (gh.GhError, TrackerError, CodeHostError, StateError, EventError, IllegalMove)


def sweep(config):
    """Make one pass. Return 0 when it completes, 1 when it stops on an error."""
    with locked(config) as held:
        if not held:
            logger.info("another pass is running")
            return OK
        state = SqliteStateCore(config.state_dir)
        try:
            Sweep(
                config, state, GitHubTracker(config), GitHubCodeHost(config),
                ClaudeCode(config.agent), STAGES,
            ).run()  # fmt: skip
        except PASS_ERRORS as error:
            logger.error("cyclix run: %s", error)
            return FAILED
        finally:
            state.close()
    return OK


@contextmanager
def locked(config):
    """Yield True while this process holds the tenant's lock, or False if another does."""
    path = config.state_dir / f"{config.tenant.name}.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        yield True  # closing the file releases the lock


class Sweep:
    def __init__(self, config, state, tracker, codehost, agent, stages):
        self.config = config
        self.tenant = config.tenant.name
        self.state = state
        self.tracker = tracker
        self.codehost = codehost
        self.agent = agent
        self.stages = stages

    def run(self):
        items = self.tracker.items()
        logger.debug("the board read returned %d items", len(items))
        # Issue number -> state, oldest issue first. Kept up to date with the pass's own moves.
        board = {item.issue: item.state for item in items}
        self.end_crashed_runs(board)
        self.release_claims(board)
        self.reconcile([item for item in items if board[item.issue] is State.IN_REVIEW], board)
        self.admit_and_run(board)

    # Correcting the state core

    def end_crashed_runs(self, board):
        """End every open run as crashed, and park its item if it is still In progress."""
        for run in self.state.open_runs(self.tenant):
            phase = run.phase or "none"
            reason = f"run crashed in phase {phase}"
            if board.get(run.issue) is State.IN_PROGRESS:
                self.move(run.issue, State.PARKED, reason, Writer.SWEEP)
                board[run.issue] = State.PARKED
            self.end(run.run_id, "crashed", reason)
            logger.debug("ended run %s for #%d as crashed", run.run_id, run.issue)

    def release_claims(self, board):
        """Release each claim whose item a human, or this pass, took out of the engine's hands."""
        for claim in self.state.claims(self.tenant):
            if board.get(claim.issue) not in HELD:
                self.release(claim.issue, claim.run_id)

    # Reconciling

    def reconcile(self, items, board):
        """Carry each item In review to where its PR ended up. An open PR writes no event.

        The reconciler's row goes under the claim's run, or a new run when the item
        has no claim. Either way the claim is released after it, so a reconciler
        that failed tries again on the next pass under a new run.
        """
        claims = {claim.issue: claim.run_id for claim in self.state.claims(self.tenant)}
        for item in items:
            pr = ended_pr(self.codehost, item)
            if pr is None:
                continue
            run_id = claims.get(item.issue) or new_run_id(item.issue)
            if self.run_stage(Reconciler(item, pr), self.context(item.issue, run_id)):
                board[item.issue] = State.DONE if pr.state == "merged" else State.PARKED
            self.release(item.issue, run_id)

    # Running

    def full_column(self, board):
        """Describe the first column at or over its WIP limit, or return None if none is."""
        counts = Counter(board.values())
        for state, limit in self.config.limits.wip.items():
            if counts[State(state)] >= limit:
                option = getattr(self.config.tracker.states, state)
                return f"{option} holds {counts[State(state)]} of its WIP limit of {limit}"
        return None

    def admit_and_run(self, board):
        if State.IN_PROGRESS in board.values():
            return
        if full := self.full_column(board):
            logger.info("admission waits: %s", full)
            return
        limit = self.config.limits.runs_per_day
        if self.state.runs_today(self.tenant) >= limit:
            logger.info("the day's limit of %d runs is reached", limit)
            return
        ready = [issue for issue, state in board.items() if state is State.READY]
        if not ready:
            return
        issue = ready[0]
        run_id = new_run_id(issue)
        if not self.state.claim(self.tenant, issue, run_id):
            return
        logger.debug("admitted #%d as %s", issue, run_id)
        ctx = self.context(issue, run_id)
        for stage in (Admission(), *self.stages):
            if not self.run_stage(stage, ctx):
                return

    def context(self, issue, run_id):
        return RunContext(
            config=self.config, state=self.state, tracker=self.tracker, codehost=self.codehost,
            agent=self.agent, run_id=run_id, number=issue, run_dir=self.run_dir(issue, run_id),
        )  # fmt: skip

    def run_stage(self, stage, ctx):
        """Run one stage as one row in the state core and one event. Return True to go on."""
        issue, run_id, name = ctx.number, ctx.run_id, stage.name
        self.state.begin_run(RunStart(run_id=run_id, tenant=self.tenant, issue=issue, stage=name))
        started = time.monotonic()
        try:
            result = stage.run(ctx)
        except Exception as error:  # noqa: BLE001 - any error in a stage fails that stage
            result = StageResult("failed", f"{name} raised {type(error).__name__}: {error}")
        fields = {
            schema.CONFIG_VERSION: self.config.version,
            schema.INSTRUCTIONS_VERSION: instructions_version(self.config),
            schema.REPOSITORY_URL: f"https://github.com/{self.config.codehost.repo}",
            schema.DURATION_MS: round((time.monotonic() - started) * 1000),
        }
        # The reason can quote the agent, so the log gets no more of it than the event does.
        logger.debug(
            "stage %s for #%d %s after %d ms: %s",
            name, issue, result.outcome, fields[schema.DURATION_MS],
            result.reason[: schema.MAX_STRING],
        )  # fmt: skip
        if ctx.worktree is not None:
            fields[schema.HEAD_NAME] = ctx.worktree.branch
        self.state.add_fields(run_id, {**fields, **result.fields})
        go_on = result.outcome == "passed"
        stopped_to = None
        if not go_on and self.tracker.item_state(issue) is State.IN_PROGRESS:
            stopped_to = result.move_to or State.PARKED
            self.move(issue, stopped_to, result.reason, writer_for(name))
        self.end(run_id, result.outcome, result.reason)
        if stopped_to not in (None, *HELD):
            self.release(issue, run_id)
        return go_on

    # Shared steps

    def move(self, issue, to, reason, writer):
        """Move an item out of In progress, and say why in a comment on the issue."""
        move(self.tracker, issue, State.IN_PROGRESS, to, writer)
        self.tracker.comment(issue, f"{to.label}: {reason}")

    def end(self, run_id, outcome, reason):
        fields = self.state.end_run(run_id, outcome, reason[: schema.MAX_STRING])
        log.write_stage_run(self.config.state_dir, self.tenant, fields)

    def release(self, issue, run_id):
        """Release the claim and remove the run's worktree, if it has one."""
        path = self.run_dir(issue, run_id) / "worktree"
        if path.exists():
            # Removing a worktree needs only its path, so the branch is left empty.
            self.codehost.remove_worktree(Worktree(issue=issue, branch="", path=path))
        self.state.release(self.tenant, issue)
        logger.debug("released the claim on #%d", issue)

    def run_dir(self, issue, run_id):
        return self.config.state_dir / "runs" / self.tenant / str(issue) / run_id


def new_run_id(issue):
    return f"r-{datetime.now(UTC):%Y%m%d-%H%M%S}-{issue}"


def instructions_version(config):
    instructions = config.agent.instructions
    return None if instructions is None else instructions.version


def writer_for(stage):
    """A stage with a writer of its own moves as itself. Build and gate move as any stage."""
    try:
        return Writer(stage)
    except ValueError:
        return Writer.ANY_STATION
