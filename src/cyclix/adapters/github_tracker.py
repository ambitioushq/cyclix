"""The tracker on a GitHub Projects board, through the gh CLI.

Make one GitHubTracker per pass. It reads the project ID, the Status field ID and the
option IDs once, and the board's items once, on first use. A board changed during a pass
is seen on the next, except that item_state reads its one item fresh.

The reads are narrow GraphQL queries through `gh api graphql`. `gh project item-list`
and `gh project field-list` fetch every field of every item, and cost about 100 points
of the hourly GraphQL limit each. A narrow page of 100 items costs 1.
"""

from cyclix import config as configlib
from cyclix.adapters import gh
from cyclix.adapters.tracker import Issue, Item, TrackerError
from cyclix.workstate import State

# Each query has an operation name, so the fake gh can tell them apart. The root works for
# a user or an organization, as `gh project` did.
BOARD_FIELDS = """
query BoardFields($owner: String!, $number: Int!, $field: String!) {
  repositoryOwner(login: $owner) {
    ... on ProjectV2Owner {
      projectV2(number: $number) {
        id
        field(name: $field) { ... on ProjectV2SingleSelectField { id options { id name } } }
      }
    }
  }
}
"""

BOARD_ITEMS = """
query BoardItems($owner: String!, $number: Int!, $field: String!, $after: String) {
  repositoryOwner(login: $owner) {
    ... on ProjectV2Owner {
      projectV2(number: $number) {
        items(first: 100, after: $after) {
          pageInfo { hasNextPage endCursor }
          nodes {
            id
            fieldValueByName(name: $field) {
              ... on ProjectV2ItemFieldSingleSelectValue { name }
            }
            content {
              __typename
              ... on Issue { number title state repository { nameWithOwner } }
            }
          }
        }
      }
    }
  }
}
"""

BOARD_ITEM = """
query BoardItem($item: ID!, $field: String!) {
  node(id: $item) {
    ... on ProjectV2Item {
      fieldValueByName(name: $field) {
        ... on ProjectV2ItemFieldSingleSelectValue { name }
      }
    }
  }
}
"""


class GitHubTracker:
    def __init__(self, config):
        self.tracker = config.tracker
        self.repo = config.codehost.repo
        # Board option name -> Cyclix state. An option not in the map is no state.
        self.states = {getattr(self.tracker.states, key): State(key) for key in configlib.STATES}
        self._board = None
        self._items = None

    def ready_items(self):
        return [item for item in self.items() if item.state is State.READY]

    def items(self):
        """Every item of the configured repo in a mapped state, by issue number.

        GitHub numbers a repo's issues in the order they are created, so the
        lowest number is the oldest issue.
        """
        found = []
        for raw in self.board_items():
            state = self.states.get(raw["status"])
            if state is not None and self._is_ours(raw):
                found.append(Item(raw["number"], raw["title"], state))
        return sorted(found, key=lambda item: item.issue)

    def item_state(self, issue):
        """The state of an issue's item, read fresh, because a human may have moved it."""
        raw = self._find(issue)
        if raw is None:
            return None
        node = self._graphql(BOARD_ITEM, item=raw["id"], field=self.tracker.status_field)["node"]
        if node is None:  # the item was removed from the board
            return None
        return self.states.get(_status(node))

    def set_state(self, issue, state):
        board = self.board()
        name = getattr(self.tracker.states, state.value)
        option = board["options"].get(name)
        if option is None:
            raise TrackerError(f'the board has no {self.tracker.status_field} option "{name}"')
        raw = self._find(issue)
        if raw is None:
            raise TrackerError(f"#{issue} is not on the board")
        gh.run(
            "project", "item-edit", "--id", raw["id"], "--project-id", board["project"],
            "--field-id", board["field"], "--single-select-option-id", option,
        )  # fmt: skip
        raw["status"] = name

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
            project = self._project(BOARD_FIELDS)
            name = self.tracker.status_field
            field = project.get("field")
            if not field or "options" not in field:
                raise TrackerError(f'the board has no single-select field "{name}"')
            self._board = {
                "project": project["id"],
                "field": field["id"],
                "options": {option["name"]: option["id"] for option in field["options"]},
            }
        return self._board

    def board_items(self):
        """Every item on the board as a flat dict, read in pages on first use."""
        if self._items is None:
            items, after = [], None
            while True:
                page = self._project(BOARD_ITEMS, after=after)["items"]
                items += [_flatten(node) for node in page["nodes"] if node is not None]
                if not page["pageInfo"]["hasNextPage"]:
                    break
                after = page["pageInfo"]["endCursor"]
            self._items = items
        return self._items

    def _find(self, issue):
        """The board's raw item for an issue of the configured repo, or None."""
        return next(
            (raw for raw in self.board_items() if self._is_ours(raw) and raw["number"] == issue),
            None,
        )

    def _project(self, query, **variables):
        """The `projectV2` object of a query that starts at the project."""
        data = self._graphql(
            query, owner=self.tracker.owner, number=self.tracker.project,
            field=self.tracker.status_field, **variables,
        )  # fmt: skip
        owner = data["repositoryOwner"]
        project = owner and owner.get("projectV2")
        if project is None:
            raise TrackerError(f"no project {self.tracker.project} for owner {self.tracker.owner}")
        return project

    @staticmethod
    def _graphql(query, **variables):
        """Run a query through gh and return its data. A GraphQL error makes gh exit non-zero."""
        args = ["api", "graphql", "-f", f"query={query}"]
        for name, value in variables.items():
            if value is None:  # an unset variable, such as the first page's cursor
                continue
            flag = "-F" if isinstance(value, int) else "-f"
            args += [flag, f"{name}={value}"]
        return gh.json(*args)["data"]

    def _is_ours(self, raw):
        """An issue of the configured repo, not a draft, a PR or another repo's issue."""
        return raw["type"] == "Issue" and raw["repository"] == self.repo


def _status(node):
    """The Status option name of an item node, or None when it has no value."""
    value = node["fieldValueByName"]
    return value["name"] if value else None


def _flatten(node):
    content = node["content"] or {}
    repository = content.get("repository") or {}
    return {
        "id": node["id"],
        "type": content.get("__typename"),
        "number": content.get("number"),
        "title": content.get("title"),
        "state": content.get("state"),
        "repository": repository.get("nameWithOwner"),
        "status": _status(node),
    }
