"""The cyclix command: what an operator and systemd run.

Exit codes: 0 success, 1 a check or run failed, 2 bad usage, 3 not built yet.
"""

import argparse
import shutil
import sys
import tempfile

from cyclix import __version__, config, runner
from cyclix.adapters import gh

OK, FAILED, USAGE, NOT_BUILT = 0, 1, 2, 3


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
    parser.add_argument("--version", action="version", version=f"cyclix {__version__}")
    commands = parser.add_subparsers(dest="command", metavar="command")

    check = commands.add_parser("check", help="check that a tenant is ready to run")
    check.add_argument("--tenant", metavar="NAME")
    check.set_defaults(handler=check_command)

    run = commands.add_parser("run", help="run the loop for a tenant")
    run.add_argument("--once", action="store_true", required=True, help="make one sweep")
    run.add_argument("--tenant", metavar="NAME")
    run.set_defaults(handler=run_command)
    return parser


def run_command(args):
    try:
        cfg = config.load(tenant=args.tenant)
    except config.ConfigError as error:
        print(error, file=sys.stderr)
        return FAILED
    return runner.sweep(cfg)


def check_command(args):
    """Print one line per check: '<what>: ok' or 'FAIL: <reason>'. Exit 1 if any fails."""
    results = []
    try:
        cfg = config.load(tenant=args.tenant)
    except config.ConfigError as error:
        cfg = None
        results.append(("config", str(error)))
    else:
        results.append((f"config for tenant {cfg.tenant.name}", None))

    gh_result = check_gh()
    results.append(gh_result)
    results.append(check_state_dir(config.state_dir()))
    if cfg is not None:
        results.append(check_agent(cfg.agent.command))
        if gh_result[1] is None:  # reading the board needs a signed-in gh
            results.extend(check_board(cfg.tracker))

    for what, failure in results:
        print(f"{what}: ok" if failure is None else f"FAIL: {failure}")
    return FAILED if any(failure is not None for _, failure in results) else OK


# Each check returns (what was checked, None) when it passes, else (what, the reason it failed).


def check_gh():
    if shutil.which("gh") is None:
        return "gh", "gh is not on PATH"
    try:
        gh.run("auth", "status")
    except gh.GhError:
        return "gh", "gh is not signed in"
    return "gh is signed in", None


def check_agent(command):
    what = f"agent command {command[0]}"
    if shutil.which(command[0]) is None:
        return what, f'the agent command "{command[0]}" is not on PATH'
    return what, None


def check_state_dir(path):
    what = f"state directory {path}"
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=path):
            pass
    except OSError as error:
        return what, f"the state directory {path} is not writable: {error.strerror}"
    return what, None


def check_board(tracker):
    """One result per configured state: is its option on the board's Status field?"""
    board = f"board {tracker.owner}/{tracker.project}"
    try:
        listing = gh.json(
            "project", "field-list", str(tracker.project),
            "--owner", tracker.owner, "--format", "json",
        )  # fmt: skip
    except gh.GhError as error:
        return [(board, f"cannot read {board}: {error.stderr}")]
    field = next((f for f in listing["fields"] if f["name"] == tracker.status_field), None)
    if field is None or "options" not in field:
        return [(board, f'the board has no single-select field "{tracker.status_field}"')]
    options = {option["name"] for option in field["options"]}
    results = []
    for state in config.STATES:
        name = getattr(tracker.states, state)
        what = f'board option "{name}" for {state}'
        missing = f'the board has no {tracker.status_field} option "{name}"'
        results.append((what, None if name in options else missing))
    return results
