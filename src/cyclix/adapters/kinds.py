"""The kind tables: the adapter class that each `kind` in the config chooses.

The runner and cyclix check build the tracker and the code host only through
these tables, and the config refuses a kind that is not in them.
"""

from cyclix.adapters.github_codehost import GitHubCodeHost
from cyclix.adapters.github_tracker import GitHubTracker

TRACKERS = {"github": GitHubTracker}
CODEHOSTS = {"github": GitHubCodeHost}
