"""The code host on GitHub, through git and gh.

The tenant's repo is cloned once into <state_dir>/repos/<tenant>/. Each run gets
a worktree on the branch cyclix/<issue>-<slug>, made from the remote base after
a fetch. Pushes never force. Every failure is a CodeHostError.
"""

import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from cyclix.adapters import gh
from cyclix.adapters.codehost import PR, CodeHostError, PRState, Worktree

SLUG_LENGTH = 40


def slug(title):
    """The title lower-cased, each run of non-alphanumerics a hyphen, cut to 40 characters."""
    text = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return text[:SLUG_LENGTH].rstrip("-")


def branch_name(issue, slug):
    return f"cyclix/{issue}-{slug}"


def git(cwd, *args):
    """Run git in cwd and return its stdout."""
    done = subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        raise CodeHostError(f"git {args[0]} exited {done.returncode}: {done.stderr.strip()}")
    return done.stdout.strip()


def gh_call(call, *args):
    try:
        return call(*args)
    except gh.GhError as error:
        raise CodeHostError(str(error)) from error


class GitHubCodeHost:
    def __init__(self, config):
        self.repo = config.codehost.repo
        self.base = config.codehost.base
        self.clone = config.state_dir / "repos" / config.tenant.name

    def ensure_clone(self):
        if (self.clone / ".git").exists():
            return
        self.clone.parent.mkdir(parents=True, exist_ok=True)
        gh_call(gh.run, "repo", "clone", self.repo, str(self.clone))

    def new_worktree(self, issue, slug, run_dir):
        self.ensure_clone()
        git(self.clone, "fetch", "-q", "origin")
        branch = branch_name(issue, slug)
        path = Path(run_dir) / "worktree"
        path.parent.mkdir(parents=True, exist_ok=True)
        git(self.clone, "worktree", "add", "-q", "--no-track", "-b", branch, str(path),
            f"origin/{self.base}")  # fmt: skip
        return Worktree(issue=issue, branch=branch, path=path)

    def remove_worktree(self, worktree):
        if worktree.path.exists():
            git(self.clone, "worktree", "remove", "--force", str(worktree.path))
        else:
            git(self.clone, "worktree", "prune")

    def head_sha(self, worktree):
        return git(worktree.path, "rev-parse", "HEAD")

    def push(self, worktree):
        # No --force and no leading "+" on the refspec, so git refuses a push that
        # would drop a commit on the remote branch.
        git(worktree.path, "push", "-q", "--set-upstream", "origin",
            f"{worktree.branch}:{worktree.branch}")  # fmt: skip

    def find_pr(self, branch):
        prs = self._prs(branch)
        return prs[0] if prs else None

    def open_pr(self, branch, title, body):
        """Open a PR, or return the open PR already on this branch.

        A run that crashed after opening its PR finds that PR here, so it never
        opens a second one. A closed or merged PR on the branch is not reused.
        """
        for pr in self._prs(branch):
            if pr.state == "open":
                return pr
        with tempfile.NamedTemporaryFile("w", suffix=".md") as body_file:
            body_file.write(body)
            body_file.flush()
            out = gh_call(
                gh.run,
                "pr", "create", "-R", self.repo, "--head", branch, "--base", self.base,
                "--title", title, "--body-file", body_file.name,
            )  # fmt: skip
        url = out.strip().splitlines()[-1]
        return PR(number=int(url.rstrip("/").rsplit("/", 1)[1]), url=url, state="open")

    def pr_state(self, number):
        fields = "state,mergedAt,closedAt,headRefOid,url"
        pr = gh_call(gh.json, "pr", "view", str(number), "-R", self.repo, "--json", fields)
        return PRState(
            number=number,
            url=pr["url"],
            state=pr["state"].lower(),
            head_sha=pr["headRefOid"],
            merged_at=timestamp(pr["mergedAt"]),
            closed_at=timestamp(pr["closedAt"]),
        )

    def _prs(self, branch):
        """Every PR on the branch, newest first."""
        prs = gh_call(
            gh.json,
            "pr", "list", "-R", self.repo, "--head", branch, "--state", "all",
            "--json", "number,state,url",
        )  # fmt: skip
        prs = sorted(prs, key=lambda pr: -pr["number"])
        return [PR(number=p["number"], url=p["url"], state=p["state"].lower()) for p in prs]


def timestamp(value):
    """gh gives times as ISO 8601 in UTC, and an unset time as null."""
    return datetime.fromisoformat(value) if value else None
