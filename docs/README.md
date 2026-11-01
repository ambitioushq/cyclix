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

## How the site is deployed

Cloudflare's Git integration for Workers, Workers Builds, builds the site from `main` and deploys it as the Worker `cyclix-docs`, which serves only static files at https://docs.cyclix.dev. [`wrangler.jsonc`](wrangler.jsonc) names the Worker, the built site folder and the custom domain, and turns off the Worker's `workers.dev` address and its per-version preview links, so the site has one address. Cloudflare keeps the build settings in its dashboard, under the Worker's Settings → Build:

- Root directory: `docs`
- Build command: `npm ci && npm run build`
- Deploy command: `npx wrangler deploy`, which runs the Wrangler version in `package-lock.json`
- Build watch paths: include only `docs/*`, so a change elsewhere in the repository starts no build
- Preview builds: off, so a branch other than `main` starts no build

GitHub CI builds the site on every pull request that touches `docs/`, so a broken link fails the pull request before Cloudflare deploys anything. A change to these settings in the dashboard must change this list too.

[ADR-0007](src/content/docs/adr/0007-deploy-the-docs-site-through-the-hosts-git-integration.md) records why the host's Git integration deploys the site, not a CI job. The Cloudflare-specific choices have these reasons:

- The site deploys as a Worker, not as a Pages project. Cloudflare now treats Pages as part of Workers, and Wrangler, Cloudflare's command-line tool, calls Pages "the previous version".
- The Worker serves only the built files and runs no code, because the site is static.
- Wrangler is a development package of the site, so the deploy runs the version pinned in `package-lock.json`, and Dependabot updates it with the site's other packages.
