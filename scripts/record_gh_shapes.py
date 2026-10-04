"""Record the output shape of each gh command the adapters use, from the sandbox.

Runs each command in COMMANDS against the sandbox repo and board named in
docs/examples/sandbox.toml, the way docs/design/iteration-0.md, "The adapters",
says the adapters call it. Writes tests/fixtures/gh-shapes/<name>.json, holding
the command with placeholders, the gh version, and either the sorted key paths of
its JSON output or, for a command that prints text, its lines with the repo and
numbers masked. The shape scenario runs the fake gh on the same commands and
fails if its output has another shape.

To have something to read, it opens an issue with a label, puts it on the board in
Ready, pushes a branch with one empty commit and opens a PR from it. It closes and
deletes all of these when it ends, even after a failure.

Run it with the sandbox token in GH_TOKEN, or signed in to gh with access to the
sandbox: `uv run python scripts/record_gh_shapes.py`.
"""

import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from cyclix.adapters import github_tracker

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "docs" / "examples" / "sandbox.toml"
SHAPES = ROOT / "tests" / "fixtures" / "gh-shapes"
LABEL = "sandbox"
# Seconds to wait for a new item to show on the board.
BOARD_WAIT = 60

# The query text is not in the recorded command, which holds the placeholder. Only the
# shape of the reply is checked, so re-record after changing a query.
QUERIES = {
    "fields_query": github_tracker.BOARD_FIELDS,
    "items_query": github_tracker.BOARD_ITEMS,
    "item_query": github_tracker.BOARD_ITEM,
}

# In the order they run: pr-list and pr-view read the PR that pr-create opens.
COMMANDS = {
    "graphql-board-fields": [
        "api", "graphql", "-f", "query={fields_query}",
        "-f", "owner={owner}", "-F", "number={project}", "-f", "field={field}",
    ],
    "project-field-list": [
        "project", "field-list", "{project}", "--owner", "{owner}", "--format", "json",
    ],
    "graphql-board-items": [
        "api", "graphql", "-f", "query={items_query}",
        "-f", "owner={owner}", "-F", "number={project}", "-f", "field={field}",
    ],
    "graphql-board-item": [
        "api", "graphql", "-f", "query={item_query}", "-f", "item={item_id}", "-f", "field={field}",
    ],
    "issue-view": [
        "issue", "view", "{issue}", "-R", "{repo}", "--json",
        "number,title,body,state,author,labels",
    ],
    "pr-create": [
        "pr", "create", "-R", "{repo}", "--head", "{branch}", "--base", "{base}",
        "--title", "{title}", "--body-file", "{body_file}",
    ],
    "pr-list": [
        "pr", "list", "-R", "{repo}", "--head", "{branch}", "--state", "all",
        "--json", "number,state,url",
    ],
    "pr-view": [
        "pr", "view", "{pr}", "-R", "{repo}", "--json", "state,mergedAt,closedAt,headRefOid,url",
    ],
}  # fmt: skip

# Commands that print text, not JSON. Their lines are recorded with values masked.
TEXT = {"pr-create"}

# Values masked in text output, so a recording does not depend on the repo or the numbers.
MASKED = ("repo", "pr", "issue")


def key_paths(value, prefix=""):
    """Every key path in a JSON value, sorted. A list's elements share the path `<list>[]`."""
    paths = set()
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            paths.add(path)
            paths.update(key_paths(child, path))
    elif isinstance(value, list):
        for child in value:
            paths.update(key_paths(child, prefix + "[]"))
    return sorted(paths)


def fill(template, values):
    return [part.format(**values) for part in template]


def mask(text, values):
    """The lines of text, with each value in MASKED written as its placeholder."""
    lines = []
    for line in text.splitlines():
        for name in MASKED:
            if name in values:
                line = re.sub(rf"(?<![\w-]){re.escape(str(values[name]))}(?![\w-])",
                              f"{{{name}}}", line)  # fmt: skip
        lines.append(line)
    return lines


def shape(name, output, values):
    """What a recording holds for this command's output."""
    if name in TEXT:
        return {"lines": mask(output, values)}
    return {"keys": key_paths(json.loads(output))}


def gh(*args):
    done = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:2])} exited {done.returncode}: {done.stderr}")
    return done.stdout


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True)


class Sandbox:
    """The sandbox repo and board, and everything made on them, so it can all be removed."""

    def __init__(self, config):
        self.config = config
        self.owner = config.tracker.owner
        self.project = str(config.tracker.project)
        self.repo = config.codehost.repo
        self.base = config.codehost.base
        self.made = []  # (kind, value), undone in reverse order

    @classmethod
    def load(cls):
        from cyclix import config as configlib

        return cls(configlib.load(CONFIG))

    def values(self):
        return {
            "owner": self.owner, "project": self.project, "repo": self.repo, "base": self.base,
            "field": self.config.tracker.status_field, **QUERIES,
        }  # fmt: skip

    def clear(self):
        """Close every open issue and PR and empty the board, left by an earlier run that died.

        The sandbox is throwaway, so this keeps nothing.
        """
        for pr in json.loads(gh("pr", "list", "-R", self.repo, "--json", "number")):
            gh("pr", "close", str(pr["number"]), "-R", self.repo, "--delete-branch")
        for issue in json.loads(gh("issue", "list", "-R", self.repo, "--json", "number")):
            gh("issue", "close", str(issue["number"]), "-R", self.repo)
        for item in self.items():
            self._delete_item(item["id"])

    def new_issue(self, title, body, label=None):
        """Open an issue and put it on the board. Return its number."""
        args = ["issue", "create", "-R", self.repo, "--title", title, "--body", body]
        if label:
            gh("label", "create", label, "-R", self.repo, "--force")
            args += ["--label", label]
        url = gh(*args).strip().splitlines()[-1]
        number = int(url.rsplit("/", 1)[1])
        self.made.append(("issue", number))
        item = json.loads(
            gh("project", "item-add", self.project, "--owner", self.owner, "--url", url,
               "--format", "json")
        )  # fmt: skip
        self.made.append(("item", item["id"]))
        return number

    def set_state(self, issue, name):
        """Move an issue's board item to the Status option with this name."""
        board = github_tracker.GitHubTracker(self.config).board()
        gh("project", "item-edit", "--id", self.item_id(issue), "--project-id", board["project"],
           "--field-id", board["field"], "--single-select-option-id", board["options"][name])  # fmt: skip

    def board_state(self, issue):
        """The Status option name of an issue's board item, or None when it has none."""
        return self._item(issue)["status"]

    def item_id(self, issue):
        return self._item(issue)["id"]

    def items(self):
        """The board's items, read fresh in narrow pages."""
        return github_tracker.GitHubTracker(self.config).board_items()

    def push_branch(self, branch, workdir):
        """Push a branch holding one empty commit on the base."""
        clone = Path(workdir) / "clone"
        gh("repo", "clone", self.repo, str(clone), "--", "-q")
        git(clone, "switch", "-q", "-c", branch)
        git(clone, "-c", "user.name=Cyclix sandbox", "-c", "user.email=sandbox@invalid",
            "commit", "-q", "--allow-empty", "-m", "Record gh shapes")  # fmt: skip
        git(clone, "push", "-q", "origin", branch)
        self.made.append(("branch", branch))

    def open_prs(self, issue):
        """The open PRs on a branch Cyclix made for this issue."""
        prs = json.loads(gh("pr", "list", "-R", self.repo, "--json", "number,headRefName"))
        return [pr for pr in prs if pr["headRefName"].startswith(f"cyclix/{issue}-")]

    def merge(self, number, branch):
        """Squash-merge a PR as a human would, and delete its branch."""
        gh("pr", "merge", str(number), "-R", self.repo, "--squash", "--delete-branch")
        self.made = [
            entry for entry in self.made if entry not in (("pr", number), ("branch", branch))
        ]

    def adopt_pr(self, number, branch):
        """Remove this PR and its branch at the end, like anything else made here."""
        self.made.append(("branch", branch))
        self.made.append(("pr", number))

    def cleanup(self):
        """Close and delete everything made here, newest first. Report what fails, go on."""
        failed = []
        for kind, value in reversed(self.made):
            try:
                if kind == "pr":
                    gh("pr", "close", str(value), "-R", self.repo)
                elif kind == "branch":
                    gh("api", "-X", "DELETE", f"repos/{self.repo}/git/refs/heads/{value}")
                elif kind == "issue":
                    gh("issue", "close", str(value), "-R", self.repo)
                elif kind == "item":
                    self._delete_item(value)
            except RuntimeError as error:
                failed.append(f"{kind} {value}: {error}")
        self.made = []
        for line in failed:
            print(f"cleanup: {line}", file=sys.stderr)

    def _item(self, issue):
        """The board item for an issue. The board shows a new item only after a few seconds."""
        deadline = time.monotonic() + BOARD_WAIT
        while True:
            for item in self.items():
                if item["repository"] == self.repo and item["number"] == issue:
                    return item
            if time.monotonic() > deadline:
                raise LookupError(f"#{issue} is not on the sandbox board")
            time.sleep(3)

    def _delete_item(self, item):
        gh("project", "item-delete", self.project, "--owner", self.owner, "--id", item)


def record(sandbox, workdir):
    """Run each command, and return {name: recording}."""
    values = sandbox.values()
    title = "Record gh shapes"
    values["issue"] = sandbox.new_issue(title, "Opened by scripts/record_gh_shapes.py.", LABEL)
    sandbox.set_state(values["issue"], sandbox.config.tracker.states.ready)
    values["title"] = title
    values["item_id"] = sandbox.item_id(values["issue"])
    values["branch"] = f"cyclix/{values['issue']}-record-gh-shapes"
    sandbox.push_branch(values["branch"], workdir)
    body_file = Path(workdir) / "body.md"
    body_file.write_text(f"Closes #{values['issue']}\n")
    values["body_file"] = str(body_file)

    version = gh("--version").split()[2]
    recordings = {}
    for name, template in COMMANDS.items():
        output = gh(*fill(template, values))
        if name == "pr-create":
            values["pr"] = int(output.strip().splitlines()[-1].rsplit("/", 1)[1])
            sandbox.made.append(("pr", values["pr"]))
        recordings[name] = {"gh": version, "command": template, **shape(name, output, values)}
    return recordings


def main():
    sandbox = Sandbox.load()
    with tempfile.TemporaryDirectory() as workdir:
        try:
            recordings = record(sandbox, workdir)
        finally:
            sandbox.cleanup()
    SHAPES.mkdir(parents=True, exist_ok=True)
    for name, recording in recordings.items():
        (SHAPES / f"{name}.json").write_text(json.dumps(recording, indent=2) + "\n")
        print(f"recorded {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
