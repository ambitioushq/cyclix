"""Load and validate a tenant's TOML config.

The file is found in this order: the path given, then CYCLIX_CONFIG, then
<tenant>.toml in the config folder when a tenant name is given. The config folder
is $XDG_CONFIG_HOME/cyclix, else ~/.config/cyclix. Every key is required,
and an unknown key is an error, so a typo never passes silently.
"""

import hashlib
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

STATES = ("ready", "in_progress", "in_review", "parked", "needs_decision", "done")


class ConfigError(Exception):
    """A config problem, worded for the operator who has to fix the file."""

    def __init__(self, message):
        super().__init__(f"config: {message}")


@dataclass(frozen=True)
class Tenant:
    name: str


@dataclass(frozen=True)
class States:
    """The board's option name for each Cyclix state."""

    ready: str
    in_progress: str
    in_review: str
    parked: str
    needs_decision: str
    done: str


@dataclass(frozen=True)
class Tracker:
    kind: str
    owner: str
    project: int
    status_field: str
    states: States


@dataclass(frozen=True)
class CodeHost:
    kind: str
    repo: str
    base: str


@dataclass(frozen=True)
class Agent:
    command: tuple[str, ...]
    model_plan: str
    model_build: str
    timeout_minutes: int


@dataclass(frozen=True)
class Gate:
    commands: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class Limits:
    runs_per_day: int


@dataclass(frozen=True)
class Config:
    tenant: Tenant
    tracker: Tracker
    codehost: CodeHost
    agent: Agent
    gate: Gate
    limits: Limits
    state_dir: Path
    version: str


# The expected type of each key. A dict is a nested table.
ARGV = "a list of strings"
ARGV_LIST = "a list of commands"
SCHEMA = {
    "tenant": {"name": str},
    "tracker": {
        "kind": str,
        "owner": str,
        "project": int,
        "status_field": str,
        "states": dict.fromkeys(STATES, str),
    },
    "codehost": {"kind": str, "repo": str, "base": str},
    "agent": {"command": ARGV, "model_plan": str, "model_build": str, "timeout_minutes": int},
    "gate": {"commands": ARGV_LIST},
    "limits": {"runs_per_day": int},
}
KINDS = {"tracker": "github", "codehost": "github"}


def load(path=None, tenant=None):
    path = find(path, tenant)
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ConfigError(f"cannot read {path}: {error.strerror}") from None
    try:
        data = tomllib.loads(raw.decode())
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"{path} is not valid TOML: {error}") from None

    check_table(data, SCHEMA, "")
    for table, kind in KINDS.items():
        if data[table]["kind"] != kind:
            raise ConfigError(f'[{table}] kind must be "{kind}", not "{data[table]["kind"]}"')

    tracker = data["tracker"]
    return Config(
        tenant=Tenant(**data["tenant"]),
        tracker=Tracker(**{**tracker, "states": States(**tracker["states"])}),
        codehost=CodeHost(**data["codehost"]),
        agent=Agent(**{**data["agent"], "command": tuple(data["agent"]["command"])}),
        gate=Gate(commands=tuple(tuple(c) for c in data["gate"]["commands"])),
        limits=Limits(**data["limits"]),
        state_dir=state_dir(),
        version="sha256:" + hashlib.sha256(raw).hexdigest(),
    )


def find(path, tenant):
    if path is not None:
        return Path(path)
    if env := os.environ.get("CYCLIX_CONFIG"):
        return Path(env)
    if tenant is not None:
        return config_home() / "cyclix" / f"{tenant}.toml"
    raise ConfigError("no config file given: set CYCLIX_CONFIG or pass --tenant")


def config_home():
    """$XDG_CONFIG_HOME, else ~/.config."""
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def state_dir():
    """CYCLIX_STATE_DIR, else $XDG_STATE_HOME/cyclix, else ~/.local/state/cyclix."""
    if env := os.environ.get("CYCLIX_STATE_DIR"):
        return Path(env)
    if xdg := os.environ.get("XDG_STATE_HOME"):
        return Path(xdg) / "cyclix"
    return Path.home() / ".local" / "state" / "cyclix"


def check_table(data, schema, name):
    """Check one table's keys and value types, naming the key on failure."""
    where = f"[{name}]" if name else "the top level"
    for key in data:
        if key not in schema:
            if isinstance(data[key], dict):
                raise ConfigError(f"unknown table [{qualify(name, key)}]")
            raise ConfigError(f'unknown key "{key}" in {where}')
    for key, expected in schema.items():
        if key not in data:
            if isinstance(expected, dict):
                raise ConfigError(f"missing table [{qualify(name, key)}]")
            raise ConfigError(f'{where} is missing "{key}"')
        value = data[key]
        if isinstance(expected, dict):
            if not isinstance(value, dict):
                raise ConfigError(f"{qualify(name, key)} must be a table")
            check_table(value, expected, qualify(name, key))
        else:
            check_value(value, expected, f'[{name}] "{key}"')


def check_value(value, expected, label):
    if expected is ARGV:
        if not is_argv(value):
            raise ConfigError(f"{label} must be a non-empty list of strings")
    elif expected is ARGV_LIST:
        if not isinstance(value, list) or not value:
            raise ConfigError(f"{label} must list at least one command")
        if not all(is_argv(command) for command in value):
            raise ConfigError(f"{label} must hold commands, each a non-empty list of strings")
    elif expected is int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ConfigError(f"{label} must be a whole number")
    elif not isinstance(value, expected):
        raise ConfigError(f"{label} must be a string")


def is_argv(value):
    return isinstance(value, list) and bool(value) and all(isinstance(v, str) for v in value)


def qualify(name, key):
    return f"{name}.{key}" if name else key
