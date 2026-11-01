# ADR-0006: Build the docs site with Astro and Starlight

**Status:** Accepted

**Date:** October 2026

## Context

Cyclix's docs are Markdown files under `docs/`, split by reader: people who run Cyclix, people who work on its code, and the decision records. GitHub shows each file on its own. It gives a reader no navigation across the files, no search, and no way to move between related pages. A docs site built from the same files gives all three.

Cyclix is an engine that operators run, not a library that programmers import, so its docs need no API pages built from docstrings. The files must still read well on GitHub, so they stay plain Markdown with no frontmatter or site-only syntax. The site must rebuild on every merge to `main`, so that it never drifts from the files.

## Decision

We build the docs site with Astro and its docs theme, Starlight. The site lives in `site/` and reads its pages from `docs/`, which stays the only copy of the docs. Each page takes its title from its first heading. The build fails when a link reaches no page or heading. A workflow builds the site on every pull request that touches the docs, and deploys it from `main`.

## Consequences

- A reader of the site gets a sidebar with one group for each kind of reader, and a search over every page.
- Astro builds pages from components as well as from Markdown. That leaves room for interactive pages, such as walkthroughs, next to the Markdown pages.
- Node joins a Python repository. `site/` has a `package.json` and a lockfile, and CI runs npm. The site's packages are tools for the docs and never part of the `cyclix` package.
- Starlight expects each page's title in frontmatter. The site supplies the title from the first heading through its own loader and Markdown plugin in `site/src/`. An Astro or Starlight upgrade can need a change there.
- The site is static, so any static host can serve it.

## Alternatives Considered

**MkDocs.** MkDocs is a Python tool that builds a site from Markdown. It would add no second language to the repository. It takes a page's title from its first heading and turns links between Markdown files into links between pages, so the files would need no adapting. It was not chosen because it builds pages only from Markdown and theme templates, with no component model for interactive pages.

**Sphinx.** Sphinx is a Python tool built around reStructuredText. It reads Markdown through the MyST extension. Its main strength is API reference built from docstrings, which Cyclix does not need.
