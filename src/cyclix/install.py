"""Write and remove the systemd user units that run the loop on a timer.

`cyclix install` writes two units to $XDG_CONFIG_HOME/systemd/user (else
~/.config/systemd/user): a oneshot service that makes one sweep, and a timer
that starts it. Then it reloads systemd and starts the timer. It never
overwrites a unit that differs from what it would write, unless forced.
"""

import difflib
import re
import shutil
import subprocess
import sys
from pathlib import Path

from cyclix import config

TENANT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
# A systemd time span in the units Cyclix accepts, such as "10min" or "1h30min".
TIME_SPAN = re.compile(r"(\d+(s|min|h|d|w))+")


class InstallError(Exception):
    """A reason install or uninstall stopped, worded for the operator."""


def install(tenant, every="10min", dry_run=False, force=False):
    """Write the units and start the timer. Raise InstallError if anything stops it."""
    check_tenant(tenant)
    if not TIME_SPAN.fullmatch(every):
        raise InstallError(f'--every must be a time span such as "10min" or "1h", not "{every}"')
    config_path = config.find(None, tenant).absolute()
    try:
        cfg = config.load(config_path)
    except config.ConfigError as error:
        raise InstallError(str(error)) from None
    if cfg.tenant.name != tenant:
        raise InstallError(
            f'{config_path} is the config for tenant "{cfg.tenant.name}", not "{tenant}"'
        )

    units = {
        service_name(tenant): service_unit(tenant, cyclix_path(), config_path),
        timer_name(tenant): timer_unit(tenant, every),
    }
    commands = [["daemon-reload"], ["enable", "--now", timer_name(tenant)]]
    differences = []
    for name, text in units.items():
        path = units_dir() / name
        if path.exists() and path.read_text() != text:
            differences.append(diff(path, text))

    if dry_run:
        for name, text in units.items():
            print(f"# would write {units_dir() / name}")
            print(text)
        for command in commands:
            print("would run: " + " ".join(["systemctl", "--user", *command]))
    if differences and not force:
        print("".join(differences), end="")
        raise InstallError(
            "a unit differs from the one Cyclix would write: pass --force to replace it"
        )
    if dry_run:
        return

    units_dir().mkdir(parents=True, exist_ok=True)
    for name, text in units.items():
        (units_dir() / name).write_text(text)
        print(f"wrote {units_dir() / name}")
    for command in commands:
        systemctl(*command)


def uninstall(tenant):
    """Stop and disable the timer, then remove both units."""
    check_tenant(tenant)
    timer = units_dir() / timer_name(tenant)
    if timer.exists():
        systemctl("disable", "--now", timer_name(tenant))
    removed = False
    for name in (timer_name(tenant), service_name(tenant)):
        path = units_dir() / name
        if path.exists():
            path.unlink()
            print(f"removed {path}")
            removed = True
    if removed:
        systemctl("daemon-reload")
    else:
        print(f'no units installed for tenant "{tenant}"')


def check_tenant(tenant):
    if not TENANT_NAME.fullmatch(tenant):
        raise InstallError(
            f'"{tenant}" cannot be part of a unit name: use letters, digits, ".", "_" and "-"'
        )


def units_dir():
    return config.config_home() / "systemd" / "user"


def service_name(tenant):
    return f"cyclix-{tenant}.service"


def timer_name(tenant):
    return f"cyclix-{tenant}.timer"


def service_unit(tenant, program, config_path):
    exec_start = " ".join(exec_word(str(w)) for w in [program, "run", "--once", "--tenant", tenant])
    return (
        "[Unit]\n"
        f"Description=Cyclix: one sweep for tenant {tenant}\n"
        "\n"
        "[Service]\n"
        "Type=oneshot\n"
        f"ExecStart={exec_start}\n"
        f"Environment={environment_word(f'CYCLIX_CONFIG={config_path}')}\n"
    )


def timer_unit(tenant, every):
    return (
        "[Unit]\n"
        f"Description=Cyclix: a sweep for tenant {tenant} every {every}\n"
        "\n"
        "[Timer]\n"
        "OnBootSec=2min\n"
        f"OnUnitActiveSec={every}\n"
        "Persistent=true\n"
        "\n"
        "[Install]\n"
        "WantedBy=timers.target\n"
    )


def cyclix_path():
    """The absolute path of the cyclix command running now, else the one on PATH."""
    program = Path(sys.argv[0])
    if program.name == "cyclix":
        return program.absolute()
    found = shutil.which("cyclix")
    if found is None:
        raise InstallError("cannot find the cyclix command on PATH")
    return Path(found).absolute()


# systemd reads "%" as a specifier in every value, and "$" as a variable in ExecStart.
# A word holding a space or a quote is wrapped in double quotes.


def exec_word(word):
    return quote(word.replace("%", "%%").replace("$", "$$"))


def environment_word(word):
    return quote(word.replace("%", "%%"))


def quote(word):
    if not re.search(r'[\s"\'\\]', word):
        return word
    return '"' + word.replace("\\", "\\\\").replace('"', '\\"') + '"'


def diff(path, text):
    return "".join(
        difflib.unified_diff(
            path.read_text().splitlines(keepends=True),
            text.splitlines(keepends=True),
            fromfile=f"{path} (installed)",
            tofile=f"{path} (cyclix)",
        )
    )


def systemctl(*args):
    argv = ["systemctl", "--user", *args]
    try:
        result = subprocess.run(argv, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        raise InstallError("systemctl is not on PATH") from None
    if result.returncode != 0:
        raise InstallError(f"{' '.join(argv)} exited {result.returncode}: {result.stderr.strip()}")
    print(f"ran {' '.join(argv)}")
