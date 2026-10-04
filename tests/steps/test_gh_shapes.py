import json
from pathlib import Path

import record_gh_shapes as recorder
from fakes.runner import run_gh
from pytest_bdd import given, scenarios, then, when

scenarios("gh_shapes.feature")

# What a recording holds besides the command and the gh version.
SHAPE_KEYS = {"keys", "lines"}


@given(
    "the recorded key paths for every gh command Cyclix uses",
    target_fixture="recordings",
)
def recordings():
    found = {path.stem: json.loads(path.read_text()) for path in recorder.SHAPES.glob("*.json")}
    assert set(found) == set(recorder.COMMANDS), "run scripts/record_gh_shapes.py"
    for name, recording in found.items():
        rerun = f"{name} was recorded from another command; run scripts/record_gh_shapes.py"
        assert recording["command"] == recorder.COMMANDS[name], rerun
    return found


@when("the fake gh runs each command", target_fixture="shapes")
def fake_runs_each(world, recordings):
    """Set up the world the way the recorder sets up the sandbox, then run the same commands."""
    title = "Record gh shapes"
    world.add_issue(3, title=title, state="Ready", body="Body", labels=[recorder.LABEL])
    body_file = Path(world.root) / "body.md"
    body_file.write_text("Closes #3\n")
    values = {
        "owner": "o", "project": "1", "repo": "o/r", "base": "main", "issue": 3,
        "title": title, "branch": "cyclix/3-record-gh-shapes", "body_file": str(body_file),
        "field": "Status", "item_id": world.item_id(3), **recorder.QUERIES,
    }  # fmt: skip
    shapes = {}
    for name in recorder.COMMANDS:
        result = run_gh(world, *recorder.fill(recordings[name]["command"], values))
        assert result.returncode == 0, f"{name}: {result.stderr}"
        if name == "pr-create":
            values["pr"] = int(result.stdout.strip().rsplit("/", 1)[1])
        shapes[name] = recorder.shape(name, result.stdout, values)
    return shapes


@then("its key paths match the recording")
def key_paths_match(recordings, shapes):
    for name, shape in shapes.items():
        recorded = {key: value for key, value in recordings[name].items() if key in SHAPE_KEYS}
        assert shape == recorded, name
