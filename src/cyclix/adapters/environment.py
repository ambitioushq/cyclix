"""The environment the agent and the gate run with: an allow-list, never the engine's own.

Both run code the engine does not trust, so neither may reach a GitHub credential.
Only the names below pass through, plus the names a tenant lists in pass_env.
git and gh are pointed away from the host user's config, where credentials live,
and git gets the identity it would have used in the worktree through variables
instead, so commits still carry it. The design is in docs/design/isolation.md.
"""

import os
import re
import subprocess
from pathlib import Path

# USER is passed because Claude Code looks its login up in the macOS Keychain by user name.
PASSED = ("PATH", "HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "TERM", "TMPDIR")
# CLAUDE_CONFIG_DIR says where Claude Code keeps its login, when that is not ~/.claude.
CLAUDE_LOGIN = ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY", "CLAUDE_CONFIG_DIR")
GIT_TIMEOUT_SECONDS = 10


def for_agent(pass_env, run_dir, cwd):
    """The agent's environment. It holds the Claude login, which the agent needs."""
    return build((*PASSED, *CLAUDE_LOGIN, *pass_env), run_dir, cwd)


def for_gate(pass_env, run_dir, cwd):
    """The gate's environment. It holds no credential at all."""
    return build((*PASSED, *pass_env), run_dir, cwd)


def build(names, run_dir, cwd):
    env = {name: os.environ[name] for name in names if name in os.environ}
    # An empty folder of its own, so gh finds no login even when the user's has one.
    gh_config = Path(run_dir) / "gh-config"
    gh_config.mkdir(parents=True, exist_ok=True)
    env.update(
        GH_CONFIG_DIR=str(gh_config),
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
        GIT_TERMINAL_PROMPT="0",
    )
    env.update(git_identity(cwd))
    return env


# git var prints an identity as "Name <email> timestamp timezone".
IDENT = re.compile(r"(?P<name>.*) <(?P<email>.*)> \d+ [+-]\d{4}")


def git_identity(cwd):
    """The author and committer git would use in cwd, read before the user's config is hidden.

    git var resolves them as a commit would: the GIT_* variables, the repository's
    own config, author.* and committer.*, user.*, then EMAIL and the system's defaults.
    """
    identity = {}
    for role in ("AUTHOR", "COMMITTER"):
        if found := IDENT.fullmatch(git_var(cwd, f"GIT_{role}_IDENT")):
            identity[f"GIT_{role}_NAME"] = found["name"]
            identity[f"GIT_{role}_EMAIL"] = found["email"]
    return {key: value for key, value in identity.items() if value}


def git_var(cwd, name):
    try:
        done = subprocess.run(
            ["git", "-C", str(cwd), "var", name],
            capture_output=True,
            text=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except OSError, subprocess.TimeoutExpired:
        return ""
    return done.stdout.strip()
