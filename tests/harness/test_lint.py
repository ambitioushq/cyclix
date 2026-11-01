import subprocess
import sys
import tomllib
from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when

scenarios(str(Path(__file__).parent / "lint.feature"))

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "pyproject.toml"
BIN = Path(sys.executable).parent


def returning_ifs(n):
    """A function with n paths and n returns: n - 1 conditions that each return, then a return."""
    body = "".join(f"    if x == {k}:\n        return {k}\n" for k in range(n - 1))
    return f"def branchy(x):\n{body}    return -1\n"


def plain_ifs(n):
    """A function with n branches, none of which returns."""
    body = "".join(f"    if x == {k}:\n        x += {k}\n" for k in range(n))
    return f"def branchy(x):\n{body}    return x\n"


def statements(n):
    """A function with n statements, each an assignment."""
    body = "".join(f"    x = {k}\n" for k in range(n))
    return f"def branchy():\n{body}"


FUNCTIONS = {
    "paths": returning_ifs,
    "returns": returning_ifs,
    "branches": plain_ifs,
    "statements": statements,
}

# Each loop and condition adds one, plus one for each level it is nested in:
# 1 + 2 + 3 + 4 + 1 (elif) + 1 (else) + 1 (while) + 2 (if in while) = 15, and the
# "and" in the last condition adds one more.
TANGLED = """\
def tangled(rows, limit):
    total = 0
    for row in rows:
        if row:
            for cell in row:
                if cell > 0:
                    total += cell
                elif cell < 0:
                    total -= cell
                else:
                    total += 1
    while total > limit:
        if total > 1 and limit > 0:
            total -= limit
    return total
"""


def run(argv, cwd):
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)


@given(parsers.parse("a file holding a function with {count:d} {kind}"), target_fixture="source")
def function_with(tmp_path, count, kind):
    (tmp_path / "branchy.py").write_text(FUNCTIONS[kind](count))
    return tmp_path / "branchy.py"


@given("a file holding a function with a cognitive complexity of 16", target_fixture="source")
def cognitive_sixteen(tmp_path):
    (tmp_path / "tangled.py").write_text(TANGLED)
    return tmp_path / "tangled.py"


@when("ruff checks the file under the project's config", target_fixture="result")
def ruff_checks_file(source):
    return run([BIN / "ruff", "check", "--config", CONFIG, source], source.parent)


@when("complexipy checks the file under the project's config", target_fixture="result")
def complexipy_checks_file(source):
    return run([BIN / "complexipy", "--config", CONFIG, source], source.parent)


@when("ruff and complexipy check the repository", target_fixture="results")
def both_check_repository():
    return [run([BIN / "ruff", "check"], ROOT), run([BIN / "complexipy"], ROOT)]


@when("I read the complexipy config", target_fixture="complexipy_paths")
def complexipy_paths():
    return tomllib.loads(CONFIG.read_text())["tool"]["complexipy"]["paths"]


@then(parsers.parse('the output names "{text}"'))
def output_names(result, text):
    assert text in result.stdout + result.stderr


@then("both exit 0")
def both_pass(results):
    for result in results:
        assert result.returncode == 0, result.stdout + result.stderr


@then(parsers.parse('it names every file in "{folder}"'))
def names_every_file(complexipy_paths, folder):
    # complexipy skips a file with no .py extension when it scans a folder, so each is named.
    files = {path.relative_to(ROOT).as_posix() for path in (ROOT / folder).iterdir()}
    assert files <= set(complexipy_paths), files - set(complexipy_paths)
