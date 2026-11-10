# smart-html-jtd

One merged GitHub Pages site for the SMART IGs' **just-the-docs** builds, the
docs-only counterpart of
[WorldHealthOrganization/smart-html](https://github.com/WorldHealthOrganization/smart-html)
(which merges the IG Publisher output of every SMART IG into smart.who.int).

This is not a fork of smart-html. It reuses the idea (one web root, one folder
per IG, one folder per release), not the content or the pipeline.

## Goals

1. **One site, every IG.** `/<ig>/` is the current build, `/<ig>/<version>/` a release.
2. **Shared things once.** Theme assets, form tools, viewers and the harness's
   own docs live once at the root and every IG points at them.
3. **A small source repository.** The site is published to `gh-pages` with
   the platform's publisher, like every IG. Git holds only this README, the docs, the site list and the
   compose script.
4. **Binaries are release assets, not git blobs.** Packages, zips and databases
   are attached to the IG repository's GitHub Release for that version.

## Docs

| Doc | What it covers |
|---|---|
| [docs/size-analysis.md](docs/size-analysis.md) | Measured sizes: docs-only builds vs IG Publisher builds vs smart-html (2026-11-08) |
| [docs/smart-html-pipeline-review.md](docs/smart-html-pipeline-review.md) | How the WHO smart-html pipeline works, where its 9.9 GB comes from, ranked optimisations |
| [docs/publishing-workflow.md](docs/publishing-workflow.md) | Proposed workflow for this repo: per-IG build, compose, deploy |
| [docs/binary-publication.md](docs/binary-publication.md) | Why binaries are in git today and how to publish them as release assets |
| [scripts/landing.py](scripts/landing.py) | The landing page: publication tables shaped like smart.who.int's, in the IG sites' theme |
| [scripts/catalog.py](scripts/catalog.py) | Builds the landing tables from every harnessed, published `smart-*` / `dth-*` repository (guidelines, L2 documents, shared foundations) |
| [docs/shared-assets.md](docs/shared-assets.md) | The assets every IG site shares, served once from here: keys, opt-in, how keys get here |

## Status

Design only (2026-11-08). No workflow runs yet.
