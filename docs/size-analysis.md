# Size analysis (2026-11-08)

All numbers are git tree blob sizes on the published branch (MB = 10^6 bytes),
measured on 2026-11-08. "Main build" means one copy of the IG at the site root,
without branch previews or release copies.

## smart-immunizations

| Site | Built | Whole branch | Main build |
|---|---|--:|--:|
| litlfred/smart-immunizations `gh-pages` (docs-only) | 2026-10-31 | 450 MB, 17,067 files | 246 MB, 9,138 files |
| WorldHealthOrganization/smart-immunizations `gh-pages` (IG Publisher) | 2026-10-02 | 8,814 MB, 163,802 files | 444 MB, 11,615 files |

The WHO branch also holds `branches/` (10 per-branch copies, 6.2 GB) and
`sitepreview/` (2.1 GB, including a 1 GB copy of v1.0.0). The litlfred branch
holds one preview under `STAGING/` (204 MB).

## smart-base

| Site | Built | Whole branch | Main build |
|---|---|--:|--:|
| litlfred/smart-base `gh-pages` | 2026-10-26 | 6,656 MB, 90,820 files | 146 MB, 4,003 files |
| WorldHealthOrganization/smart-base `gh-pages` | 2026-11-04 | 10,889 MB, 153,117 files | 253 MB, 3,034 files |

litlfred/smart-base still carries `branches/` with 35 old IG Publisher branch
copies (6.5 GB). WHO carries 50 branch copies (9.6 GB) and `sitepreview/` (1 GB).

For one build, the IG Publisher output is about **1.7 to 1.8 times** the
docs-only build. The whole-branch sizes are driven by the per-branch copies.

## What the 246 MB docs-only main build is (smart-immunizations)

| Part | MB | Files | Needed per IG? |
|---|--:|--:|---|
| `assets/` (form builder 9.7, LHC-Forms 6.7, vendor libs incl. PDF viewer 15.3, `js/` incl. 6.2 MB search index 9.5, images 12.6, `assets/library` 18.3, glossary 3.4) | 82.0 | 1,280 | Mostly shared: 55% is byte-identical to smart-base's copy |
| `ast-data/resources` (parsed copy of every FHIR resource) | 46.7 | 756 | **No**: owner, 2026-11-08 |
| FHIR resource JSON at the root (Library 26.2 with embedded ELM, PlanDefinition 8.1, Measure 5.4) | ~46 | ~720 | The resources, yes; the embedded ELM should load from the KG |
| `en/cat-harness/` (harness processes 8.8, library 5.1, methodologies 2.3, ...) | 24.2 | 443 | **No**: only ~8 pages (0.4 MB) are smart-immunizations' own |
| `en/folio-assistant-core/` (bibliography 8.6, glossary 4.6) | 13.2 | 562 | No: the layer's own site has it |
| `artifact/` (thin viewer pages, ~5 KB each) | 13.6 | 3,485 | Yes |
| `cat-harness/auto-docs` (task/skill indexes, largest 522 KB) | 5.2 | 61 | No |
| `fhir-artifact-index/` + `smart-base/fhir-artifact-index/` (incl. a 1.2 MB package.tgz) | 6.7 | ~1,060 | Own index yes, smart-base copy no |
| questionnaires, who-iris, docs, code, other | ~8 | — | Mixed |

### Page weight

Every page rendered by the harness layout carries **about 31 KB of template
developer comments** (`<!-- ... -->` from the Liquid includes) in its `<head>`.
A typical 50 KB page is 18 KB without them. Across `en/` that is about 15 MB.

The bibliography index (758 KB) inlines four download formats per entry as
`data:` URIs (CSL-JSON, BibTeX, RIS, XML: 391 KB), while per-entry `.bib` /
`.ris` files are also published.

Harness pages are rendered per site (relative paths, site title), so **0%** of
`en/cat-harness/` is byte-identical between smart-immunizations and smart-base.
They cannot be shared by de-duplication. They have to be rendered once and
linked.

### Estimated docs-only build after trimming

| Step | Saves |
|---|--:|
| Drop `ast-data/resources` | 47 MB |
| Link to harness/core docs instead of re-rendering them | ~42 MB |
| Strip template comments | ~15 MB |
| Load ELM from the KG instead of embedding it in Library JSON | up to ~26 MB |
| Serve `assets/` from one shared root | ~82 MB per IG, paid once per site |

The result is roughly **30 to 60 MB per IG** plus one shared assets root.

## WorldHealthOrganization/smart-html `main` (smart.who.int)

9,858 MB in 292,819 files (shallow pack 1.16 GB, 294 commits since 2023-09-27).

| Category | MB | Files |
|---|--:|--:|
| `.json1/.json2/.xml1/.xml2` content-negotiation clones (`clone-xml-json: true`), byte-identical to the base file | 1,499 | 57,752 |
| Release binaries (`full-ig.zip`, `package.db`, `*.zip`, `.tgz`, `.pack`) | 1,901 | 663 |
| Duplicated web assets (same bytes in another folder) | 1,314 | — |
| Other HTML | 1,340 | 27,970 |
| `.ttl` / `.xml` alternate formats | 922 | 27,344 |
| QA reports (`qa*.html`, `qa.json`, ...) | 691 | 1,061 |
| Format view pages (`*.json.html` etc.) | 563 | 39,549 |
| Change history pages | 165 | 12,763 |
| JS source maps | 122 | 70 |

Per-version copies make up about 5.9 GB. trust alone has 15 versions (2.35 GB).
Exact duplicate files across the whole tree total 3.54 GB.
