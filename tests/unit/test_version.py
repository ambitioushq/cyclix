import tomllib
from pathlib import Path

import cyclix

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def test_version_matches_pyproject():
    project = tomllib.loads(PYPROJECT.read_text())["project"]
    assert cyclix.__version__ == project["version"]
