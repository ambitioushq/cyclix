# The docs site

Astro and Starlight build the docs site from the Markdown files in [`docs/`](../docs/README.md). Those files are the only copy of the pages, so edit them there. This folder holds only the site's setup.

To preview the site on your own machine, use the Node version named in `.nvmrc` and run:

```sh
cd site
npm ci
npm run dev
```

The site is served at `http://localhost:4321` and reloads when a file under `docs/` changes. `npm run build` writes the site to `site/dist/` and fails when a link reaches no page or heading.
