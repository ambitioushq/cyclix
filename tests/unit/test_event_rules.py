import json
import re
from pathlib import Path

import pytest

from cyclix import __version__
from cyclix.events.log import EventError, write_stage_run
from cyclix.events.schema import MAX_STRING

DESIGN = Path(__file__).resolve().parents[2] / "docs" / "design" / "iteration-0.md"


def fields(**extra):
    base = {
        "cyclix.tenant": "t",
        "cyclix.issue.id": 12,
        "cyclix.run.id": "r1",
        "cyclix.stage": "gate",
        "cyclix.round": 1,
        "cyclix.outcome": "passed",
        "cyclix.outcome.reason": "",
    }
    return base | extra


def lines(state_dir):
    path = state_dir / "events" / "t.jsonl"
    return path.read_text().splitlines() if path.exists() else []


def doc_example():
    """The example event in the design doc's "The event log, schema version 0"."""
    section = DESIGN.read_text().split("## The event log, schema version 0", 1)[1]
    return json.loads(re.search(r"```json\n(.*?)```", section, re.DOTALL)[1])


def test_a_line_has_the_same_keys_as_the_design_doc_example(tmp_path):
    example = doc_example()
    event = write_stage_run(tmp_path, "t", fields())
    assert list(event) == list(example)
    assert list(event["attributes"]) == list(example["attributes"])
    assert list(event["resource"]) == list(example["resource"])


def test_the_written_line_is_the_returned_event(tmp_path):
    event = write_stage_run(tmp_path, "t", fields())
    assert [json.loads(line) for line in lines(tmp_path)] == [event]


def test_ids_timestamp_and_resource_have_the_schema_shapes(tmp_path):
    event = write_stage_run(tmp_path, "t", fields())
    assert re.fullmatch(r"[0-9a-f]{32}", event["trace_id"])
    assert re.fullmatch(r"[0-9a-f]{16}", event["span_id"])
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", event["timestamp"])
    assert event["resource"] == {"service.name": "cyclix", "service.version": __version__}


def test_events_append_and_keep_earlier_lines(tmp_path):
    write_stage_run(tmp_path, "t", fields())
    write_stage_run(tmp_path, "t", fields(**{"cyclix.stage": "pr"}))
    assert [json.loads(line)["attributes"]["cyclix.stage"] for line in lines(tmp_path)] == [
        "gate",
        "pr",
    ]


def test_gate_checks_are_written_as_given(tmp_path):
    checks = [{"name": "tests", "passed": False, "duration_ms": 40112}]
    event = write_stage_run(tmp_path, "t", fields(**{"cyclix.gate.checks": checks}))
    assert event["attributes"]["cyclix.gate.checks"] == checks


def test_a_string_at_the_limit_is_kept(tmp_path):
    write_stage_run(tmp_path, "t", fields(**{"cyclix.outcome.reason": "x" * MAX_STRING}))
    assert len(lines(tmp_path)) == 1


def test_a_long_string_inside_gate_checks_is_refused(tmp_path):
    checks = [{"name": "x" * (MAX_STRING + 1), "passed": True}]
    with pytest.raises(EventError, match="event attribute cyclix.gate.checks is too long"):
        write_stage_run(tmp_path, "t", fields(**{"cyclix.gate.checks": checks}))
    assert lines(tmp_path) == []


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("cyclix.stage", "station", "event stage 'station' is not a stage"),
        ("cyclix.outcome", "ok", "event outcome 'ok' is not an outcome"),
    ],
)
def test_an_unknown_stage_or_outcome_is_refused(tmp_path, key, value, message):
    with pytest.raises(EventError, match=message):
        write_stage_run(tmp_path, "t", fields(**{key: value}))
    assert lines(tmp_path) == []
