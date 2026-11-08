# Publishing workflow (proposed)

How the just-the-docs builds of all SMART IGs become one site here, with a git
repository that stays small.

## Layout of the published site

```
/                         landing: list of IGs and their versions
/_shared/<hash>/...       theme + tool bundles (form builder, LHC-Forms, PDF viewer,
                          Prism, search runtime), one copy per content hash
/_layers/<layer>/...      harness and core docs (cat-harness, folio-assistant-core,
                          fhir-harness, smart-base, who-iris), rendered once
/<ig>/                    current build of that IG: its own pages, FHIR JSON,
                          thin artifact/ viewers, its own search index
/<ig>/<version>/          a release of that IG (same shape)
```

An IG folder holds only what belongs to that IG. Anything that is the same for
every IG goes in `_shared/`, and anything owned by another layer goes in
`_layers/`.

## What each IG repository does

The IG keeps its existing `site-publish.yml` (`stage-local.ts`), with three
changes in the platform build (cat-harness-tools), not in the IG:

1. **Do not emit** `ast-data/resources`, the mounted layers' pages
   (`en/cat-harness/`, `en/folio-assistant-core/`, `cat-harness/auto-docs`),
   or template comments. Pages link to `_layers/` instead.
2. **Reference shared bundles by content hash** (`/_shared/<hash>/...`) and
   write a manifest `shared.json` listing each one and its hash.
3. **Package the build** as `site.tar.zst` and attach it to a GitHub Release
   (tag `site-<version>` for a release, a rolling `site-current` for the
   default branch), with the binaries (see
   [binary-publication.md](binary-publication.md)).

The IG's own `gh-pages` then only needs branch previews, or nothing at all.

## What this repository does

`sites.json` lists what to publish:

```json
{
  "igs": [
    { "repo": "litlfred/smart-immunizations", "path": "immunizations",
      "current": "site-current", "releases": ["site-1.0.0"] }
  ],
  "layers": ["cat-harness", "folio-assistant-core", "fhir-harness", "smart-base", "who-iris"]
}
```

A workflow (`compose.yml`, on dispatch, on a schedule, or on a
`repository_dispatch` from an IG release):

1. Downloads every listed `site.tar.zst` release asset.
2. Unpacks each into `/<ig>/` or `/<ig>/<version>/`.
3. Merges every `shared.json` into `/_shared/`. Same hash means one copy. A
   hash collision with different bytes fails the run.
4. Renders the layers once into `/_layers/`.
5. Runs the link check across the whole site.
6. Uploads the site with `actions/upload-pages-artifact` and deploys with
   `actions/deploy-pages`.

## Why the git repository stays small

- **No `gh-pages` branch.** Pages is deployed from an Actions artifact, so the
  built site is never committed and history never grows with it.
- **No binaries in git.** They are release assets on the IG repositories.
- **Git holds only** this README, `docs/`, `sites.json` and the compose
  script: kilobytes.

Rebuilding the site is cheap because it is a download, unpack and copy, with
no IG Publisher and no Jekyll for the IGs.

## Previews

Branch previews stay out of the merged site:

- An IG branch preview is a PR artifact (`site.tar.zst` uploaded by the IG's
  CI), or a `STAGING/<branch>/` folder on the IG's own `gh-pages` that is
  removed when the branch is deleted.
- A preview of this composed site is a `compose.yml` run on a PR, which
  uploads the artifact without deploying.

## Size budget

| Part | Estimate |
|---|--:|
| `_shared/` | ~80 to 100 MB |
| `_layers/` | ~50 MB |
| Each IG (current) | ~30 to 60 MB |
| Each IG release | ~30 to 60 MB |

About 20 IGs with a few releases each would come to roughly 1 to 2 GB, compared
with 9.9 GB for smart-html today. If that is still over the 1 GB Pages limit,
older releases can be served from their `site-<version>.tar.zst` on demand,
leaving only the current build and the latest release on Pages.

## Open questions

- Which IGs are listed first. Proposal: smart-immunizations and smart-base as
  the pilot.
- Whether `_layers/` is rendered here or downloaded from each layer's own
  release asset. The second keeps this repo free of the harness toolchain.
- Custom domain or `litlfred.github.io/smart-html-jtd/`. The relative paths
  must work under a sub-path either way.
