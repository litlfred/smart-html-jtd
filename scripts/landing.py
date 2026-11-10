#!/usr/bin/env python3
"""Render the merged site's landing page (index.html).

    python3 scripts/landing.py --sites sites.json --catalog catalog.json --out _site/index.html

The page has the shape of smart.who.int's "SMART Guideline Publications"
table (health domain with its cover, publication date, the DAK, the DAK
components, the FHIR IG and its source), drawn in the theme the IG sites use
(page-layout.css: the blue page bar, system font, the same colour tokens and
dark scheme). It is one self-contained file except for the cover images.

Rows come from the catalogue scripts/catalog.py builds from the repositories
(three sections: guidelines, L2 documents such as the DTHs and smart-ra, and
shared foundations). Without a catalogue it lists only the IGs in sites.json.
A filter box narrows every section as you type.
"""
import argparse
import datetime
import html
import json
import os
import sys

E = html.escape

# Icons as inline SVG (the IG sites load no icon font). currentColor, so they
# follow the scheme.
ICON = {
    "pdf": '<svg class="ico ico-pdf" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 1h5l4 4v10H4z" fill="none" stroke="currentColor" stroke-width="1.3"/><path d="M9 1v4h4" fill="none" stroke="currentColor" stroke-width="1.3"/><text x="8.5" y="12.6" font-size="4.6" font-weight="700" text-anchor="middle" fill="currentColor" font-family="system-ui,sans-serif">PDF</text></svg>',
    "page": '<svg class="ico ico-page" viewBox="0 0 16 16" aria-hidden="true"><path d="M3 1h6l4 4v10H3z" fill="none" stroke="currentColor" stroke-width="1.3"/><path d="M9 1v4h4M5.5 8h5M5.5 10.5h5M5.5 13h3" fill="none" stroke="currentColor" stroke-width="1.2"/></svg>',
    "fhir": '<svg class="ico ico-fhir" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1c.6 2.6 4.5 4.4 4.5 8.4A4.5 4.5 0 0 1 3.5 9.4C3.5 7 5 5.7 5.8 4.4c.3 1.6 1 2.3 1.7 2.6C7.4 4.9 7.6 2.8 8 1z" fill="currentColor"/></svg>',
    "github": '<svg class="ico ico-gh" viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>',
}

CSS = """
:root{--fa-pl-fg:#1f2328;--fa-pl-bg:#fff;--fa-pl-muted:#59636e;--fa-pl-line:#d1d9e0;--fa-pl-soft:#f6f8fa;--fa-pl-link:#0b5cad;
  --bar-bg:#1c4b7c;--bar-fg:#fff;--head-bg:#2f6aa3;--head-fg:#fff;--card:#fff;--pdf:#b30b00;--page:#1d6f42;--fhir:#c2410c;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-fa-scheme="light"]){--fa-pl-fg:#e6edf3;--fa-pl-bg:#0d1117;--fa-pl-muted:#9198a1;--fa-pl-line:#3d444d;--fa-pl-soft:#151b23;--fa-pl-link:#6cb6ff;
  --bar-bg:#163a60;--head-bg:#1f4f7d;--card:#0d1117;--pdf:#ff7b72;--page:#56d364;--fhir:#ffa657;color-scheme:dark}}
:root[data-fa-scheme="dark"]{--fa-pl-fg:#e6edf3;--fa-pl-bg:#0d1117;--fa-pl-muted:#9198a1;--fa-pl-line:#3d444d;--fa-pl-soft:#151b23;--fa-pl-link:#6cb6ff;
  --bar-bg:#163a60;--head-bg:#1f4f7d;--card:#0d1117;--pdf:#ff7b72;--page:#56d364;--fhir:#ffa657;color-scheme:dark}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--fa-pl-soft);color:var(--fa-pl-fg);font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--fa-pl-link)}
.fa-page-bar{position:sticky;top:0;z-index:10;display:flex;flex-wrap:wrap;align-items:center;gap:.25rem 1.25rem;padding:.5rem 1.5rem;background:var(--bar-bg);color:var(--bar-fg);font-size:.95rem}
.fa-page-bar a{color:inherit;text-decoration:none}
.fa-page-bar a:hover,.fa-page-bar a:focus-visible{text-decoration:underline}
.bar-home{font-weight:600;margin-right:auto}
.masthead{background:var(--fa-pl-bg);border-bottom:1px solid var(--fa-pl-line);padding:1.25rem 1.5rem}
.masthead .brand{display:flex;align-items:center;gap:.75rem;font-size:1.35rem;font-weight:600;color:var(--bar-bg);line-height:1.2}
:root[data-fa-scheme="dark"] .masthead .brand{color:var(--fa-pl-link)}
@media (prefers-color-scheme:dark){:root:not([data-fa-scheme="light"]) .masthead .brand{color:var(--fa-pl-link)}}
.masthead .brand small{display:block;font-size:.85rem;font-weight:400;color:var(--fa-pl-muted)}
.brand-mark{flex:none;width:2.5rem;height:2.5rem;border-radius:6px;background:var(--bar-bg);color:#fff;display:grid;place-items:center;font-weight:700;font-size:1.1rem}
main{max-width:84rem;margin:0 auto;padding:1.5rem 1.5rem 3rem}
h1{font-size:1.6rem;line-height:1.25;margin:.25rem 0 1rem}
h2{font-size:1.3rem;margin:2.5rem 0 .75rem;border-bottom:1px solid var(--fa-pl-line);padding-bottom:.25rem}
.lede p{margin:.4rem 0;max-width:60rem}
.updated{color:var(--fa-pl-muted);font-size:.92rem;margin-top:1rem}
.note{border-left:4px solid var(--fa-pl-line);padding:.25rem .9rem;color:var(--fa-pl-muted);font-size:.9rem;margin:1rem 0}
.pubs{width:100%;border-collapse:separate;border-spacing:0;margin-top:1.5rem;background:var(--card);border:1px solid var(--fa-pl-line);border-radius:8px;overflow:hidden;font-size:.97rem}
.pubs th{background:var(--head-bg);color:var(--head-fg);text-align:left;vertical-align:middle;padding:.9rem 1rem;font-weight:600;line-height:1.3}
.pubs td{padding:1rem;vertical-align:middle;border-top:1px solid var(--fa-pl-line)}
.pubs tbody tr:nth-child(even) td{background:var(--fa-pl-soft)}
.pubs ul{list-style:none;margin:0;padding:0}
.pubs li{margin:.2rem 0;display:flex;gap:.5rem;align-items:flex-start}
.pubs a{text-decoration:none}
.pubs a:hover,.pubs a:focus-visible{text-decoration:underline}
.domain{font-weight:500}
.cover{display:block;width:100px;height:auto;margin:.6rem auto 0;border:1px solid var(--fa-pl-line);border-radius:4px;background:var(--fa-pl-soft)}
.ico{flex:none;width:1.05em;height:1.05em;margin-top:.22em}
.ico-pdf{color:var(--pdf)}.ico-page{color:var(--page)}.ico-fhir{color:var(--fhir)}.ico-gh{color:var(--fa-pl-fg)}
.na{color:var(--fa-pl-muted)}
.found{display:grid;grid-template-columns:repeat(auto-fill,minmax(18rem,1fr));gap:1rem;margin:1rem 0 0;padding:0;list-style:none}
.found li{background:var(--card);border:1px solid var(--fa-pl-line);border-radius:8px;padding:1rem}
.found h3{margin:0 0 .25rem;font-size:1.05rem}
.found p{margin:0 0 .6rem;color:var(--fa-pl-muted);font-size:.92rem}
.found .links{display:flex;flex-wrap:wrap;gap:.4rem 1.2rem}
.found .links a{display:inline-flex;gap:.4rem;align-items:flex-start;text-decoration:none}
footer{background:var(--bar-bg);color:var(--bar-fg);text-align:center;font-size:.82rem;padding:.75rem 1.5rem}
footer a{color:inherit}
.meta{display:block;color:var(--fa-pl-muted);font-size:.8rem;margin-top:.15rem}
.badge{display:table;margin:.35rem 0 .1rem;padding:.05rem .45rem;border:1px solid currentColor;border-radius:3px;font-size:.75rem;font-weight:600;color:var(--fa-pl-link)}
.count{font-size:.85rem;font-weight:400;color:var(--fa-pl-muted)}
.filter{display:flex;gap:.6rem;align-items:center;margin:1rem 0 0;max-width:32rem}
.filter label{font-weight:600}
.filter input{flex:1;font:inherit;padding:.4rem .6rem;border:1px solid var(--fa-pl-line);border-radius:4px;background:var(--fa-pl-bg);color:var(--fa-pl-fg)}
.pubs{margin-top:.75rem}
@media (max-width:52rem){
  .pubs,.pubs tbody,.pubs tr,.pubs td{display:block;width:100%}
  .pubs thead{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
  .pubs tr{border-top:1px solid var(--fa-pl-line)}
  .pubs tbody tr:first-child{border-top:0}
  .pubs td{border-top:0;padding:.35rem 1rem}
  .pubs td:first-child{padding-top:1rem}
  .pubs td:last-child{padding-bottom:1rem}
  .pubs td[data-label]::before{content:attr(data-label);display:block;font-size:.78rem;font-weight:600;color:var(--fa-pl-muted);text-transform:uppercase;letter-spacing:.03em}
  .pubs tbody tr:nth-child(even) td{background:var(--fa-pl-soft)}
  .cover{margin:.5rem 0 0}
}
@media (max-width:40rem){.fa-page-bar,.masthead,main,footer{padding-left:1rem;padding-right:1rem}h1{font-size:1.35rem}}
"""


def link(kind, href, text, external=False):
    rel = ' rel="noopener"' if external else ""
    return f'<li>{ICON[kind]}<a href="{E(href)}"{rel}>{E(text)}</a></li>'


def ul(items):
    return f'<ul>{"".join(items)}</ul>' if items else '<span class="na">Not available</span>'


def at(e, page):
    return e["site"] + page


def fmt_date(s):
    """2024-12-06 -> December 2024; a year or free text stays as written."""
    if not s:
        return ""
    try:
        return datetime.date.fromisoformat(s).strftime("%B %Y")
    except ValueError:
        return s


def meta_line(e):
    bits = [f'v{e["version"]}' if e.get("version") else "", e.get("releaseLabel") or e.get("status") or ""]
    bits = [b for b in bits if b]
    return f'<small class="meta">{E(" · ".join(bits))}</small>' if bits else ""


def l3_links(e):
    out = []
    if e.get("fhirIg"):
        label = "FHIR Implementation Guide (draft)"
        out.append(link("fhir", e["site"], label, not e["hostedHere"]))
        if e.get("upstream", {}).get("ciBuild"):
            out.append(link("fhir", e["upstream"]["ciBuild"], "WHO CI build", True))
    out.append(link("github", e["github"], "GitHub", True))
    if e.get("upstream"):
        out.append(link("github", e["upstream"]["github"], "WHO repository", True))
    return out


def search_text(e):
    return E(" ".join(str(x) for x in [e.get("domain"), e.get("title"), e["name"], e.get("layer")] if x).lower())


def guideline_row(e):
    domain = e.get("domain") or e.get("title") or e["name"]
    sub = f'<small class="meta">{E(e["title"])}</small>' if e.get("domain") and e.get("title") else ""
    cover = ""
    if e.get("cover"):
        cover = f'<img class="cover" src="{E(e["cover"])}" alt="Cover of the {E(domain)} Digital Adaptation Kit" loading="lazy" width="100" height="135" onerror="this.remove()">'
    dak = e.get("dak")
    dak_cell = ul([link("pdf", dak["url"], dak.get("title", "Digital Adaptation Kit"), True)] if dak else [])
    comps = [link("page", c.get("url") or at(e, c["page"]), c["title"], "url" in c or not e["hostedHere"]) for c in e.get("components", [])]
    date = e.get("published") or fmt_date(e.get("date"))
    return (f'<tr data-search="{search_text(e)}">'
            f'<td data-label="Health domain"><span class="domain">{E(domain)}</span>{sub}{cover}</td>'
            f'<td data-label="Publication date">{E(date) or "<span class=na>Draft</span>"}{meta_line(e)}</td>'
            f'<td data-label="Digital Adaptation Kit (DAK, L2)">{dak_cell}</td>'
            f'<td data-label="DAK components (L2)">{ul(comps)}</td>'
            f'<td data-label="FHIR Implementation Guide (L3)">{ul(l3_links(e))}</td>'
            "</tr>")


def document_row(e):
    title = e.get("title") or e["name"]
    sub = f'<small class="meta">{E(e["subtitle"])}</small>' if e.get("subtitle") else ""
    if e.get("role") == "reference-architecture":
        sub = '<span class="badge">Reference architecture for the DTHs</span>' + sub
    links = e.get("links") or []
    main_doc = [link("page", at(e, links[0]["page"]), links[0]["title"], not e["hostedHere"])] if links else [link("page", e["site"], "Site", not e["hostedHere"])]
    parts = [link("page", at(e, l["page"]), l["title"], not e["hostedHere"]) for l in links[1:]]
    kind = e.get("documentKind") or ""
    return (f'<tr data-search="{search_text(e)}">'
            f'<td data-label="Handbook"><span class="domain">{E(title)}</span>{sub}</td>'
            f'<td data-label="Date">{E(fmt_date(e.get("date"))) or "<span class=na>Not dated</span>"}'
            f'{f"<small class=meta>{E(kind)}</small>" if kind else ""}</td>'
            f'<td data-label="L2 document">{ul(main_doc)}</td>'
            f'<td data-label="Components (L2)">{ul(parts)}</td>'
            f'<td data-label="Source">{ul(l3_links(e))}</td>'
            "</tr>")


def foundation(e):
    title = e.get("title") or e["name"]
    summary = f'<p>{E(e["summary"])}</p>' if e.get("summary") else ""
    return (f'<li data-search="{search_text(e)}"><h3>{E(title)}</h3>{meta_line(e)}{summary}<div class="links">'
            f'<a href="{E(e["site"])}">{ICON["fhir"]}<span>FHIR Implementation Guide (draft)</span></a>'
            f'<a href="{E(e["github"])}" rel="noopener">{ICON["github"]}<span>GitHub</span></a>'
            "</div></li>")


def entries_from_sites(cfg):
    """No catalogue (offline): one entry per IG this site hosts, from sites.json alone."""
    base = cfg.get("base", "").rstrip("/")
    found = cfg.get("catalog", {}).get("foundations", [])
    over = cfg.get("catalog", {}).get("overrides", {})
    out = []
    for ig in cfg["igs"]:
        name = ig["repo"].split("/")[1]
        e = {"repo": ig["repo"], "name": name, "site": f'{base}/{ig["path"]}/', "hostedHere": True,
             "github": f'https://github.com/{ig["repo"]}', "title": ig.get("title"), "fhirIg": True,
             "section": "foundations" if name in found else "guidelines", "components": [], "links": []}
        e.update(over.get(name, {}))
        out.append(e)
    return out


TABLE_JS = """
(function(){var q=document.getElementById("filter");if(!q)return;
var rows=[].slice.call(document.querySelectorAll("[data-search]"));
var counts=[].slice.call(document.querySelectorAll("[data-count]"));
function run(){var v=q.value.trim().toLowerCase();rows.forEach(function(r){r.hidden=!!v&&r.getAttribute("data-search").indexOf(v)<0});
counts.forEach(function(c){var box=document.getElementById(c.getAttribute("data-count"));var n=box.querySelectorAll("[data-search]:not([hidden])").length;c.textContent=n+(n===1?" entry":" entries")})}
q.addEventListener("input",run);run()})();
"""


def render(cfg, entries=None, updated=None):
    entries = entries if entries is not None else entries_from_sites(cfg)
    site = cfg.get("site", {})
    title = site.get("title", "SMART Guidelines")
    subtitle = site.get("subtitle", "Implementation Guide docs builds")
    updated = updated or datetime.datetime.now(datetime.timezone.utc).strftime("%B %Y")
    official = site.get("official", "https://smart.who.int/")
    initiative = site.get("initiative", "https://www.who.int/teams/digital-health-and-innovation/smart-guidelines")
    key = lambda e: (e.get("domain") or e.get("title") or e["name"]).lower()
    guides = sorted((e for e in entries if e.get("section") == "guidelines"), key=key)
    # The DTHs first, then the reference architecture they all build on (smart-ra).
    docs = sorted((e for e in entries if e.get("section") == "documents"),
                  key=lambda e: (e.get("role") == "reference-architecture", key(e)))
    founds = sorted((e for e in entries if e.get("section") == "foundations"), key=key)
    nav = ['<a href="#publications">Guidelines</a>']
    if docs:
        nav.append('<a href="#handbooks">Handbooks</a>')
    if founds:
        nav.append('<a href="#foundations">Shared foundations</a>')
    docs_html = ""
    if docs:
        docs_html = ('<h2 id="handbooks">Digital Transformation Handbooks (L2) <small class="count" data-count="docs-table"></small></h2>'
                     "<p>L2 documents built on WHO Digital Transformation Handbooks and the DPI-H Reference Architecture, "
                     "with their glossary, ArchiMate and review pages.</p>"
                     '<table class="pubs" id="docs-table"><thead><tr><th scope="col">Handbook</th><th scope="col">Date</th>'
                     '<th scope="col">L2 document</th><th scope="col">Components<br>(L2)</th><th scope="col">Source</th></tr></thead>'
                     f'<tbody>{"".join(document_row(e) for e in docs)}</tbody></table>')
    found_html = ""
    if founds:
        found_html = ('<h2 id="foundations">Shared foundations <small class="count" data-count="found-list"></small></h2>'
                      "<p>Implementation Guides every SMART Guideline builds on.</p>"
                      f'<ul class="found" id="found-list">{"".join(foundation(e) for e in founds)}</ul>')
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(title)}: {E(subtitle)}">
<meta name="theme-color" content="#1c4b7c">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Crect width='16' height='16' rx='3' fill='%231c4b7c'/%3E%3C/svg%3E">
<script>try{{var s=localStorage.getItem("fa-color-scheme");if(s==="dark"||s==="light")document.documentElement.setAttribute("data-fa-scheme",s)}}catch(e){{}}</script>
<style>{CSS}</style>
</head>
<body>
<nav class="fa-page-bar" aria-label="Site">
<a class="bar-home" href="./">{E(title)}</a>
{"".join(nav)}
<a href="{E(official)}" rel="noopener">smart.who.int</a>
</nav>
<header class="masthead"><div class="brand"><span class="brand-mark" aria-hidden="true">S</span><span>{E(title)}<small>{E(subtitle)}</small></span></div></header>
<main id="main-content">
<h1 id="publications">SMART Guideline Publications</h1>
<div class="lede">
<p>The tables below list every harnessed SMART Guideline and Digital Transformation Handbook, with links to each Digital Adaptation Kit (L2), its components, and the draft build of its FHIR Implementation Guide (L3). They are built from the repositories themselves each time the site is composed.</p>
<p>For more information on the WHO SMART Guidelines initiative, <a href="{E(initiative)}" rel="noopener">visit here</a>. The official publications are at <a href="{E(official)}" rel="noopener">smart.who.int</a>.</p>
</div>
<p class="updated">Last updated: {E(updated)}</p>
<div class="filter"><label for="filter">Filter</label><input id="filter" type="search" placeholder="Health domain, title or repository" autocomplete="off"></div>
<h2 id="guidelines">SMART Guidelines (DAK, L2 and FHIR IG, L3) <small class="count" data-count="guides-table"></small></h2>
<table class="pubs" id="guides-table">
<thead><tr><th scope="col">Health domain</th><th scope="col">Publication date</th><th scope="col">Digital Adaptation Kit<br>(DAK, L2)</th><th scope="col">DAK components<br>(L2)</th><th scope="col">FHIR Implementation Guide<br>(L3)</th></tr></thead>
<tbody>
{"".join(guideline_row(e) for e in guides)}
</tbody>
</table>
{docs_html}
{found_html}
<p class="note">These are draft, docs-only builds. The FHIR package, downloads and the IG Publisher build stay with each guide's own release.</p>
</main>
<footer><a href="{E(official)}" rel="noopener">smart.who.int</a> · <a href="https://github.com/{E(site.get('repo', 'litlfred/smart-html-jtd'))}" rel="noopener">Source</a></footer>
<script>{TABLE_JS}</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", required=True)
    ap.add_argument("--catalog", help="catalogue from scripts/catalog.py (default: only the IGs in sites.json)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--updated", help='date shown as "Last updated" (default: this month)')
    a = ap.parse_args()
    cfg = json.load(open(a.sites, encoding="utf-8"))
    entries = json.load(open(a.catalog, encoding="utf-8"))["entries"] if a.catalog else None
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(render(cfg, entries, a.updated))
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
