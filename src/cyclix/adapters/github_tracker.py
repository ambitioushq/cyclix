"""The tracker on a GitHub Projects board, through the gh CLI.

Make one GitHubTracker per pass. It reads the project ID, the Status field ID and
the option IDs once, on first use, so a board changed during a pass is seen on the next.
"""

from cyclix import config as configlib
from cyclix.adapters import gh
from cyclix.adapters.tracker import Issue, Item, TrackerError
from cyclix.workstate import State

# The --limit of the first item-list call. A larger board is read again with a limit
# that covers it, because gh pages through the board itself up to the limit.
PAGE = 100


class GitHubTracker:
    def __init__(self, config):
        self.tracker = config.tracker
        self.repo = config.codehost.repo
        # Board option name -> Cyclix state. An option not in the map is no state.
        self.states = {getattr(self.tracker.states, key): State(key) for key in configlib.STATES}
        self._board = None

    def ready_items(self):
        return [item for item in self.items() if item.state is State.READY]

    def items(self):
        """Every item of the configured repo in a mapped state, by issue number.

        GitHub numbers a repo's issues in the order they are created, so the
        lowest number is the oldest issue.
        """
        found = []
        for raw in self._list():
            state = self.states.get(raw.get("status"))
            if state is not None and self._is_ours(raw):
                found.append(Item(raw["content"]["number"], raw["content"]["title"], state))
        return sorted(found, key=lambda item: item.issue)

    def item_state(self, issue):
        return next((item.state for item in self.items() if item.issue == issue), None)

    def set_state(self, issue, state):
        board = self.board()
        name = getattr(self.tracker.states, state.value)
        option = board["options"].get(name)
        if option is None:
            raise TrackerError(f'the board has no {self.tracker.status_field} option "{name}"')
        item = next(
            (raw["id"] for raw in self._list() if self._is_ours(raw)
             and raw["content"]["number"] == issue),
            None,
        )  # fmt: skip
        if item is None:
            raise TrackerError(f"#{issue} is not on the board")
        gh.run(
            "project", "item-edit", "--id", item, "--project-id", board["project"],
            "--field-id", board["field"], "--single-select-option-id", option,
        )  # fmt: skip

    def issue(self, issue):
        raw = gh.json(
            "issue", "view", str(issue), "-R", self.repo,
            "--json", "number,title,body,state,author,labels",
        )  # fmt: skip
        return Issue(
            number=raw["number"],
            title=raw["title"],
            body=raw["body"],
            state=raw["state"],
            author=raw["author"]["login"],
            labels=tuple(label["name"] for label in raw["labels"]),
        )

    def comment(self, issue, body):
        gh.run("issue", "comment", str(issue), "-R", self.repo, "--body", body)

    def board(self):
        """The project ID, the Status field ID and its option IDs by name, read once."""
        if self._board is None:
            project = self._project("view")
            fields = self._project("field-list")["fields"]
            name = self.tracker.status_field
            field = next((f for f in fields if f["name"] == name), None)
            if field is None or "options" not in field:
                raise TrackerError(f'the board has no single-select field "{name}"')
            self._board = {
                "project": project["id"],
                "field": field["id"],
                "options": {option["name"]: option["id"] for option in field["options"]},
            }
        return self._board

    def _list(self):
        """Every raw item on the board. A board larger than PAGE is read again in full."""
        limit = PAGE
        while True:
            listing = self._project("item-list", "--limit", str(limit))
            total = listing["totalCount"]
            if len(listing["items"]) >= total or limit >= total:
                return listing["items"]
            limit = total

    def _project(self, command, *args):
        return gh.json(
            "project", command, str(self.tracker.project),
            "--owner", self.tracker.owner, "--format", "json", *args,
        )  # fmt: skip

    def _is_ours(self, raw):
        """An issue of the configured repo, not a draft, a PR or another repo's issue."""
        content = raw.get("content", {})
        return content.get("type") == "Issue" and content.get("repository") == self.repo
