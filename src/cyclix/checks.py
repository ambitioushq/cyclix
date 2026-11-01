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
    """Run every check and return one Result per line that `cyclix check` prints, in order.

    path is the config file, or None when no file was named. cfg is the loaded
    config, or None when loading it raised error.

    The prerequisites that the adapters share run once, after the config check.
    An adapter whose config or prerequisite failed is skipped. Without a config
    the adapters are not known, so the prerequisites of every adapter run.
    """
    if cfg is None:
        failed = {"the config"}
        results = [config_failure(error, path)]
        every = (ClaudeCode, *kinds.TRACKERS.values(), *kinds.CODEHOSTS.values())
        adapters = [(adapter, None) for adapter in every]
    else:
        failed = set()
        results = [Result(f"config for tenant {cfg.tenant.name}")]
        adapters = [
            (ClaudeCode(cfg.agent), cfg.agent),
            (kinds.TRACKERS[cfg.tracker.kind](cfg), cfg.tracker),
            (kinds.CODEHOSTS[cfg.codehost.kind](cfg), cfg.codehost),
        ]

    # dict.fromkeys drops a prerequisite that a second adapter shares, and keeps the order.
    for prerequisite in dict.fromkeys(p for adapter, _ in adapters for p in adapter.needs):
        result = prerequisite.check()
        if result.failure is not None:
            failed.add(prerequisite.name)
        results.append(result)
    results.append(check_state_dir(config.state_dir()))
    for adapter, table in adapters:
        needs = [
            need for need in ("the config", *(p.name for p in adapter.needs)) if need in failed
        ]
        if needs:
            results.append(Result(adapter.readiness_label(table), needs=" and ".join(needs)))
        else:
            results.extend(adapter.readiness(path))
    return results


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
