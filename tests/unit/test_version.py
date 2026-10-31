import tomllib
from importlib.metadata import version
from pathlib import Path

from cyclix.cli import main

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def test_version_matches_pyproject(capsys):
    project = tomllib.loads(PYPROJECT.read_text())["project"]
    assert version("cyclix") == project["version"]
    assert main(["--version"]) == 0
    assert capsys.readouterr().out == f"cyclix {project['version']}\n"
