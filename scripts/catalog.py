#!/usr/bin/env python3
"""Build the landing page's catalogue from the repositories themselves.

    python3 scripts/catalog.py --sites sites.json --out catalog.json

What is listed is declared in the site's guideline portfolio
(`catalog.portfolio` in sites.json, default guideline-portfolio.json; issue
#20): smart-base's `guideline-portfolio/1.0.0` kind over cat-harness-tools'
`portfolio/1.0.0`. It names the SMART levels (L1 to L4, in order) and, for
each, the libraries whose members belong there. A library is reached one of
three ways:

- `library`: a who-iris catalogue, by item (IRIS handle). Each item's title,
  date and cover come from that catalogue (catalogue/nodes, catalogue/records,
  library/<id>-cover.png); it links to IRIS and, when who-iris holds it, to
  its who-iris entry page;
- `discover`: every repository of `owner` named with one of `prefixes`;
- `repos`: repositories listed by name.

`memberKind` says what a discovered or listed library takes: `folio-document`
or `fhir-ig`. For every candidate repository:

1. it is HARNESSED when it has an index.lock.json, and PUBLISHED when it has
   a gh-pages branch; only harnessed, published repositories are listed;
2. its layer name is the index.config.json instance read from `.` (smart-ra's
   is dpi-h-ra), and `<name>.json`, its declaration, gives its title and the
   pages it publishes (each directory's `coverage.visualiser`);
3. a folio manifest (folio/<name>/<name>.ts) makes it a `folio-document` (a
   DTH, smart-base document kinds `dth` / `l2-dth`); else a sushi-config.yaml
   makes it a `fhir-ig`, whose DAK component pages are read off its `pages:`;
4. it joins the first library, in level order, that takes its member kind
   and names it (`repos`), else matches it (`discover`). A `repos` library of
   IGs is a level's shared foundations.

Members are linked where they publish, never copied. The portfolio's
`memberOverrides` hold only what no repository holds (a DAK's cover and its
WHO publication link). A fork's upstream is `catalog.upstream`/<repo>, with
its CI build on build.fhir.org. The result is a JSON list that
scripts/landing.py renders.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

RAW = "https://raw.githubusercontent.com/{repo}/HEAD/{path}"

# DAK components as smart.who.int names them, and the IG pages that hold them.
DAK_PAGES = [
    ("Core data dictionary", ["dictionary"]),
    ("Decision support logic", ["decision-logic"]),
    ("Indicator table", ["indicators"]),
    ("Functional and non-functional requirements", ["system-requirements", "functional-requirements", "requirements"]),
]


SMART_LEVELS = ["L1", "L2", "L3", "L4"]
SOURCES = ("library", "discover", "repos")


def check_portfolio(p):
    """The checks of guideline-portfolio/1.0.0 (smart-base) that the catalogue
    relies on: SMART levels in order, unique ids, one source per library."""
    errs = []
    if not str(p.get("$schema", "")).startswith("guideline-portfolio/1."):
        errs.append(f"$schema is {p.get('$schema')!r}, not guideline-portfolio/1.x")
    extra = set(p) - {"$schema", "id", "title", "description", "levels", "memberOverrides"}
    if extra:
        errs.append(f"unknown keys {sorted(extra)}")
    last, libs = -1, set()
    for lv in p.get("levels") or []:
        at = SMART_LEVELS.index(lv["id"]) if lv.get("id") in SMART_LEVELS else -1
        if at <= last:
            errs.append(f"level {lv.get('id')!r} is not a SMART level in order ({', '.join(SMART_LEVELS)})")
        last = max(last, at)
        for lib in lv.get("libraries") or []:
            if lib.get("id") in libs:
                errs.append(f"library {lib.get('id')!r} is declared twice")
            libs.add(lib.get("id"))
            src = lib.get("source") or {}
            if [k for k in SOURCES if k in src] == [] or len([k for k in SOURCES if k in src]) > 1:
                errs.append(f"library {lib.get('id')!r}: source must be one of {', '.join(SOURCES)}")
    if not p.get("levels"):
        errs.append("no levels")
    if errs:
        raise ValueError("guideline portfolio: " + "; ".join(errs))
    return p


def load_portfolio(cfg, sites_dir="."):
    """The guideline portfolio sites.json names, checked."""
    path = os.path.join(sites_dir, cfg.get("catalog", {}).get("portfolio", "guideline-portfolio.json"))
    return check_portfolio(json.load(open(path, encoding="utf-8")))


def libraries(p):
    """Every (level, library), in level order."""
    for lv in p["levels"]:
        for lib in lv.get("libraries") or []:
            yield lv, lib


def foundations(p):
    """Repository names in a `repos` library of IGs: the shared foundations."""
    return {r.split("/")[1] for _, lib in libraries(p) for r in lib["source"].get("repos", [])
            if lib["source"].get("memberKind") in (None, "fhir-ig")}


def place(p, repo, member_kind, exclude=()):
    """The (level, library) that takes this repository, or (None, None)."""
    owner, name = repo.split("/")
    for lv, lib in libraries(p):  # a library that names it wins over one that discovers it
        src = lib["source"]
        if "repos" in src and repo in src["repos"] and src.get("memberKind") in (None, member_kind):
            return lv, lib
    for lv, lib in libraries(p):
        src = lib["source"]
        if "discover" in src:
            d = src["discover"]
            kind = d.get("memberKind")
            hit = (d["owner"] == owner and any(name.startswith(x) for x in d["prefixes"])
                   and name not in (d.get("exclude") or []) and name not in exclude)
        else:
            continue
        if hit and kind in (None, member_kind):
            return lv, lib
    return None, None


def http(url, token=None):
    req = urllib.request.Request(url, headers={"User-Agent": "smart-html-jtd-catalog", "Accept": "application/vnd.github+json"})
    if token and "api.github.com" in url:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def raw(repo, path):
    return http(RAW.format(repo=repo, path=path))


def search_repos(owner, prefixes, token):
    found = {}
    for p in prefixes:
        q = urllib.parse.quote(f"user:{owner} {p} in:name fork:true")
        page = 1
        while True:
            body = json.loads(http(f"https://api.github.com/search/repositories?q={q}&per_page=100&page={page}", token))
            for it in body["items"]:
                if it["name"].startswith(p) and not it["archived"]:
                    found[it["full_name"]] = {"fork": it["fork"], "description": it.get("description") or ""}
            if len(body["items"]) < 100:
                break
            page += 1
    return found


def has_branch(repo, branch):
    r = subprocess.run(["git", "ls-remote", "--exit-code", "--heads", f"https://github.com/{repo}", branch],
                       capture_output=True, text=True, timeout=60)
    return r.returncode == 0


def scalar(yaml_text, key):
    """A top-level scalar from sushi-config.yaml, without a YAML library."""
    m = re.search(rf"^{key}:\s*(.+?)\s*(?:#.*)?$", yaml_text, re.M)
    return m.group(1).strip().strip("\"'") if m else None


def manifest_field(ts, key):
    m = re.search(rf"\b{key}:\s*\"((?:[^\"\\]|\\.)*)\"", ts)
    return m.group(1) if m else None


def layer_name(repo, index_config):
    try:
        cfg = json.loads(index_config)
    except (TypeError, ValueError):
        return repo.split("/")[1]
    for inst in cfg.get("instances") or cfg.get("layers") or []:
        if ((inst.get("source") or {}).get("local") or {}).get("at") == ".":
            return inst["name"]
    return repo.split("/")[1]


def visualisers(decl):
    out = []
    for d in decl.get("directories") or []:
        for v in (d.get("coverage") or {}).get("visualiser") or []:
            if v.get("ref") and v.get("title"):
                out.append({"title": v["title"], "page": v["ref"]})
    return out


def entry(repo, info, cat, portfolio, hosted):
    owner, name = repo.split("/")
    if not raw(repo, "index.lock.json"):
        return None, "not harnessed"
    if not has_branch(repo, "gh-pages"):
        return None, "harnessed, no gh-pages"
    layer = layer_name(repo, raw(repo, "index.config.json"))
    decl = {}
    d = raw(repo, f"{layer}.json")
    if d:
        try:
            decl = json.loads(d)
        except ValueError:
            pass
    sushi = raw(repo, "sushi-config.yaml") or ""
    manifest = raw(repo, f"folio/{layer}/{layer}.ts") or ""
    site = f"{hosted[name]}/" if name in hosted else f"https://{owner}.github.io/{name}/"
    e = {
        "repo": repo,
        "name": name,
        "layer": layer,
        "site": site,
        "hostedHere": name in hosted,
        "github": f"https://github.com/{repo}",
        "components": [],
        "links": visualisers(decl),
    }
    if info.get("fork"):
        up = f'{cat.get("upstream", "WorldHealthOrganization")}/{name}'
        e["upstream"] = {"github": f"https://github.com/{up}"}
        if sushi:
            e["upstream"]["ciBuild"] = f"https://build.fhir.org/ig/{up}/"
    if manifest:
        e["section"] = "documents"
        e["title"] = manifest_field(manifest, "title") or decl.get("title") or name
        e["subtitle"] = manifest_field(manifest, "subtitle")
        e["date"] = manifest_field(manifest, "date")
        e["documentKind"] = manifest_field(manifest, "documentKind")
        e["level"] = manifest_field(manifest, "level")
        e["status"] = manifest_field(manifest, "status")
    elif sushi:
        e["section"] = "foundations" if name in foundations(portfolio) else "guidelines"
        e["title"] = scalar(sushi, "title") or decl.get("title") or name
        e["date"] = scalar(sushi, "date")
        e["version"] = scalar(sushi, "version")
        e["status"] = scalar(sushi, "status")
        e["releaseLabel"] = scalar(sushi, "releaseLabel")
        for title, pages in DAK_PAGES:
            hit = next((p for p in pages if re.search(rf"^\s+{re.escape(p)}\.md:", sushi, re.M)), None)
            if hit:
                e["components"].append({"title": title, "page": f"{hit}.html"})
    else:
        return None, "harnessed, neither a document nor an IG"
    if sushi:
        e["fhirIg"] = True
    lv, lib = place(portfolio, repo, "folio-document" if manifest else "fhir-ig", cat.get("exclude", []))
    if not lv:
        return None, "not in any library of the portfolio"
    e["portfolioLevel"], e["library"] = lv["id"], lib["id"]
    e.update((portfolio.get("memberOverrides") or {}).get(name, {}))
    return e, "listed"


def short_title(t):
    """A title up to its subtitle, unless that leaves too little to name it."""
    head = t.split(":")[0].strip()
    return head if len(head) >= 20 else t


def iris_publications(pub):
    """A `library` source's items, read from a sparse shallow clone of the
    who-iris catalogue (one fetch, rather than one request per node)."""
    if not pub or not pub.get("items"):
        return []
    import tempfile
    repo = pub.get("repo", "litlfred/who-iris")
    site = pub.get("site", f"https://{repo.split('/')[0]}.github.io/{repo.split('/')[1]}/").rstrip("/")
    d = tempfile.mkdtemp(prefix="who-iris-")
    run = lambda *a: subprocess.run(["git", "-C", d, *a], check=True, capture_output=True, text=True, timeout=600)
    subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--no-checkout",
                    f"https://github.com/{repo}", d], check=True, capture_output=True, timeout=600)
    run("sparse-checkout", "set", "--no-cone", "/catalogue/nodes/", "/catalogue/records/", "/library/*-cover.png")
    run("checkout", "-q")
    nodes = {}
    ndir = os.path.join(d, "catalogue", "nodes")
    for f in os.listdir(ndir):
        try:
            n = json.load(open(os.path.join(ndir, f), encoding="utf-8"))
        except ValueError:
            continue
        if n.get("kind") == "item" and n.get("handle"):
            nodes[n["handle"]] = n
    out = []
    for h in pub["items"]:
        n = nodes.get(h)
        if not n:
            print(f"  publication {h}: not in {repo}'s catalogue", file=sys.stderr)
            continue
        date = None
        try:
            rec = json.load(open(os.path.join(d, n["metadataRef"]), encoding="utf-8"))
            date = next((f["values"][0]["value"] for f in rec.get("fields", [])
                         if f.get("element") == "date" and f.get("qualifier") == "issued"), None)
        except (KeyError, OSError, ValueError):
            pass
        lid = n.get("libraryId")
        iris = f"https://iris.who.int/handle/{h}"
        e = {"section": "publications", "name": lid or h.replace("/", "-"), "handle": h,
             "title": n["title"], "short": short_title(n["title"]),
             "date": date, "iris": iris, "hostedHere": False, "site": iris,
             "state": (n.get("materialization") or {}).get("state")}
        if lid:
            e["entry"] = f"{site}/cat-harness/library/{repo.split('/')[1]}/{lid}/"
            e["site"] = e["entry"]
            if os.path.isfile(os.path.join(d, "library", f"{lid}-cover.png")):
                e["cover"] = RAW.format(repo=repo, path=f"library/{lid}-cover.png")
        out.append(e)
    return out


def candidates(p, token):
    """Every repository a `discover` or `repos` library names."""
    found = {}
    for _, lib in libraries(p):
        src = lib["source"]
        if "discover" in src:
            found.update(search_repos(src["discover"]["owner"], src["discover"]["prefixes"], token))
        for r in src.get("repos", []):
            if r not in found:
                body = http(f"https://api.github.com/repos/{r}", token)
                if body:
                    it = json.loads(body)
                    found[r] = {"fork": it.get("fork", False), "description": it.get("description") or ""}
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--check", action="store_true", help="only check the portfolio declaration")
    a = ap.parse_args()
    cfg = json.load(open(a.sites, encoding="utf-8"))
    cat = cfg.get("catalog", {})
    portfolio = load_portfolio(cfg, os.path.dirname(os.path.abspath(a.sites)))
    if a.check:
        print(f"portfolio {portfolio['id']}: {', '.join(lv['id'] for lv in portfolio['levels'])} ok")
        return 0
    base = cfg.get("base", "").rstrip("/")
    hosted = {ig["repo"].split("/")[1]: f'{base}/{ig["path"]}' for ig in cfg["igs"]}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    repos = candidates(portfolio, token)
    out, skipped = [], {}
    for repo in sorted(repos):
        if repo.split("/")[1] in cat.get("exclude", []):
            skipped[repo] = "excluded in sites.json"
            continue
        e, why = entry(repo, repos[repo], cat, portfolio, hosted)
        if e:
            out.append(e)
        else:
            skipped[repo] = why
    pubs = []
    for lv, lib in libraries(portfolio):
        if "library" in lib["source"]:
            for e in iris_publications(lib["source"]["library"]):
                e["portfolioLevel"], e["library"] = lv["id"], lib["id"]
                pubs.append(e)
    out += pubs
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump({"portfolio": {k: portfolio.get(k) for k in ("id", "title", "description")},
                   "entries": out, "skipped": skipped}, fh, indent=2, ensure_ascii=False)
    print(f"catalogue: {len(out)} listed ({len(pubs)} L1 publications), {len(skipped)} skipped")
    for r, why in sorted(skipped.items()):
        print(f"  skipped {r}: {why}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
