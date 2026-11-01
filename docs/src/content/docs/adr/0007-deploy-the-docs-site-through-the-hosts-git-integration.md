---
title: "ADR-0007: Deploy the docs site through the host's Git integration"
---

**Status:** Accepted

**Date:** November 2026

## Context

[ADR-0006](/adr/0006-build-the-docs-site-with-astro-and-starlight/) has a CI workflow build the docs site on every pull request and deploy it from `main`. To deploy, the workflow holds the docs host's API token as a repository secret. The host also offers a Git integration: it watches the repository, builds the site from `main` and deploys it. The host's deploy tool had also started to send its older static-site commands to a newer product, so the workflow's deploy command could no longer create the site.

## Decision

The host's Git integration builds the site from `main` and deploys it. CI builds the site on every pull request that touches the docs, so a broken link fails the pull request. The repository holds the host's standard config file, which names the site and its built folder. The host's deploy tool is a pinned development package of the site. The build settings that the host keeps outside the repository are recorded in the docs folder's README.

## Consequences

- No host credential is stored in GitHub, and no CI job can publish the site.
- The host runs the same build as CI, and that build fails on a broken link. A broken link that reaches `main` without a pull request fails the host's build, and the site is not deployed.
- The deploy tool's version is pinned in the lockfile and updated with the site's other packages.
- Some build settings live with the host, where a pull request does not review them. The README section that records them must change with them.
- The host's app needs read access to the repository.

## Alternatives Considered

**A deploy job in CI.** A job in the docs workflow deploys the built site with the host's API token, as ADR-0006 set out. It keeps every setting in the repository, but it stores a write credential for the host in GitHub, and the workflow needs its own rules to stop an older build from deploying over a newer one. It was not chosen because the host's Git integration deploys with no credential in GitHub.
