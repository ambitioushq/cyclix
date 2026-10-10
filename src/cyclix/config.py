"""Load and validate a tenant's TOML config.

The file is found in this order: the path given, then CYCLIX_CONFIG, then
<tenant>.toml in the config folder when a tenant name is given. The config folder
is $XDG_CONFIG_HOME/cyclix, else ~/.config/cyclix. Every key is required,
apart from the [limits.wip] table, and an unknown key is an error, so a typo
never passes silently.
"""

import hashlib
import math
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from cyclix.adapters import environment

STATES = ("ready", "in_progress", "in_review", "parked", "needs_decision", "done")
# The states that may carry a WIP limit. The engine adds nothing to Ready, and Done is the end.
WIP_STATES = ("in_progress", "in_review", "parked", "needs_decision")


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
class AgentStage:
    """How the agent runs for one stage: its model, its caps and the tools it may use."""

    model: str
    max_turns: int
    max_budget_usd: float
    tools: tuple[str, ...]


@dataclass(frozen=True)
class Agent:
    command: tuple[str, ...]
    timeout_minutes: int
    # Environment variable names the agent sees beyond the engine's own allow-list.
    pass_env: tuple[str, ...]
    plan: AgentStage
    build: AgentStage


@dataclass(frozen=True)
class Gate:
    commands: tuple[tuple[str, ...], ...]
    pass_env: tuple[str, ...]


@dataclass(frozen=True)
class Limits:
    runs_per_day: int
    # Cyclix state -> the most items it may hold. A state left out has no limit.
    wip: dict[str, int]


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
NAMES = "a list of names, possibly empty"
NUMBER = "a finite number above 0"
COUNT = "a whole number of 1 or more"
AGENT_STAGE = {"model": str, "max_turns": COUNT, "max_budget_usd": NUMBER, "tools": ARGV}
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
    "agent": {
        "command": ARGV,
        "timeout_minutes": COUNT,
        "pass_env": NAMES,
        "plan": AGENT_STAGE,
        "build": AGENT_STAGE,
    },
    "gate": {"commands": ARGV_LIST, "pass_env": NAMES},
    "limits": {"runs_per_day": int},
}
KINDS = {"tracker": "github", "codehost": "github"}
# Flags the engine sets on every agent call, and flags that would widen what the agent
# may do. The agent command may hold none of them, so no config can turn the limits off.
ENGINE_FLAGS = (
    "--model",
    "--permission-mode",
    "--permission-prompts",
    "--dangerously-skip-permissions",
    "--allow-dangerously-skip-permissions",
    "--allowedTools",
    "--allowed-tools",
    "--tools",
    "--restricted",
    "--strict-mcp-config",
    "--mcp-config",
    "--settings",
    "--setting-sources",
    "--add-dir",
    "--max-turns",
    "--max-budget-usd",
)


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

    wip = data.get("limits", {}).pop("wip", {})
    check_table(data, SCHEMA, "")
    check_wip(wip)
    for table, kind in KINDS.items():
        if data[table]["kind"] != kind:
            raise ConfigError(f'[{table}] kind must be "{kind}", not "{data[table]["kind"]}"')
    check_agent_command(data["agent"]["command"])
    check_pass_env(data["agent"]["pass_env"], "agent", CREDENTIALS)
    # The gate gets no Claude login either: it runs the repository's own code.
    check_pass_env(data["gate"]["pass_env"], "gate", (*CREDENTIALS, *environment.CLAUDE_LOGIN))

    tracker = data["tracker"]
    agent = data["agent"]
    gate = data["gate"]
    return Config(
        tenant=Tenant(**data["tenant"]),
        tracker=Tracker(**{**tracker, "states": States(**tracker["states"])}),
        codehost=CodeHost(**data["codehost"]),
        agent=Agent(
            command=tuple(agent["command"]),
            timeout_minutes=agent["timeout_minutes"],
            pass_env=tuple(agent["pass_env"]),
            plan=agent_stage(agent["plan"]),
            build=agent_stage(agent["build"]),
        ),
        gate=Gate(
            commands=tuple(tuple(c) for c in gate["commands"]),
            pass_env=tuple(gate["pass_env"]),
        ),
        limits=Limits(**data["limits"], wip=wip),
        state_dir=state_dir(),
        version="sha256:" + hashlib.sha256(raw).hexdigest(),
    )


def agent_stage(table):
    return AgentStage(
        **{
            **table,
            "max_budget_usd": float(table["max_budget_usd"]),
            "tools": tuple(table["tools"]),
        }
    )


# Names pass_env may not let through. The GitHub tokens and the SSH agent reach
# GitHub; the askpass and SSH programs can hand git a credential; a GIT_CONFIG*
# variable can set a credential helper or undo the engine's own git settings.
CREDENTIALS = (
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "GH_ENTERPRISE_TOKEN",
    "GITHUB_ENTERPRISE_TOKEN",
    "GH_CONFIG_DIR",
    "SSH_AUTH_SOCK",
    "GIT_ASKPASS",
    "SSH_ASKPASS",
    "GIT_SSH",
    "GIT_SSH_COMMAND",
    "GIT_TERMINAL_PROMPT",
)


def check_pass_env(names, table, forbidden):
    for name in names:
        if name in forbidden or name.startswith("GIT_CONFIG"):
            raise ConfigError(
                f'[{table}] "pass_env" must not hold {name}: '
                "the engine keeps credentials and git's config out of the agent and the gate"
            )


def check_agent_command(command):
    for arg in command:
        flag = arg.split("=", 1)[0]
        if flag in ENGINE_FLAGS:
            raise ConfigError(
                f'[agent] "command" must not hold {flag}: '
                "the engine decides the agent's permissions, tools and caps"
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
    elif expected is NAMES:
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ConfigError(f"{label} must be a list of names")
    elif expected is int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ConfigError(f"{label} must be a whole number")
    elif expected is COUNT:
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ConfigError(f"{label} must be a whole number of 1 or more")
    elif expected is NUMBER:
        # TOML allows nan and inf, and nan fails every comparison, so test the range directly.
        if (
            not isinstance(value, int | float)
            or isinstance(value, bool)
            or not 0 < value < math.inf
        ):
            raise ConfigError(f"{label} must be a finite number above 0")
    elif not isinstance(value, expected):
        raise ConfigError(f"{label} must be a string")


def check_wip(wip):
    """The optional [limits.wip] table: a whole number of 1 or more for each limited state."""
    if not isinstance(wip, dict):
        raise ConfigError("limits.wip must be a table")
    for key, value in wip.items():
        if key not in WIP_STATES:
            raise ConfigError(
                f'[limits.wip] cannot limit "{key}": only {", ".join(WIP_STATES)} take a limit'
            )
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ConfigError(f'[limits.wip] "{key}" must be a whole number of 1 or more')
    if wip.get("in_progress", 1) != 1:
        raise ConfigError(
            '[limits.wip] "in_progress" can only be 1 until the engine runs items side by side'
        )


def is_argv(value):
    return isinstance(value, list) and bool(value) and all(isinstance(v, str) for v in value)


def qualify(name, key):
    return f"{name}.{key}" if name else key
