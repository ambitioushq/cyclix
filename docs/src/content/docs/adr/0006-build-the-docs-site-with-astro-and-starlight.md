---
title: "ADR-0006: Build the docs site with Astro and Starlight"
---

**Status:** Accepted. [ADR-0007](/adr/0007-deploy-the-docs-site-through-the-hosts-git-integration/) replaces how the site is deployed.

**Date:** November 2026

## Context

Cyclix's docs are split by reader: people who run Cyclix, people who work on its code, and the decision records. Read as Markdown files on GitHub, they give a reader no navigation, no search and no way to move between related pages. A docs site gives all three.

Cyclix is an engine that operators run, not a library that programmers import, so its docs need no API pages built from docstrings. The docs will change quickly and be read by many people, so the site must stay easy to upgrade, and it must let the docs set their own page order, landing page and layout. The docs must change in the same pull request as the code they describe, and a broken link must fail that pull request.

## Decision

We build the docs site with Astro and its docs theme, Starlight, in Starlight's standard layout and with no custom code. The Starlight project is the `docs/` folder of this repository. The pages are Markdown files in `docs/src/content/docs/`. Each page names its title in frontmatter and links to other pages by their site path. The site is the place to read the docs. GitHub shows each page as its source.

The build fails when a link reaches no page or heading. A workflow builds the site on every pull request that touches the docs, and deploys it from `main`.

## Consequences

- A reader of the site gets a sidebar with one group for each kind of reader, and a search over every page.
- Each page can set its sidebar order and label, a description and a page layout in frontmatter. A page that needs Starlight's components, such as tabs or steps, can be written in MDX.
- Starlight documents and tests this layout, so an upgrade needs no changes to code of our own.
- On GitHub, links between pages do not work, and Starlight's own syntax shows as plain text. A reader on GitHub reads one page at a time.
- Node joins a Python repository. `docs/` has a `package.json` and a lockfile, and CI runs npm. The site's packages are tools for the docs and never part of the `cyclix` package.
- The site is static, so any static host can serve it. A marketing website, if Cyclix gets one, is a separate site.

## Alternatives Considered

**Keep the docs as plain Markdown that reads well on GitHub, and adapt the site to it.** The pages would stay in a top-level `docs/` folder with no frontmatter, and the site would read them from there. Starlight expects frontmatter and its own folder, so the site would need its own loader, a Markdown plugin to turn links between files into links between pages, and settings that point Starlight at the outside folder. An Astro or Starlight upgrade could break any of them. It was not chosen because the site, not GitHub, is where the docs are read.

**MkDocs.** MkDocs is a Python tool that builds a site from Markdown. It would add no second language to the repository. It takes a page's title from its first heading and turns links between Markdown files into links between pages, so the files would read well on GitHub too. It was not chosen because it builds pages only from Markdown and theme templates, with no component model for interactive pages.

**Sphinx.** Sphinx is a Python tool built around reStructuredText. It reads Markdown through the MyST extension. Its main strength is API reference built from docstrings, which Cyclix does not need.
