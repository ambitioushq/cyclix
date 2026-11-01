"""The code host on GitHub, through git and gh.

The tenant's repo is cloned once into <state_dir>/repos/<tenant>/. Each run gets
a worktree on the branch cyclix/<issue>-<slug>, made from the remote base after
a fetch. A later run on the same issue checks out the branch the earlier run left.
Pushes never force. git never prompts, and every git call has a time limit.
Every failure is a CodeHostError.
"""

import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from cyclix.adapters import gh, process
from cyclix.adapters.codehost import PR, CodeHostError, PRState, Worktree
from cyclix.adapters.readiness import Result

SLUG_LENGTH = 40
# Seconds a git call may take. A call that reaches the remote gets longer than one
# that stays in the local repository.
GIT_NETWORK_SECONDS = 300
GIT_LOCAL_SECONDS = 60
NETWORK_COMMANDS = {"clone", "fetch", "pull", "push", "ls-remote"}

# What protecting the base branch takes: each rule as a ruleset names it, what the
# branch allows without it, and the rule's name in GitHub's ruleset settings.
PROTECTION_RULES = (
    ("pull_request", "lets a change skip a pull request", "Require a pull request before merging"),
    ("non_fast_forward", "allows force-pushes", "Block force pushes"),
    ("deletion", "allows deletion", "Restrict deletions"),
)


def slug(title):
    """The title lower-cased, each run of non-alphanumerics a hyphen, cut to 40 characters."""
    text = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return text[:SLUG_LENGTH].rstrip("-")


def branch_name(issue, slug):
    return f"cyclix/{issue}-{slug}"


def git(cwd, *args):
    """Run git in cwd and return its stdout.

    git never asks for a password, so a missing credential fails the call instead
    of waiting on a terminal no one reads.
    """
    timeout = GIT_NETWORK_SECONDS if args[0] in NETWORK_COMMANDS else GIT_LOCAL_SECONDS
    stdout, stderr, code = process.run(
        ["git", "-C", str(cwd), *args], timeout,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )  # fmt: skip
    if code is None:
        raise CodeHostError(f"git {args[0]} gave no answer after {timeout} seconds")
    if code != 0:
        raise CodeHostError(f"git {args[0]} exited {code}: {stderr.strip()}")
    return stdout.strip()


def gh_call(call, *args):
    try:
        return call(*args)
    except gh.GhError as error:
        raise CodeHostError(str(error)) from error


class GitHubCodeHost:
    needs = (gh.SIGNED_IN,)

    def __init__(self, config):
        self.codehost = config.codehost
        self.repo = config.codehost.repo
        self.base = config.codehost.base
        self.clone = config.state_dir / "repos" / config.tenant.name

    def ensure_clone(self):
        if (self.clone / ".git").exists():
            return
        self.clone.parent.mkdir(parents=True, exist_ok=True)
        try:
            gh.run("repo", "clone", self.repo, str(self.clone), timeout=GIT_NETWORK_SECONDS)
        except gh.GhError as error:
            raise CodeHostError(str(error)) from error

    def new_worktree(self, issue, slug, run_dir):
        self.ensure_clone()
        git(self.clone, "fetch", "-q", "origin")
        branch = branch_name(issue, slug)
        path = Path(run_dir) / "worktree"
        path.parent.mkdir(parents=True, exist_ok=True)
        if git(self.clone, "branch", "--list", branch):
            # An earlier run on this issue left its branch, so this run goes on from its commits.
            git(self.clone, "worktree", "add", "-q", str(path), branch)
        else:
            git(self.clone, "worktree", "add", "-q", "--no-track", "-b", branch, str(path),
                f"origin/{self.base}")  # fmt: skip
        return Worktree(issue=issue, branch=branch, path=path)

    def add_local_files(self, worktree, files):
        """Write files into the worktree and keep them out of every commit.

        If the repository tracks any of their paths, write nothing and return those paths.
        """
        paths = [path for path, _ in files]
        listed = git(worktree.path, "ls-files", "-z", "--", *(f":(literal){p}" for p in paths))
        if tracked := sorted(set(listed.split("\0")) & set(paths)):
            return tracked
        # The exclude file is shared by every worktree of the clone, so a path goes in it once.
        exclude = worktree.path / git(worktree.path, "rev-parse", "--git-path", "info/exclude")
        exclude.parent.mkdir(parents=True, exist_ok=True)
        text = exclude.read_text() if exclude.exists() else ""
        new = [p for p in map(exclude_pattern, paths) if p not in text.splitlines()]
        if new:
            with exclude.open("a") as out:
                out.write(
                    ("\n" if text and not text.endswith("\n") else "") + "\n".join(new) + "\n"
                )
        for path, content in files:
            target = worktree.path / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        return []

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

    @staticmethod
    def readiness_label(table=None):
        what = "protection of the base branch"
        return what if table is None else f'{what} "{table.base}"'

    def readiness(self, config_path):
        """Does the base branch require a pull request and refuse force-pushes and deletion?

        A rule counts whether it comes from classic branch protection or from a ruleset.
        Reading classic protection needs admin rights, which a narrow token lacks, so a
        ruleset alone is enough when it holds every rule.
        """
        base, repo = self.base, self.repo
        what = self.readiness_label(self.codehost)
        found, unreadable = set(), None
        try:
            classic = gh.json("api", f"repos/{repo}/branches/{base}/protection")
        except gh.GhError as error:
            if "Branch not protected" not in error.stderr:
                unreadable = error.stderr
        else:
            if "required_pull_request_reviews" in classic:
                found.add("pull_request")
            for rule, key in (
                ("non_fast_forward", "allow_force_pushes"),
                ("deletion", "allow_deletions"),
            ):
                if classic.get(key, {}).get("enabled") is False:
                    found.add(rule)
        try:
            rules = gh.json("api", f"repos/{repo}/rules/branches/{base}")
        except gh.GhError as error:
            unreadable = unreadable or error.stderr
        else:
            found.update(rule.get("type") for rule in rules)

        missing = [(gap, setting) for rule, gap, setting in PROTECTION_RULES if rule not in found]
        if not missing:
            return [Result(what)]
        if unreadable:
            # GitHub protects no branch of a private repository on a free plan, so
            # neither a ruleset nor admin rights help there.
            if "make this repository public" in unreadable:
                fix = f"make {repo} public, or move its owner to a paid GitHub plan; "
                fix += f'then add a ruleset for "{base}" in the settings of {repo}'
            else:
                fix = f'protect "{base}" with a ruleset in the settings of {repo}, '
                fix += f"or sign gh in as an admin of {repo}"
            return [Result(what, f"cannot read it: {unreadable}", fix)]
        gaps = and_list([gap for gap, _ in missing])
        settings = and_list([f'"{setting}"' for _, setting in missing])
        fix = f'in the settings of {repo}, add a ruleset for "{base}" with {settings}'
        return [Result(what, gaps, fix)]

    def _prs(self, branch):
        """Every PR on the branch, newest first."""
        prs = gh_call(
            gh.json,
            "pr", "list", "-R", self.repo, "--head", branch, "--state", "all",
            "--json", "number,state,url",
        )  # fmt: skip
        prs = sorted(prs, key=lambda pr: -pr["number"])
        return [PR(number=p["number"], url=p["url"], state=p["state"].lower()) for p in prs]


def exclude_pattern(path):
    """A git exclude line that matches this one path, from the top of the worktree."""
    pattern = "/" + re.sub(r"[\\*?\[]", lambda match: "\\" + match[0], path)
    # git drops a trailing space from a pattern unless it is escaped.
    return pattern[:-1] + "\\ " if pattern.endswith(" ") else pattern


def timestamp(value):
    """gh gives times as ISO 8601 in UTC, and an unset time as null."""
    return datetime.fromisoformat(value) if value else None


def and_list(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]
