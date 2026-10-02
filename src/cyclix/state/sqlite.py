"""The StateCore on SQLite: <state_dir>/state.db, in WAL mode.

The schema version lives in meta. A file newer than SCHEMA_VERSION is refused.
An older one is brought up by the numbered steps in MIGRATIONS, where step i
takes the file from version i to version i + 1. Every write runs in one
BEGIN IMMEDIATE transaction, so two processes never interleave half a write.
"""

import json
import sqlite3
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from cyclix.state.core import Claim, RunStart, RunState, StateError

BUSY_TIMEOUT_MS = 5000

MIGRATIONS = [
    # 0 -> 1
    """
    CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE claims (
        tenant TEXT NOT NULL,
        issue INTEGER NOT NULL,
        run_id TEXT NOT NULL,
        claimed_at TEXT NOT NULL,
        PRIMARY KEY (tenant, issue)
    );
    CREATE TABLE runs (
        id INTEGER PRIMARY KEY,
        run_id TEXT NOT NULL,
        tenant TEXT NOT NULL,
        issue INTEGER NOT NULL,
        stage TEXT NOT NULL,
        phase TEXT,
        round INTEGER NOT NULL,
        started_at TEXT NOT NULL,
        ended_at TEXT,
        outcome TEXT,
        fields_json TEXT NOT NULL,
        UNIQUE (run_id, stage, round)
    );
    CREATE UNIQUE INDEX runs_one_open ON runs (run_id) WHERE ended_at IS NULL;
    CREATE TABLE checks (
        id INTEGER PRIMARY KEY,
        run_row INTEGER NOT NULL REFERENCES runs (id),
        sha TEXT NOT NULL,
        "check" TEXT NOT NULL,
        passed INTEGER NOT NULL,
        at TEXT NOT NULL
    );
    CREATE TABLE spend (
        tenant TEXT NOT NULL,
        day TEXT NOT NULL,
        usd REAL NOT NULL,
        tokens INTEGER NOT NULL,
        PRIMARY KEY (tenant, day)
    );
    """,
]
SCHEMA_VERSION = len(MIGRATIONS)


def now():
    return datetime.now(UTC)


class SqliteStateCore:
    def __init__(self, state_dir: Path, clock: Callable[[], datetime] = now):
        self.clock = clock
        state_dir = Path(state_dir)
        state_dir.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(
            state_dir / "state.db", timeout=BUSY_TIMEOUT_MS / 1000, autocommit=True
        )
        self.db.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
        self.db.execute("PRAGMA journal_mode = WAL")
        self.db.execute("PRAGMA foreign_keys = ON")
        try:
            self.migrate()
        except BaseException:
            self.db.close()
            raise

    def close(self):
        self.db.close()

    @contextmanager
    def write(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield self.db
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        self.db.execute("COMMIT")

    def version(self):
        has_meta = self.db.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'meta'"
        ).fetchone()
        if not has_meta:
            return 0
        row = self.db.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
        return int(row[0]) if row else 0

    def migrate(self):
        with self.write():
            version = self.version()
            if version > SCHEMA_VERSION:
                raise StateError(
                    f"state.db is schema {version}; this Cyclix reads up to {SCHEMA_VERSION}"
                )
        while version < SCHEMA_VERSION:
            with self.write() as db:
                # Another process may have migrated while this one waited.
                version = self.version()
                if version >= SCHEMA_VERSION:
                    break
                for statement in MIGRATIONS[version].split(";"):
                    if statement.strip():
                        db.execute(statement)
                version += 1
                db.execute(
                    "INSERT OR REPLACE INTO meta VALUES ('schema_version', ?)", (str(version),)
                )

    def stamp(self):
        return self.clock().isoformat()

    # Claims

    def claim(self, tenant, issue, run_id):
        with self.write() as db:
            cursor = db.execute(
                "INSERT OR IGNORE INTO claims VALUES (?, ?, ?, ?)",
                (tenant, issue, run_id, self.stamp()),
            )
            return cursor.rowcount == 1

    def release(self, tenant, issue):
        with self.write() as db:
            db.execute("DELETE FROM claims WHERE tenant = ? AND issue = ?", (tenant, issue))

    def claims(self, tenant):
        rows = self.db.execute(
            "SELECT tenant, issue, run_id, claimed_at FROM claims WHERE tenant = ? ORDER BY issue",
            (tenant,),
        )
        return [
            Claim(tenant=t, issue=i, run_id=r, claimed_at=datetime.fromisoformat(at))
            for t, i, r, at in rows
        ]

    # Runs

    def begin_run(self, run: RunStart):
        fields = {
            "cyclix.tenant": run.tenant,
            "cyclix.issue.id": run.issue,
            "cyclix.run.id": run.run_id,
            "cyclix.stage": run.stage,
            "cyclix.round": run.round,
        }
        try:
            with self.write() as db:
                db.execute(
                    "INSERT INTO runs (run_id, tenant, issue, stage, round, started_at,"
                    " fields_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        run.run_id,
                        run.tenant,
                        run.issue,
                        run.stage,
                        run.round,
                        self.stamp(),
                        json.dumps(fields),
                    ),
                )
        except sqlite3.IntegrityError:
            raise StateError(
                f"run {run.run_id} already has an open stage,"
                f" or already ran {run.stage} round {run.round}"
            ) from None

    def open_row(self, db, run_id):
        row = db.execute(
            "SELECT id, fields_json, started_at FROM runs WHERE run_id = ? AND ended_at IS NULL",
            (run_id,),
        ).fetchone()
        if row is None:
            raise StateError(f"run {run_id} has no open stage")
        return row[0], json.loads(row[1]), row[2]

    def set_phase(self, run_id, phase):
        with self.write() as db:
            row_id, _, _ = self.open_row(db, run_id)
            db.execute("UPDATE runs SET phase = ? WHERE id = ?", (phase, row_id))

    def add_fields(self, run_id, fields):
        with self.write() as db:
            row_id, built, _ = self.open_row(db, run_id)
            built.update(fields)
            db.execute(
                "UPDATE runs SET fields_json = ?, round = ? WHERE id = ?",
                (json.dumps(built), built["cyclix.round"], row_id),
            )

    def end_run(self, run_id, outcome, reason):
        """End the run's open stage and return its event fields, outcome included."""
        with self.write() as db:
            row_id, fields, _ = self.open_row(db, run_id)
            fields["cyclix.outcome"] = outcome
            fields["cyclix.outcome.reason"] = reason
            db.execute(
                "UPDATE runs SET ended_at = ?, outcome = ?, fields_json = ? WHERE id = ?",
                (self.stamp(), outcome, json.dumps(fields), row_id),
            )
        return fields

    def open_runs(self, tenant):
        rows = self.db.execute(
            "SELECT run_id, tenant, issue, stage, phase, round, started_at, fields_json"
            " FROM runs WHERE tenant = ? AND ended_at IS NULL ORDER BY started_at, id",
            (tenant,),
        )
        return [
            RunState(
                run_id=run_id,
                tenant=t,
                issue=issue,
                stage=stage,
                phase=phase,
                round=round_,
                started_at=datetime.fromisoformat(started),
                fields=json.loads(fields),
            )
            for run_id, t, issue, stage, phase, round_, started, fields in rows
        ]

    # Checks

    def record_check(self, run_id, sha, check, passed):
        with self.write() as db:
            row_id, _, _ = self.open_row(db, run_id)
            db.execute(
                'INSERT INTO checks (run_row, sha, "check", passed, at) VALUES (?, ?, ?, ?, ?)',
                (row_id, sha, check, int(passed), self.stamp()),
            )

    def best_verified(self, tenant, issue):
        """The last commit whose checks all passed, in a stage row that ended without crashing.

        A row still open, or ended as crashed, may have stopped partway through
        its checks, so its commits never count.
        """
        row = self.db.execute(
            """
            SELECT checks.sha FROM checks JOIN runs ON runs.id = checks.run_row
            WHERE runs.tenant = ? AND runs.issue = ?
              AND runs.ended_at IS NOT NULL AND runs.outcome != 'crashed'
            GROUP BY checks.run_row, checks.sha
            HAVING MIN(checks.passed) = 1
            ORDER BY MAX(checks.id) DESC
            LIMIT 1
            """,
            (tenant, issue),
        ).fetchone()
        return row[0] if row else None

    # Spend

    def add_spend(self, tenant, usd, tokens):
        """Add to the tenant's spend for today, by the UTC date."""
        with self.write() as db:
            db.execute(
                "INSERT INTO spend VALUES (?, ?, ?, ?) ON CONFLICT (tenant, day)"
                " DO UPDATE SET usd = usd + excluded.usd, tokens = tokens + excluded.tokens",
                (tenant, self.clock().astimezone(UTC).date().isoformat(), usd, tokens),
            )
