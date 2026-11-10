#!/usr/bin/env python3
"""Render the merged site's landing page (index.html) from sites.json.

    python3 scripts/landing.py --sites sites.json --out _site/index.html

The page has the shape of smart.who.int's "SMART Guideline Publications"
table (health domain with its cover, publication date, the DAK, the DAK
components, the FHIR IG and its source), drawn in the theme the IG sites use
(page-layout.css: the blue page bar, system font, the same colour tokens and
dark scheme). It is one self-contained file, so it needs nothing from any IG
folder and nothing outside this site except the cover images.

Each IG in sites.json may carry:

  "domain"     health domain shown in the first column (default: title)
  "cover"      URL of the DAK cover image
  "published"  publication date as shown, e.g. "January 2025"
  "dak"        {"title", "url"}: the L2 publication (PDF / IRIS page)
  "components" [{"title", "page"} | {"title", "url"}]: DAK components; a
               `page` is relative to this IG's folder on this site
  "section"    "publications" (default) or "foundations": the second list
               holds shared IGs with no DAK of their own (smart-base)
  "summary"    one line under a foundation's name
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


def href_for(ig, item):
    return item["url"] if "url" in item else f'{ig["path"]}/{item["page"]}'


def pub_row(ig):
    domain = ig.get("domain", ig.get("title", ig["path"]))
    cover = ""
    if ig.get("cover"):
        cover = f'<img class="cover" src="{E(ig["cover"])}" alt="Cover of the {E(domain)} Digital Adaptation Kit" loading="lazy" width="100" height="135" onerror="this.remove()">'
    dak = ig.get("dak")
    dak_cell = f'<ul>{link("pdf", dak["url"], dak.get("title", "Digital Adaptation Kit"), True)}</ul>' if dak else '<span class="na">Not available</span>'
    comps = ig.get("components") or []
    comp_cell = "<ul>" + "".join(link("page", href_for(ig, c), c["title"], "url" in c) for c in comps) + "</ul>" if comps else '<span class="na">Not available</span>'
    l3 = [link("fhir", f'{ig["path"]}/', "FHIR Implementation Guide"),
          link("github", f'https://github.com/{ig["repo"]}', "GitHub", True)]
    return ("<tr>"
            f'<td data-label="Health domain"><span class="domain">{E(domain)}</span>{cover}</td>'
            f'<td data-label="Publication date">{E(ig.get("published", "")) or "<span class=na>Not published</span>"}</td>'
            f'<td data-label="Digital Adaptation Kit (DAK, L2)">{dak_cell}</td>'
            f'<td data-label="DAK components (L2)">{comp_cell}</td>'
            f'<td data-label="FHIR Implementation Guide (L3)"><ul>{"".join(l3)}</ul></td>'
            "</tr>")


def foundation(ig):
    title = ig.get("title", ig["path"])
    summary = f'<p>{E(ig["summary"])}</p>' if ig.get("summary") else ""
    return (f'<li><h3>{E(title)}</h3>{summary}<div class="links">'
            f'<a href="{E(ig["path"])}/">{ICON["fhir"]}<span>FHIR Implementation Guide</span></a>'
            f'<a href="https://github.com/{E(ig["repo"])}" rel="noopener">{ICON["github"]}<span>GitHub</span></a>'
            "</div></li>")


def render(cfg, updated=None):
    site = cfg.get("site", {})
    title = site.get("title", "SMART Guidelines")
    subtitle = site.get("subtitle", "Implementation Guide docs builds")
    updated = updated or datetime.datetime.now(datetime.timezone.utc).strftime("%B %Y")
    pubs = [ig for ig in cfg["igs"] if ig.get("section", "publications") == "publications"]
    founds = [ig for ig in cfg["igs"] if ig.get("section") == "foundations"]
    official = site.get("official", "https://smart.who.int/")
    initiative = site.get("initiative", "https://www.who.int/teams/digital-health-and-innovation/smart-guidelines")
    rows = "\n".join(pub_row(ig) for ig in pubs)
    found_html = ""
    if founds:
        found_html = ('<h2 id="foundations">Shared foundations</h2>'
                      "<p>Implementation Guides every SMART Guideline builds on.</p>"
                      f'<ul class="found">{"".join(foundation(ig) for ig in founds)}</ul>')
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
<a href="#publications">Publications</a>{'<a href="#foundations">Shared foundations</a>' if founds else ''}
<a href="{E(official)}" rel="noopener">smart.who.int</a>
</nav>
<header class="masthead"><div class="brand"><span class="brand-mark" aria-hidden="true">S</span><span>{E(title)}<small>{E(subtitle)}</small></span></div></header>
<main id="main-content">
<h1 id="publications">SMART Guideline Publications</h1>
<div class="lede">
<p>The table below lists the SMART Guidelines published on this site, with links to each Digital Adaptation Kit (L2), its components, and the docs build of its FHIR Implementation Guide (L3).</p>
<p>For more information on the WHO SMART Guidelines initiative, <a href="{E(initiative)}" rel="noopener">visit here</a>. The official publications are at <a href="{E(official)}" rel="noopener">smart.who.int</a>.</p>
</div>
<p class="updated">Last updated: {E(updated)}</p>
<table class="pubs">
<thead><tr><th scope="col">Health domain</th><th scope="col">Publication date</th><th scope="col">Digital Adaptation Kit<br>(DAK, L2)</th><th scope="col">DAK components<br>(L2)</th><th scope="col">FHIR Implementation Guide<br>(L3)</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
{found_html}
<p class="note">These are docs-only builds of each Implementation Guide. The FHIR package, downloads and the IG Publisher build stay with each guide's own release.</p>
</main>
<footer><a href="{E(official)}" rel="noopener">smart.who.int</a> · <a href="https://github.com/{E(site.get('repo', 'litlfred/smart-html-jtd'))}" rel="noopener">Source</a></footer>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--updated", help='date shown as "Last updated" (default: this month)')
    a = ap.parse_args()
    cfg = json.load(open(a.sites, encoding="utf-8"))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(render(cfg, a.updated))
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
