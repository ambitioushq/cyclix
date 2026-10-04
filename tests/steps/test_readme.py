import re
from pathlib import Path

from pytest_bdd import scenarios, then

scenarios("readme.feature")

README = Path(__file__).resolve().parents[2] / "README.md"


def listed_subcommands(help_text):
    """Names of the indented lines under 'positional arguments:', minus the metavar line."""
    names = []
    in_section = False
    for line in help_text.splitlines():
        if line.startswith("positional arguments:"):
            in_section = True
        elif in_section and line and not line.startswith(" "):
            break
        elif in_section and line.startswith("    ") and not line.startswith("     "):
            names.append(line.split()[0])
    return names


def usage_section(text):
    match = re.search(r"(?ms)^## Usage\s*$(.*?)(?=^## |\Z)", text)
    assert match, "README.md has no '## Usage' section"
    return match.group(1)


@then(
    'each subcommand it lists appears in a "cyclix <subcommand>" example '
    "in the README's Usage section"
)
def readme_has_each_subcommand(result):
    names = listed_subcommands(result.stdout)
    assert names, f"found no subcommands in the help output:\n{result.stdout}"
    usage = usage_section(README.read_text())
    missing = [n for n in names if not re.search(rf"cyclix {re.escape(n)}(?=\s|$)", usage)]
    assert not missing, f"no example in the README's Usage section for: {', '.join(missing)}"
