"""The checks behind `cyclix check`: is a tenant ready to run?

The config and the state directory belong to no adapter, so their checks are
here. Each adapter checks its own outside system.
"""

import tempfile

from cyclix import config
from cyclix.adapters import kinds
from cyclix.adapters.claude_code import ClaudeCode
from cyclix.adapters.readiness import Result


def run(path, cfg, error=None):
    """Run every check, and return one Result for each line that `cyclix check` prints, in order.

    path is the config file, or None when no file was named. cfg is the loaded
    config, or None when loading it raised error.
    """
    if cfg is None:
        return run_without_config(path, error)
    adapters = [
        ClaudeCode(cfg.agent),
        kinds.TRACKERS[cfg.tracker.kind](cfg),
        kinds.CODEHOSTS[cfg.codehost.kind](cfg),
    ]
    shared, failed = run_prerequisites(adapters)
    results = [Result(f"config for tenant {cfg.tenant.name}"), *shared]
    results.append(check_state_dir(config.state_dir()))
    for adapter in adapters:
        missing = [p.name for p in adapter.prerequisites if p.name in failed]
        if missing:
            results.append(skipped(adapter, missing))
        else:
            results.extend(adapter.readiness(path))
    return results


def run_without_config(path, error):
    """The kinds are unknown, so run the prerequisites of every adapter, then skip every adapter."""
    adapters = [ClaudeCode, *kinds.TRACKERS.values(), *kinds.CODEHOSTS.values()]
    shared, failed = run_prerequisites(adapters)
    results = [config_failure(error, path), *shared]
    results.append(check_state_dir(config.state_dir()))
    for adapter in adapters:
        missing = [p.name for p in adapter.prerequisites if p.name in failed]
        results.append(skipped(adapter, ["the config", *missing]))
    return results


def run_prerequisites(adapters):
    """Run each prerequisite of the adapters once. Return the results and the names that failed."""
    results, failed = [], set()
    # dict.fromkeys drops a prerequisite that a second adapter shares, and keeps the order.
    for prerequisite in dict.fromkeys(p for adapter in adapters for p in adapter.prerequisites):
        result = prerequisite.check()
        if result.failure is not None:
            failed.add(prerequisite.name)
        results.append(result)
    return results, failed


def skipped(adapter, missing):
    return Result(adapter.label, needs=" and ".join(missing))


def config_failure(error, path):
    reason = str(error).removeprefix("config: ")
    if path is None:
        fix = "pass --tenant NAME, or set CYCLIX_CONFIG to the config file's path"
    elif not path.exists():
        fix = f"write the tenant config at {path}"
    else:
        fix = f"edit {path}"
    return Result("config", reason, fix)


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
