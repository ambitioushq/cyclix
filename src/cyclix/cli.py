"""The cyclix command: what an operator and systemd run.

Exit codes: 0 success, 1 a check or run failed, 2 bad usage.

check, install and uninstall print their results to stdout. run writes log
records to stderr, and check writes them there too, so they never mix with its
results. This module is the only one that sets up where log records go.
"""

import argparse
import logging
import sys
from importlib.metadata import version

from cyclix import checks, config, install, runner

try:
    import argcomplete
except ImportError:  # the optional extras group is not installed, so there is no completion
    argcomplete = None

logger = logging.getLogger(__name__)

OK, FAILED, USAGE = 0, 1, 2


def main(argv=None):
    parser = build_parser()
    if argcomplete is not None:
        argcomplete.autocomplete(parser)
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
    path = cfg = error = None
    try:
        path = config.find(None, args.tenant)
        logger.debug("read the config at %s", path)
        cfg = config.load(path)
    except config.ConfigError as failure:
        error = failure
    results = checks.run(path, cfg, error)
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
