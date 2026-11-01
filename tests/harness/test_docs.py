import re
from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when

scenarios(str(Path(__file__).parent / "docs.feature"))

ROOT = Path(__file__).resolve().parents[2]
SITE = "https://docs.cyclix.dev/"
PAGES = Path("docs/src/content/docs")

LINK = re.compile(r"""(?<!!)\[[^\]]*\]\(<?([^)\s>]+)>?(?:\s+(?:"[^"]*"|'[^']*'|\([^)]*\)))?\s*\)""")
REFERENCE = re.compile(r"^ {0,3}\[[^\]]+\]:\s*<?([^\s>]+)>?")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


def prose_lines(path):
    """The lines of a Markdown file outside its fenced code blocks."""
    fence = None
    for line in path.read_text().splitlines():
        match = FENCE.match(line)
        if fence is None:
            if match:
                fence = match[1]
            else:
                yield line
        elif (
            match
            and match[1][0] == fence[0]
            and len(match[1]) >= len(fence)
            and not match[2].strip()
        ):
            # A fence closes only with its own character, at least as long, and nothing after it.
            fence = None


def slug(heading):
    """GitHub's anchor for a heading: lower case, punctuation dropped, spaces as hyphens."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading).replace("`", "")
    return re.sub(r"[^\w\- ]", "", text.lower()).replace(" ", "-")


def anchors(path):
    """Every heading anchor in the file. A repeated heading gets -1, -2 and so on."""
    seen, found = {}, set()
    for line in prose_lines(path):
        if match := HEADING.match(line):
            base = slug(match[1])
            count = seen.get(base, 0)
            seen[base] = count + 1
            found.add(base if count == 0 else f"{base}-{count}")
    return found


def site_page(pages, route):
    """The file in the pages folder for the page at this route, or None when that file builds no page."""
    route = route.partition("?")[0].strip("/")
    if not route:
        return pages / "index.md"
    file = pages / f"{route}.md"
    if not file.exists():
        file = pages / route / "index.md"
    # Starlight builds no page from a file whose name starts with an underscore.
    return None if file.name.startswith("_") else file


def broken_links(files, root):
    """Each relative link, or link to the docs site, whose file or heading does not exist, as text lines."""
    problems = []
    for path in files:
        for line in prose_lines(path):
            for target in [*LINK.findall(line), *REFERENCE.findall(line)]:
                if target.startswith(SITE):
                    route, _, heading = target.removeprefix(SITE).partition("#")
                    linked = site_page(root / PAGES, route)
                elif re.match(r"[a-z][a-z0-9+.-]*:", target):
                    continue  # a URL, not a file in the repository
                elif target.startswith("/"):
                    continue  # a page on the docs site, which the site build checks
                else:
                    name, _, heading = target.partition("#")
                    linked = path if not name else (path.parent / name).resolve()
                shown = path.relative_to(root)
                if linked is None or not linked.exists():
                    problems.append(f"{shown}: {target} does not exist")
                elif heading and (linked.suffix != ".md" or heading not in anchors(linked)):
                    problems.append(f"{shown}: {target} has no such heading")
    return problems


def markdown_files(top):
    skipped = {".git", "node_modules"}
    return sorted(p for p in top.rglob("*.md") if not skipped & set(p.parts))


@given(
    parsers.parse('a docs folder where "{name}" links to "{target}"'),
    target_fixture="docs_folder",
)
def folder_with_link(tmp_path, name, target):
    (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / name).write_text(f"See [it]({target}).\n")
    (tmp_path / "b.md").write_text("# The first part\n\n## The second part\n")
    return tmp_path


@given(
    parsers.parse('a docs folder where "{name}" links to the site page "{target}"'),
    target_fixture="docs_folder",
)
def folder_with_site_link(tmp_path, name, target):
    pages = tmp_path / PAGES
    pages.mkdir(parents=True)
    (pages / "index.md").write_text("---\ntitle: Home\n---\n")
    (pages / "b.md").write_text("# The first part\n\n## The second part\n")
    (pages / "_draft.md").write_text("# A draft\n")
    (tmp_path / name).write_text(f"See [it]({target}).\n")
    return tmp_path


@given(
    parsers.parse('a docs folder where "{name}" shows the link "{target}" in a code block'),
    target_fixture="docs_folder",
)
def folder_with_fenced_link(tmp_path, name, target):
    (tmp_path / name).write_text(f"```\n[it]({target})\n```\n")
    return tmp_path


@given(
    parsers.parse('a docs folder where "{name}" links to "{target}" with a title'),
    target_fixture="docs_folder",
)
def folder_with_titled_link(tmp_path, name, target):
    (tmp_path / name).write_text(f'See [it]({target} "Title").\n')
    return tmp_path


@given(
    parsers.parse(
        'a docs folder where "{name}" links to "{target}" through a reference definition'
    ),
    target_fixture="docs_folder",
)
def folder_with_reference_link(tmp_path, name, target):
    (tmp_path / name).write_text(f"See [it][ref].\n\n[ref]: {target}\n")
    return tmp_path


@given(
    parsers.parse(
        'a docs folder where "{name}" shows the link "{target}" inside a fence example in a longer code block'
    ),
    target_fixture="docs_folder",
)
def folder_with_nested_fence(tmp_path, name, target):
    (tmp_path / name).write_text(f"````\n```\n[it]({target})\n```\n````\n")
    return tmp_path


@when(
    "the links in README.md and under docs/ are checked",
    target_fixture="report",
)
def check_the_repository():
    return broken_links([ROOT / "README.md", *markdown_files(ROOT / "docs")], ROOT)


@when("the links in that folder are checked", target_fixture="report")
def check_the_folder(docs_folder):
    return broken_links(markdown_files(docs_folder), docs_folder)


@then("every relative link reaches a file, and a heading when it names one")
def nothing_is_broken(report):
    assert not report, "\n".join(report)


@then(parsers.parse('the report names "{name}" and "{target}"'))
def report_names(report, name, target):
    assert any(name in line and target in line for line in report), report


@then("the report is empty")
def report_is_empty(report):
    assert report == []
