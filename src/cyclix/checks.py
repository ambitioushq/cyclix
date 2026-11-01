"""The checks behind `cyclix check`: is a tenant ready to run?"""

import shutil
import tempfile

from cyclix import config
from cyclix.adapters import gh
from cyclix.adapters.claude_code import ClaudeCode
from cyclix.adapters.github_codehost import GitHubCodeHost
from cyclix.adapters.github_tracker import GitHubTracker
from cyclix.adapters.readiness import Result


def run(path, cfg, error=None):
    """Run every check and return one Result per line that `cyclix check` prints, in order.

    path is the config file, or None when no file was named. cfg is the loaded
    config, or None when loading it raised error.
    """
    results, failed = [], set()
    if cfg is None:
        failed.add("the config")
        results.append(config_failure(error, path))
    else:
        results.append(Result(f"config for tenant {cfg.tenant.name}"))

    gh_result = check_gh()
    if gh_result.failure is not None:
        failed.add("gh signed in")
    results.append(gh_result)
    results.append(check_state_dir(config.state_dir()))
    if cfg is None:
        results.append(skipped("agent command", failed & {"the config"}))
    else:
        results.extend(ClaudeCode(cfg.agent).readiness(path))
    # Reading the board and the branch needs both the config and a signed-in gh.
    if failed:
        board = "board" if cfg is None else f"board {cfg.tracker.owner}/{cfg.tracker.project}"
        protection = "protection of the base branch"
        if cfg is not None:
            protection += f' "{cfg.codehost.base}"'
        results += [skipped(board, failed), skipped(protection, failed)]
    else:
        results.extend(GitHubTracker(cfg).readiness(path))
        results.extend(GitHubCodeHost(cfg).readiness(path))
    return results


def skipped(what, failed):
    needs = [need for need in ("the config", "gh signed in") if need in failed]
    return Result(what, needs=" and ".join(needs))


def config_failure(error, path):
    reason = str(error).removeprefix("config: ")
    if path is None:
        fix = "pass --tenant NAME, or set CYCLIX_CONFIG to the config file's path"
    elif not path.exists():
        fix = f"write the tenant config at {path}"
    else:
        fix = f"edit {path}"
    return Result("config", reason, fix)


def check_gh():
    if shutil.which("gh") is None:
        return Result("gh", "not on PATH", "install gh, the GitHub CLI, and put it on PATH")
    try:
        gh.run("auth", "status")
    except gh.GhError:
        return Result("gh", "not signed in", 'run "gh auth login"')
    return Result("gh is signed in")


def check_state_dir(path):
    what = f"state directory {path}"
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=path):
            pass
    except OSError as error:
        fix = f"make {path} writable, or set CYCLIX_STATE_DIR to a directory you can write"
        return Result(what, f"not writable: {error.strerror}", fix)
    return Result(what)
