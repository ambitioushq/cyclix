import subprocess
import sys
from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when

scenarios(str(Path(__file__).parent / "lint.feature"))

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "pyproject.toml"
BIN = Path(sys.executable).parent

# Ten conditions give eleven paths through the function.
ELEVEN_PATHS = (
    "def branchy(x):\n"
    + "".join(f"    if x == {k}:\n        return {k}\n" for k in range(10))
    + "    return -1\n"
)

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


@given("a file holding a function with 11 paths", target_fixture="source")
def eleven_paths(tmp_path):
    (tmp_path / "branchy.py").write_text(ELEVEN_PATHS)
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


@then(parsers.parse('the output names "{text}"'))
def output_names(result, text):
    assert text in result.stdout + result.stderr


@then("both exit 0")
def both_pass(results):
    for result in results:
        assert result.returncode == 0, result.stdout + result.stderr
