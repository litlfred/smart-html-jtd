# Shared assets

Owner, 2026-11-09 (Q-SZ-7 "A"). Every IG docs site carried its own copy of
three directories, about 15 MB each time:

| Directory | What | Size |
|---|---|---:|
| `assets/lhc-forms/<version>/` | NLM LHC-Forms, which draws the Questionnaire form pages | 6.7 MB |
| `assets/vendor/crepe/` | the ✍ suggest editor (Milkdown Crepe + KaTeX) | 4.0 MB |
| `assets/img/harness/` | the harness landing images (rail avatars, page headers) | 5.2 MB |

This site serves them once, at `shared/<dir>/<key>/`. The form builder
(9 MB) stays with each IG: its offline service worker reads that IG's own
terminology files.

## Why here

This site is published from the same github.io account as the IG sites, so a
page, a frame or a service worker that loads these files stays on its own
origin (litlfred.github.io, or worldhealthorganization.github.io for a WHO
copy). A CDN would be a different origin.

## How an IG opts in

In the IG repository's `index.config.json`:

```json
"site": { "landing": "smart-base", "sharedAssets": "https://litlfred.github.io/smart-html-jtd/" }
```

At its next build, cat-harness-tools' `scripts/lib/shared-assets.ts` checks
each directory's `<host>shared/<dir>/<key>/.shared.json`. If it is served, the
build rewrites the site's references to it and drops its own copy. If it is
not, the build keeps the copy and says so. A site never points at nothing.

## The key

The key is a digest of the directory's files, so a site loads exactly the
bytes it was built with. The editor bundle is the exception. Bun names its
chunks by a hash of the temporary build path, so two builds of the same
versions differ. The bundle therefore carries a `.build.json` with the
versions it was built from, and its key is a digest of that file.

## How keys get here

`compose.yml` runs `shared-assets.ts stage` over each IG's published build. A
directory that is not yet here is copied to `shared/<dir>/<key>/` and kept on
the `shared` branch. Keys are only ever added, so an old site keeps working.
The loop heals itself:

1. An IG re-pins and builds. Its new key is not served yet, so the build keeps
   its own copy.
2. The next compose stages that copy from the IG's build.
3. The IG's next build finds the key and shares it.

## Before the first run

Pages must be on: Settings → Pages → Source: **GitHub Actions**. Then run
"Compose and deploy" by hand.
