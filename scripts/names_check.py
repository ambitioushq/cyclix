"""Fail if a tracked file or a commit message holds a name from a private list.

The names come from the environment variable CYCLIX_FORBIDDEN_NAMES, one per line.
A match is reported by its position in the list, never by the name, because the
CI log is public.

Exit codes: 0 when clean, 1 on any match, 2 when the list is missing or empty.
"""

import argparse
import os
import re
import subprocess
import sys

VARIABLE = "CYCLIX_FORBIDDEN_NAMES"


def read_names():
    text = os.environ.get(VARIABLE, "")
    return [line.strip() for line in text.splitlines() if line.strip()]


def pattern_for(name):
    """Match the name as whole words, with any run of spaces or hyphens between words."""
    words = re.split(r"[\s-]+", name)
    body = r"[\s-]+".join(re.escape(word) for word in words)
    return re.compile(rf"(?<!\w){body}(?!\w)", re.IGNORECASE)


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, check=True).stdout


def find(patterns, label, text):
    """Print one line per name found on each line of text, and return how many."""
    found = 0
    for line_number, line in enumerate(text.splitlines(), start=1):
        for position, pattern in enumerate(patterns, start=1):
            if pattern.search(line):
                print(f"{label}:{line_number}: forbidden name #{position}")
                found += 1
    return found


def scan_files(patterns):
    found = 0
    for raw in git("ls-files", "-z").split(b"\0"):
        path = raw.decode()
        if not path or not os.path.isfile(path):
            continue
        with open(path, "rb") as file:
            text = file.read().decode("utf-8", errors="replace")
        found += find(patterns, path, text)
    return found


def scan_commits(patterns, commit_range):
    found = 0
    for sha in git("rev-list", commit_range).decode().split():
        short = git("rev-parse", "--short", sha).decode().strip()
        message = git("log", "-1", "--format=%B", sha).decode("utf-8", errors="replace")
        found += find(patterns, short, message)
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--commits", metavar="BASE..HEAD", help="also scan these commit messages")
    args = parser.parse_args()

    names = read_names()
    if not names:
        print(f"{VARIABLE} is missing or empty.", file=sys.stderr)
        return 2

    patterns = [pattern_for(name) for name in names]
    found = scan_files(patterns)
    if args.commits:
        found += scan_commits(patterns, args.commits)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
