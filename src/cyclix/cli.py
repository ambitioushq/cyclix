"""The cyclix command: what an operator and systemd run.

Exit codes: 0 success, 1 a check or run failed, 2 bad usage.

check, install and uninstall print their results to stdout. run writes log
records to stderr, and check writes them there too, so they never mix with its
results. This module is the only one that sets up where log records go.
"""

import argparse
import logging
import shutil
import sys
import tempfile
from importlib.metadata import version
from typing import NamedTuple

from cyclix import config, install, runner
from cyclix.adapters import gh

logger = logging.getLogger(__name__)

OK, FAILED, USAGE = 0, 1, 2


def main(argv=None):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit:  # argparse exits 2 on bad usage, 0 after --version
        return exit.code
    if args.command is None:
        parser.print_usage(sys.stderr)
        return USAGE
    return args.handler(args)


def build_parser():
    parser = argparse.ArgumentParser(prog="cyclix")
    parser.add_argument("--version", action="version", version=f"cyclix {version('cyclix')}")
    commands = parser.add_subparsers(dest="command", metavar="command")

    check = commands.add_parser("check", help="check that a tenant is ready to run")
    check.add_argument("--tenant", metavar="NAME")
    check.add_argument("--verbose", action="store_true", help="log each step at DEBUG")
    check.set_defaults(handler=check_command)

    run = commands.add_parser("run", help="make one pass of the loop for a tenant")
    run.add_argument("--tenant", metavar="NAME")
    run.add_argument("--verbose", action="store_true", help="log each step at DEBUG")
    run.set_defaults(handler=run_command)

    install_ = commands.add_parser("install", help="run the loop on a systemd user timer")
    install_.add_argument("--tenant", metavar="NAME", required=True)
    install_.add_argument("--every", metavar="SPAN", default="10min", help="default 10min")
    install_.add_argument("--dry-run", action="store_true", help="print and change nothing")
    install_.add_argument("--force", action="store_true", help="replace units that differ")
    install_.set_defaults(handler=install_command)

    uninstall = commands.add_parser("uninstall", help="stop the timer and remove its units")
    uninstall.add_argument("--tenant", metavar="NAME", required=True)
    uninstall.set_defaults(handler=uninstall_command)
    return parser


def set_up_logging(verbose):
    """Send the cyclix logger's records to stderr, with the level and name at DEBUG."""
    handler = logging.StreamHandler(sys.stderr)
    style = "%(levelname)s %(name)s: %(message)s" if verbose else "%(message)s"
    handler.setFormatter(logging.Formatter(style))
    root = logging.getLogger("cyclix")
    # main can run more than once in one process, as in the tests.
    for old in root.handlers[:]:
        root.removeHandler(old)
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if verbose else logging.INFO)


def run_command(args):
    set_up_logging(args.verbose)
    try:
        cfg = config.load(tenant=args.tenant)
    except config.ConfigError as error:
        logger.error("%s", error)
        return FAILED
    return runner.sweep(cfg)


def install_command(args):
    try:
        install.install(args.tenant, every=args.every, dry_run=args.dry_run, force=args.force)
    except install.InstallError as error:
        print(f"install: {error}", file=sys.stderr)
        return FAILED
    return OK


def uninstall_command(args):
    try:
        install.uninstall(args.tenant)
    except install.InstallError as error:
        print(f"uninstall: {error}", file=sys.stderr)
        return FAILED
    return OK


def check_command(args):
    """Print one line per check, and exit 1 if any fails.

    A pass prints '<what>: ok'. A failure prints 'FAIL: <what>: <reason>', then a
    line on how to fix it. A check that needs one that failed prints
    'skipped: <what>: needs <that check>'.
    """
    set_up_logging(args.verbose)
    results, failed = [], set()
    path = None
    try:
        path = config.find(None, args.tenant)
        logger.debug("read the config at %s", path)
        cfg = config.load(path)
    except config.ConfigError as error:
        cfg = None
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
        results.append(check_agent(cfg.agent.command, path))
    # Reading the board and the branch needs both the config and a signed-in gh.
    if failed:
        board = "board" if cfg is None else f"board {cfg.tracker.owner}/{cfg.tracker.project}"
        protection = "protection of the base branch"
        if cfg is not None:
            protection += f' "{cfg.codehost.base}"'
        results += [skipped(board, failed), skipped(protection, failed)]
    else:
        results.extend(check_board(cfg.tracker, path))
        results.append(check_protection(cfg.codehost))

    for result in results:
        if result.needs:
            print(f"skipped: {result.what}: needs {result.needs}")
        elif result.failure is None:
            print(f"{result.what}: ok")
        else:
            # gh's errors can run over several lines, which would part the fix from its failure.
            print(f"FAIL: {result.what}: {' '.join(result.failure.split())}")
            print(f"  fix: {result.fix}")
    return FAILED if any(r.failure is not None for r in results) else OK


class Result(NamedTuple):
    """What a check looked at; on a failure, the reason and how to fix it."""

    what: str
    failure: str | None = None
    fix: str | None = None
    needs: str | None = None  # the earlier checks that failed, when this one did not run


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


def check_agent(command, path):
    what = f"agent command {command[0]}"
    if shutil.which(command[0]) is None:
        return Result(what, "not on PATH", f"install it, or change [agent] command in {path}")
    return Result(what)


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


def check_board(tracker, path):
    """One result per configured state: is its option on the board's Status field?"""
    board = f"board {tracker.owner}/{tracker.project}"
    try:
        listing = gh.json(
            "project", "field-list", str(tracker.project),
            "--owner", tracker.owner, "--format", "json",
        )  # fmt: skip
    except gh.GhError as error:
        fix = (
            f"check [tracker] owner and project in {path}; "
            'if they are right, run "gh auth refresh -s read:project"'
        )
        return [Result(board, f"cannot read it: {error.stderr}", fix)]
    field = next((f for f in listing["fields"] if f["name"] == tracker.status_field), None)
    if field is None or "options" not in field:
        name = tracker.status_field
        fix = f'add a single-select field "{name}" to the board, '
        fix += f"or change [tracker] status_field in {path}"
        return [Result(board, f'no single-select field "{name}"', fix)]
    options = {option["name"] for option in field["options"]}
    results = []
    for state in config.STATES:
        name = getattr(tracker.states, state)
        what = f'board option "{name}" for {state}'
        if name in options:
            results.append(Result(what))
        else:
            fix = f'add "{name}" to the board\'s {tracker.status_field} field, '
            fix += f"or change [tracker.states] {state} in {path}"
            results.append(Result(what, f"not on the {tracker.status_field} field", fix))
    return results


# What protecting the base branch takes: each rule as a ruleset names it, what the
# branch allows without it, and the rule's name in GitHub's ruleset settings.
PROTECTION_RULES = (
    ("pull_request", "lets a change skip a pull request", "Require a pull request before merging"),
    ("non_fast_forward", "allows force-pushes", "Block force pushes"),
    ("deletion", "allows deletion", "Restrict deletions"),
)


def check_protection(codehost):
    """Does the base branch require a pull request and refuse force-pushes and deletion?

    A rule counts whether it comes from classic branch protection or from a ruleset.
    Reading classic protection needs admin rights, which a narrow token lacks, so a
    ruleset alone is enough when it holds every rule.
    """
    base, repo = codehost.base, codehost.repo
    what = f'protection of the base branch "{base}"'
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
        return Result(what)
    if unreadable:
        # GitHub protects no branch of a private repository on a free plan, so
        # neither a ruleset nor admin rights help there.
        if "make this repository public" in unreadable:
            fix = f"make {repo} public, or move its owner to a paid GitHub plan; "
            fix += f'then add a ruleset for "{base}" in the settings of {repo}'
        else:
            fix = f'protect "{base}" with a ruleset in the settings of {repo}, '
            fix += f"or sign gh in as an admin of {repo}"
        return Result(what, f"cannot read it: {unreadable}", fix)
    gaps = and_list([gap for gap, _ in missing])
    settings = and_list([f'"{setting}"' for _, setting in missing])
    fix = f'in the settings of {repo}, add a ruleset for "{base}" with {settings}'
    return Result(what, gaps, fix)


def and_list(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]
