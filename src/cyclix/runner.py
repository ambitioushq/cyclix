"""One pass of the loop for one tenant, as docs/design/iteration-0.md, "The sweep", sets out.

1. Read the board.
2. Correct the state core to match it. The tracker wins every disagreement.
3. Run the reconciler on every item In review. The reconciler comes with #14.
4. If no item is In progress and the day's run limit is not reached, admit the
   oldest Ready item and run it through STAGES. Stop at the first stage whose
   outcome is not passed or skipped.

A file lock at <state_dir>/<tenant>.lock keeps two passes from overlapping. So a
run still open when a pass holds the lock was left by a pass that died.
"""

import fcntl
import functools
import sys
import time
from contextlib import contextmanager
from datetime import UTC, datetime

from cyclix.adapters import gh
from cyclix.adapters.claude_code import ClaudeCode
from cyclix.adapters.codehost import CodeHostError, Worktree
from cyclix.adapters.github_codehost import GitHubCodeHost, slug
from cyclix.adapters.github_tracker import GitHubTracker
from cyclix.adapters.tracker import TrackerError
from cyclix.events import log, schema
from cyclix.events.log import EventError
from cyclix.stages.base import GO_ON, RunContext, StageResult
from cyclix.state.core import RunStart, StateError
from cyclix.state.sqlite import SqliteStateCore
from cyclix.workstate import IllegalMove, State, Writer, move

OK, FAILED = 0, 1

# The stages after admission, in order. #14 adds plan, build, gate, adversarial_review and pr.
STAGES = ()

# While an item is in one of these states the engine holds it, so its claim stays.
HELD = frozenset({State.IN_PROGRESS, State.IN_REVIEW})

# A failure outside a stage stops the pass. A failure inside a stage fails that stage.
PASS_ERRORS = (gh.GhError, TrackerError, CodeHostError, StateError, EventError, IllegalMove)


def sweep(config):
    """Make one pass. Return 0 when it completes, 1 when it stops on an error."""
    with locked(config) as held:
        if not held:
            print("another pass is running")
            return OK
        state = SqliteStateCore(config.state_dir)
        try:
            Sweep(
                config, state, GitHubTracker(config), GitHubCodeHost(config),
                ClaudeCode(config.agent),
            ).run()  # fmt: skip
        except PASS_ERRORS as error:
            print(f"cyclix run: {error}", file=sys.stderr)
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
    def __init__(self, config, state, tracker, codehost, agent):
        self.config = config
        self.tenant = config.tenant.name
        self.state = state
        self.tracker = tracker
        self.codehost = codehost
        self.agent = agent

    def run(self):
        # Issue number -> state, oldest issue first. Kept up to date with the pass's own moves.
        board = {item.issue: item.state for item in self.tracker.items()}
        self.end_crashed_runs(board)
        self.release_claims(board)
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

    def release_claims(self, board):
        """Release each claim whose item a human, or this pass, took out of the engine's hands."""
        for claim in self.state.claims(self.tenant):
            if board.get(claim.issue) not in HELD:
                self.release(claim.issue, claim.run_id)

    # Running

    def admit_and_run(self, board):
        if State.IN_PROGRESS in board.values():
            return
        limit = self.config.limits.runs_per_day
        if self.state.runs_today(self.tenant) >= limit:
            print(f"the day's limit of {limit} runs is reached")
            return
        ready = [issue for issue, state in board.items() if state is State.READY]
        if not ready:
            return
        issue = ready[0]
        run_id = f"r-{datetime.now(UTC):%Y%m%d-%H%M%S}-{issue}"
        if not self.state.claim(self.tenant, issue, run_id):
            return
        admitted = {}

        def admit():
            self.state.set_phase(run_id, "move")
            move(self.tracker, issue, State.READY, State.IN_PROGRESS, Writer.ADMISSION)
            details = self.tracker.issue(issue)
            self.state.set_phase(run_id, "worktree")
            run_dir = self.run_dir(issue, run_id)
            worktree = self.codehost.new_worktree(issue, slug(details.title), run_dir)
            admitted["ctx"] = RunContext(
                config=self.config, state=self.state, tracker=self.tracker,
                codehost=self.codehost, agent=self.agent, run_id=run_id, issue=details,
                worktree=worktree, run_dir=run_dir,
            )  # fmt: skip
            return StageResult("passed", fields={schema.HEAD_NAME: worktree.branch})

        if not self.run_stage(issue, run_id, "admission", admit):
            return
        ctx = admitted["ctx"]
        for stage in STAGES:
            if not self.run_stage(
                issue, run_id, stage.name, functools.partial(stage.run, ctx), ctx
            ):
                return

    def run_stage(self, issue, run_id, name, work, ctx=None):
        """Run one stage as one row in the state core and one event. Return True to go on."""
        self.state.begin_run(RunStart(run_id=run_id, tenant=self.tenant, issue=issue, stage=name))
        started = time.monotonic()
        try:
            result = work()
        except Exception as error:  # noqa: BLE001 - any error in a stage fails that stage
            result = StageResult("failed", f"{name} raised {type(error).__name__}: {error}")
        fields = {
            schema.CONFIG_VERSION: self.config.version,
            schema.DURATION_MS: round((time.monotonic() - started) * 1000),
        }
        if ctx is not None:
            fields[schema.HEAD_NAME] = ctx.worktree.branch
        self.state.add_fields(run_id, {**fields, **result.fields})
        go_on = result.outcome in GO_ON
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

    def run_dir(self, issue, run_id):
        return self.config.state_dir / "runs" / self.tenant / str(issue) / run_id


def writer_for(stage):
    """A stage with a writer of its own moves as itself. Build, gate and review move as any stage."""
    try:
        return Writer(stage)
    except ValueError:
        return Writer.ANY_STATION
