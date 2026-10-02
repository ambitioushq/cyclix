"""List the scenarios that carry no @issue-<n> tag, and fail if there are any.

A tag on the Feature line counts for every scenario in that file.
Run it as `python tests/tag_check.py [features dir]`.
"""

import re
import sys
from pathlib import Path

FEATURES = Path(__file__).resolve().parent / "features"
TAG = re.compile(r"@issue-\d+\b")
SCENARIO = re.compile(r"\s*(Scenario|Scenario Outline|Scenario Template|Example):\s*(.*)")


def untagged_scenarios(features_dir=FEATURES):
    """Return "<file>: <scenario name>" for each scenario without an issue tag."""
    found = []
    for feature in sorted(Path(features_dir).rglob("*.feature")):
        feature_tagged = False
        tags = []
        for line in feature.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("@"):
                tags.append(stripped)
            elif stripped.startswith("Feature:"):
                feature_tagged = any(TAG.search(t) for t in tags)
                tags = []
            elif match := SCENARIO.match(line):
                if not feature_tagged and not any(TAG.search(t) for t in tags):
                    found.append(f"{feature.name}: {match[2]}")
                tags = []
            elif stripped and not stripped.startswith("#"):
                tags = []
    return found


def main():
    features_dir = sys.argv[1] if len(sys.argv) > 1 else FEATURES
    found = untagged_scenarios(features_dir)
    for entry in found:
        print(f"{entry}: no @issue-<n> tag")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
