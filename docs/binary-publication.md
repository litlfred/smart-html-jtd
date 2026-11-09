# Binary publication

## Why the binaries are in git today

The FHIR IG Publisher's `-go-publish` was designed for HL7's own servers. It
writes a release straight into a **web root folder** on an Apache server:
pages, `package.tgz`, `full-ig.zip`, `package.db`, the definition and example
zips, and the `.pack` files all land next to the HTML.

smart-html adapted this to GitHub by making that web root a git repository
served by GitHub Pages. So whatever the publisher writes into the web root is
committed, binaries included. Two exceptions exist today:

- files over 100 MB (GitHub's hard file limit) are moved to `release-assets/`;
- `ig-build-zips/` is excluded from the preview copy.

Those moved files are uploaded to a GitHub Release only when one exists for the
tag. Otherwise they are dropped.

On WHO smart-html this is **663 binary files, 1.9 GB**. The largest are
`hiv/package.db` (97 MB), `ddcc/full-ig.zip` (50 MB, with a second copy in
`ddcc/1.0.1/`), and one `trust/*/full-ig.zip` of about 44 MB per version.

Binaries are the worst thing to keep in git:

- they barely compress, and every version adds a new copy to history forever;
- a clone, even a shallow one, has to download them;
- they count toward the Pages size limit and slow every Pages deploy.

## What to do instead

| File | Where it goes | Why |
|---|---|---|
| `package.tgz` | Site (`/<ig>/<version>/package.tgz`) **and** release asset | Small. FHIR tooling and the package feed fetch it from the canonical path |
| `full-ig.zip` | Release asset only | The site is the browsable form of the same content |
| `package.db` | Release asset only (or not published) | An IG Publisher working database, not something a reader needs |
| `definitions.*.zip`, `examples.*.zip` | Release asset only | Download bundles |
| `*.pack` | Release asset only | Download bundles |
| QA output | CI artifact, or release asset | Build evidence, not reader content |
| Docs-only `site.tar.zst` | Release asset (`site-<version>`, `site-current`) | Input to the compose step |

The download page of each IG links to
`https://github.com/<owner>/<ig-repo>/releases/download/<tag>/<file>`.

## How to publish them

In the IG repository's release job, after the build:

```bash
tag="v${VERSION}"
gh release view "$tag" >/dev/null 2>&1 || gh release create "$tag" --title "$tag" --notes-file CHANGELOG.md
gh release upload "$tag" output/package.tgz output/full-ig.zip output/*.zip --clobber
# then delete them from the web root copy, except package.tgz
```

For smart-html this means two changes to `ig_publisher.py`: always create the
release before uploading (instead of uploading only when one exists), and
divert binaries by type rather than only by size.

Release assets have a 2 GB per-file limit and no total limit per release.
Downloads are served from GitHub's CDN, and the IG repository's git history
never grows.

## Caveat

The FHIR package feed (`package-feed.xml`) and tools that resolve
`<canonical>/package.tgz` expect the package on the site itself. That is why
`package.tgz` stays on the site. GitHub Pages can't redirect a `.tgz` path to a
release asset.
