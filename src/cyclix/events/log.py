"""Writes events to <state_dir>/events/<tenant>.jsonl, one JSON object per line.

Each line goes out in a single write on a file opened with O_APPEND, and is synced
before the call returns, so lines from two processes never interleave and a line
the caller saw written survives a crash.
"""

import json
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path

from cyclix import __version__
from cyclix.events import schema


class EventError(Exception):
    """An event that schema 0 does not allow. Nothing is written."""


def write_stage_run(state_dir: Path, tenant: str, fields: dict[str, object]) -> dict:
    """Write one stage-run event from the fields the state core built up, and return it."""
    for key in fields:
        if key not in schema.STAGE_RUN_KEYS:
            raise EventError(f"event attribute {key} is not in schema {schema.SCHEMA}")
    attributes = {key: fields.get(key) for key in schema.STAGE_RUN_KEYS}
    for key, value in attributes.items():
        if too_long(value):
            raise EventError(f"event attribute {key} is too long")
    if attributes[schema.STAGE] not in schema.STAGES:
        raise EventError(f"event stage {attributes[schema.STAGE]!r} is not a stage")
    if attributes[schema.OUTCOME] not in schema.OUTCOMES:
        raise EventError(f"event outcome {attributes[schema.OUTCOME]!r} is not an outcome")
    if attributes[schema.COST_USD] is not None:
        attributes[schema.COST_USD] = round(attributes[schema.COST_USD], schema.COST_PLACES)
    event = {
        "schema": schema.SCHEMA,
        "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "trace_id": secrets.token_hex(16),
        "span_id": secrets.token_hex(8),
        "body": schema.STAGE_RUN,
        "resource": {"service.name": schema.SERVICE_NAME, "service.version": __version__},
        "attributes": attributes,
    }
    append(Path(state_dir) / "events" / f"{tenant}.jsonl", event)
    return event


def too_long(value):
    """True if the value, or any string inside it, is longer than MAX_STRING."""
    if isinstance(value, str):
        return len(value) > schema.MAX_STRING
    if isinstance(value, dict):
        return any(too_long(v) for v in value.values())
    if isinstance(value, list | tuple):
        return any(too_long(v) for v in value)
    return False


def append(path, event):
    """Append the event as one line, in one write, and sync it to disk."""
    line = (json.dumps(event, ensure_ascii=False) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, line)
        os.fsync(fd)
    finally:
        os.close(fd)
