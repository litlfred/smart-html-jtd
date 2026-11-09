# WHO smart-html render pipeline: review and optimisations

Reviewed at WorldHealthOrganization/smart-html `main` 4191acf (2026-10-12).
Sizes are in [size-analysis.md](size-analysis.md).

## How it works today

1. An IG repository calls `smart-html/.github/workflows/release.yml@main` from
   its `release-candidate` branch when `publication-request.json` is present.
2. The job installs Java 17, Python 3.11, Node 18 + SUSHI, Graphviz, Ruby and
   Jekyll on every run. It downloads `ig_publisher.py`, `requirements.txt` and
   `release-config.yaml` from smart-html `main`, and the pre-SUSHI scripts from
   smart-ig-template `master`, all unpinned.
3. `ig_publisher.py`:
   - clones the source, the HL7 history template, the FHIR ig-registry and the
     smart-html web root (sparse: `templates/`, `assets/`, the IG's folder);
   - downloads `publisher.jar` from `releases/latest` (unpinned);
   - runs the IG Publisher **twice**: a normal `-ig .` build, then
     `-go-publish` (which builds again in publication mode);
   - moves files over 100 MB out of the web root into `release-assets/`;
   - rsyncs the whole (sparse) web root to the IG repo's
     `gh-pages/sitepreview/` and pushes;
   - opens a PR to smart-html `main` with the new web root content (squash
     merged by a maintainer), and a PR to ig-registry;
   - uploads `release-assets/` to a GitHub Release, but only when a release
     for the tag already exists.
4. smart-html `main` is served by GitHub Pages at smart.who.int (`CNAME`).
   `publish-setup.json` declares `"server": "apache"` and
   `"clone-xml-json": true`.

Separately, each IG's own CI (`ghbuild`) publishes a full IG Publisher build
per branch into that IG's `gh-pages/branches/<branch>/`, which is never pruned.

## Findings, ranked by size impact

| # | Finding | Impact |
|---|---|---|
| 1 | **Release binaries are committed** (`full-ig.zip`, `package.db`, definition/example zips, `.pack`). They compress poorly and every version adds new ones. See [binary-publication.md](binary-publication.md). | 1.9 GB in the site, and the largest share of git growth |
| 2 | **`clone-xml-json: true`** writes `.json1/.json2/.xml1/.xml2` copies for Apache content negotiation. GitHub Pages does no content negotiation, so they are never served by negotiation. | 1.5 GB, 57,752 files |
| 3 | **Shared web assets are copied into every IG and every version** (the IG template's `assets/`, fonts, jQuery, Prism, ...). | 1.3 GB of duplicates |
| 4 | **Every version is a full static copy** (trust: 15 versions). | ~5.9 GB |
| 5 | **QA reports are published** in every version. | 0.7 GB |
| 6 | **`.ttl` and `.xml` for every resource, each with its own HTML view.** | 0.9 GB + views |
| 7 | JS source maps published. | 0.12 GB |
| 8 | Per-branch IG builds are never pruned on IG `gh-pages` (`branches/`), and `sitepreview/` copies the whole web root. | 6 to 10 GB per IG repo |

GitHub Pages documents a 1 GB limit for a published site. smart.who.int is at
9.9 GB and almost 293k files.

## Pipeline issues (correctness and speed)

- **Two IG Publisher runs** per release (`build()` then `publish()`), the
  slowest step done twice.
- **Unpinned inputs**: scripts from `main`/`master`, `publisher.jar` from
  `latest`, `jekyll` unversioned. The same release can't be rebuilt.
- **Errors swallowed**: the pre-SUSHI scripts run with `|| true`.
- **Tool install every run** (Ruby, Jekyll, Graphviz, SUSHI). A prebuilt image
  (`hl7fhir/ig-publisher-base` is mentioned in the readme but not used) would
  skip it.
- **Large-file diversion breaks the site**: files over 100 MB are moved out of
  the web root before the PR, but are uploaded only if a release exists.
  Otherwise they are silently missing.
- **Release PRs carry the whole IG folder**: a new version squash-merges a full
  copy into a 9.9 GB repository.

## Recommended optimisations

Ordered by saving per unit of effort. None of these need IG content changes.

1. Set `"clone-xml-json": false` and delete the existing `*.json1/2`,
   `*.xml1/2` files. Saves 1.5 GB and 58k files. Check that nothing links to them
   (Apache-only feature).
2. Publish binaries as GitHub Release assets on the IG repo and link to them
   ([binary-publication.md](binary-publication.md)). Keep only the small
   `package.tgz` on the site, for the package feed. Saves ~1.9 GB.
3. Exclude QA output and `*.map` from the web root copy (keep QA as a CI
   artifact or a release asset). Saves ~0.8 GB.
4. Hoist shared template assets to one versioned root (`/assets/<template
   version>/`) and rewrite references at publish time. Saves ~1.3 GB.
5. Run the IG Publisher once (`-go-publish` only).
6. Pin every input (smart-html scripts by SHA, `publisher.jar` by version,
   pre-SUSHI scripts by SHA) and fail on script errors.
7. Deploy Pages from an Actions artifact instead of serving `main`. The site
   stops growing git history, and release PRs carry only metadata (see
   [publishing-workflow.md](publishing-workflow.md)).
8. Prune `branches/` on IG `gh-pages` for deleted branches, and make
   `sitepreview/` hold only the IG's folder.
9. Optionally publish `.ttl`/`.xml` only for releases, or load them through the
   same fetch-on-view loader already used by `slim_format_pages.py`.

Steps 1 to 4 alone take smart.who.int from about 9.9 GB to about 4.4 GB.

These are proposals for WHO's repository. Nothing has been changed there.
