"""The fake GitHub world that the fake gh and the fake agent read and write.

A world lives in one directory per scenario:

    world.json         issues, the board, PRs, and whether gh is signed in
    calls.jsonl        one line per fake gh call: {"argv": [...], "exit": n}
    faults.json        faults to inject into fake gh calls
    agent-script.json  one entry per fake agent call
    agent-pids.txt     the process IDs the fake agent ran as or started, one per line
    prompts/<n>.txt    the prompt the fake agent got on call n
    state/             the state directory Cyclix runs against
    remote.git         a bare git repository that stands in for the GitHub remote
    config.toml        the tenant config Cyclix runs with

The fakes find the directory through the environment variable CYCLIX_FAKES_DIR.
"""

import json
import os
import re
import subprocess
from pathlib import Path

ENV = "CYCLIX_FAKES_DIR"
REPO = "o/r"
OWNER = "o"
PROJECT = 1
TENANT = "test"
STATES = [
    "Backlog",
    "Next",
    "Ready",
    "In progress",
    "In review",
    "Parked",
    "Needs decision",
    "Done",
]

AGENT_DEFAULTS = {
    "files": {},
    "commit": False,
    "answer": "",
    "exit": 0,
    "input_tokens": 1000,
    "output_tokens": 200,
    "cost_usd": 0.01,
    "duration_ms": 1000,
    "num_turns": 1,
    "model": "claude-sonnet-5-5",
    "sleep_seconds": 0,
    "stdout": None,
}

CONFIG = f"""\
[tenant]
name = "{TENANT}"

[tracker]
kind = "github"
owner = "{OWNER}"
project = {PROJECT}
status_field = "Status"

[tracker.states]
ready = "Ready"
in_progress = "In progress"
in_review = "In review"
parked = "Parked"
needs_decision = "Needs decision"
done = "Done"

[codehost]
kind = "github"
repo = "{REPO}"
base = "main"

[agent]
command = ["fake-agent"]
model_plan = "claude-opus-5-5"
model_build = "claude-sonnet-5-5"
timeout_minutes = 1

[gate]
commands = [["true"]]

[limits]
runs_per_day = 6
"""


def option_id(name):
    return "opt-" + slug(name)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def git_env():
    """An environment where git ignores the user's own config, so tests behave the same anywhere."""
    return {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }


def git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, env=git_env(), capture_output=True, text=True, check=True
    ).stdout.strip()


class World:
    def __init__(self, root):
        self.root = Path(root)
        self.path = self.root / "world.json"
        self.calls_path = self.root / "calls.jsonl"
        self.faults_path = self.root / "faults.json"
        self.agent_script_path = self.root / "agent-script.json"
        self.prompts_dir = self.root / "prompts"
        self.agent_pids_path = self.root / "agent-pids.txt"
        self.state_dir = self.root / "state"
        self.remote = self.root / "remote.git"
        self.config = self.root / "config.toml"

    @classmethod
    def from_env(cls):
        return cls(os.environ[ENV])

    def create(self):
        """Write an empty world, a test config and a bare remote holding one commit on main."""
        self.state_dir.mkdir(parents=True)
        self.prompts_dir.mkdir()
        self.config.write_text(CONFIG)
        self.save(
            {
                "repo": REPO,
                "issues": [],
                "board": {
                    "number": PROJECT,
                    "owner": OWNER,
                    "id": "PVT_fake1",
                    "title": "Fake board",
                    "status_field": {
                        "id": "PVTSSF_status",
                        "name": "Status",
                        "options": [{"id": option_id(s), "name": s} for s in STATES],
                    },
                    "items": [],
                },
                "prs": [],
            }
        )
        git(self.root, "init", "-q", "--bare", "-b", "main", str(self.remote))
        seed = self.root / "seed"
        git(self.root, "clone", "-q", str(self.remote), str(seed))
        (seed / "README.md").write_text("A test repository.\n")
        git(seed, "add", "README.md")
        git(seed, "commit", "-q", "-m", "Start")
        git(seed, "push", "-q", "origin", "HEAD:main")
        return self

    def load(self):
        return json.loads(self.path.read_text())

    def save(self, data):
        self.path.write_text(json.dumps(data, indent=2) + "\n")

    # Issues and the board

    def add_issue(self, number, title=None, state=None, body=""):
        data = self.load()
        data["issues"].append(
            {
                "number": number,
                "title": title or f"Issue {number}",
                "body": body,
                "state": "OPEN",
                "author": {"login": "maintainer"},
                "labels": [],
            }
        )
        if state is not None:
            data["board"]["items"].append(
                {"id": f"PVTI_{number}", "issue": number, "status": state}
            )
        self.save(data)

    def add_foreign_item(self, repo, number, state):
        """Put an issue of another repository on the board."""
        data = self.load()
        data["board"]["items"].append(
            {"id": f"PVTI_{slug(repo)}_{number}", "issue": number, "repo": repo, "status": state}
        )
        self.save(data)

    def add_draft_item(self, title, state):
        """Put a draft item, which has no issue, on the board."""
        data = self.load()
        items = data["board"]["items"]
        items.append({"id": f"PVTI_draft{len(items)}", "draft": title, "status": state})
        self.save(data)

    def board_state(self, number):
        return self._local_item(number)["status"]

    def remove_option(self, name):
        """Take a Status option off the board."""
        data = self.load()
        field = data["board"]["status_field"]
        field["options"] = [o for o in field["options"] if o["name"] != name]
        self.save(data)

    def item_id(self, number):
        return self._local_item(number)["id"]

    def _local_item(self, number):
        """The board item for an issue of this world's repo."""
        for item in self.load()["board"]["items"]:
            if "draft" not in item and "repo" not in item and item["issue"] == number:
                return item
        raise LookupError(f"#{number} is not on the board")

    # Pull requests

    def add_pr(self, issue, state="OPEN"):
        """Add a PR for an issue on the branch cyclix/<issue>-<slug of its title>."""
        data = self.load()
        title = next(i["title"] for i in data["issues"] if i["number"] == issue)
        number = next_number(data)
        data["prs"].append(
            {
                "number": number,
                "title": title,
                "body": f"Closes #{issue}",
                "head": f"cyclix/{issue}-{slug(title)}",
                "base": "main",
                "state": state,
                "headRefOid": "0" * 40,
                "mergedAt": None,
                "closedAt": None,
            }
        )
        self.save(data)
        return number

    def prs_for(self, issue):
        return [pr for pr in self.load()["prs"] if pr["head"].startswith(f"cyclix/{issue}-")]

    # gh itself

    def set_logged_in(self, logged_in):
        """Whether `gh auth status` reports a signed-in account."""
        data = self.load()
        data["logged_in"] = logged_in
        self.save(data)

    # Calls and faults

    def calls(self):
        if not self.calls_path.exists():
            return []
        return [json.loads(line) for line in self.calls_path.read_text().splitlines()]

    def faults(self):
        if not self.faults_path.exists():
            return []
        return json.loads(self.faults_path.read_text())

    def add_fault(self, command, exit=1, stderr="", stdout="", call=None):
        """Make the given call of a gh command fail. The default is the next call."""
        prefix = command.split()
        if call is None:
            call = 1 + sum(1 for c in self.calls() if c["argv"][: len(prefix)] == prefix)
        faults = self.faults()
        faults.append(
            {"command": command, "call": call, "exit": exit, "stderr": stderr, "stdout": stdout}
        )
        self.faults_path.write_text(json.dumps(faults, indent=2) + "\n")

    # The agent

    def agent_script(self):
        if not self.agent_script_path.exists():
            return []
        return json.loads(self.agent_script_path.read_text())

    def add_agent_step(self, **step):
        unknown = set(step) - set(AGENT_DEFAULTS)
        if unknown:
            raise TypeError(f"unknown agent step keys: {sorted(unknown)}")
        script = self.agent_script()
        script.append({**AGENT_DEFAULTS, **step})
        self.agent_script_path.write_text(json.dumps(script, indent=2) + "\n")

    def record_agent_pid(self, pid):
        with self.agent_pids_path.open("a") as pids:
            pids.write(f"{pid}\n")

    def agent_pids(self):
        """The process IDs of every fake agent call and the processes it started."""
        if not self.agent_pids_path.exists():
            return []
        return [int(line) for line in self.agent_pids_path.read_text().split()]

    def prompts(self):
        return [p.read_text() for p in sorted(self.prompts_dir.glob("*.txt"), key=_call_number)]

    # The event log

    def events(self, tenant=TENANT):
        path = self.state_dir / "events" / f"{tenant}.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines()]


def next_number(data):
    """GitHub numbers issues and PRs from one sequence."""
    numbers = [i["number"] for i in data["issues"]] + [p["number"] for p in data["prs"]]
    return max(numbers, default=0) + 1


def _call_number(path):
    return int(path.stem)
