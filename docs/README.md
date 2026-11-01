# Cyclix documentation

This folder is the source of the Cyclix docs site, built with Astro and Starlight. Read the docs on the site: it has the navigation, the search and the links between pages.

The pages are Markdown files in [`src/content/docs/`](src/content/docs/), one file for each page. A page's path in that folder is its path on the site, so `design/engine.md` is the page `/design/engine/`. Each page names its title in frontmatter, and links to other pages by their site path. GitHub shows each page, but those links work only on the site.

[`examples/`](examples/) holds the example tenant configs that the pages and the README link to.

## Preview the site

Use the Node version named in `.nvmrc`, and run:

```sh
cd docs
npm ci
npm run dev
```

The site is served at `http://localhost:4321` and reloads when a page changes. `npm run build` writes the site to `docs/dist/` and fails when a link reaches no page or heading.
