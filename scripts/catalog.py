#!/usr/bin/env python3
"""Build the landing page's catalogue from the repositories themselves.

    python3 scripts/catalog.py --sites sites.json --out catalog.json

Nothing in the table is kept by hand except what no repository holds (a DAK's
cover and its WHO publication link, under `catalog.overrides` in sites.json).
For every repository of `catalog.owner` whose name starts with one of
`catalog.prefixes`:

1. it is HARNESSED when it has an index.lock.json, and PUBLISHED when it has
   a gh-pages branch; only harnessed, published repositories are listed;
2. its layer name is the index.config.json instance read from `.` (smart-ra's
   is dpi-h-ra), and `<name>.json`, its declaration, gives its title and the
   pages it publishes (each directory's `coverage.visualiser`);
3. a folio manifest (folio/<name>/<name>.ts) makes it an L2 DOCUMENT (a DTH,
   smart-base document kinds `dth` / `l2-dth`); else a sushi-config.yaml makes
   it a FHIR IG, whose DAK component pages are read off its `pages:`;
4. `catalog.foundations` lists the shared IGs every guide builds on.

A fork's upstream is `catalog.upstream`/<repo>, with its CI build on
build.fhir.org. The result is a JSON list that scripts/landing.py renders.
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


def entry(repo, info, cat, hosted):
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
        e["section"] = "foundations" if name in cat.get("foundations", []) else "guidelines"
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
    e.update(cat.get("overrides", {}).get(name, {}))
    return e, "listed"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cfg = json.load(open(a.sites, encoding="utf-8"))
    cat = cfg.get("catalog", {})
    base = cfg.get("base", "").rstrip("/")
    hosted = {ig["repo"].split("/")[1]: f'{base}/{ig["path"]}' for ig in cfg["igs"]}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    repos = search_repos(cat.get("owner", "litlfred"), cat.get("prefixes", ["smart-", "dth-"]), token)
    out, skipped = [], {}
    for repo in sorted(repos):
        if repo.split("/")[1] in cat.get("exclude", []):
            skipped[repo] = "excluded in sites.json"
            continue
        e, why = entry(repo, repos[repo], cat, hosted)
        if e:
            out.append(e)
        else:
            skipped[repo] = why
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump({"entries": out, "skipped": skipped}, fh, indent=2, ensure_ascii=False)
    print(f"catalogue: {len(out)} listed, {len(skipped)} skipped")
    for r, why in sorted(skipped.items()):
        print(f"  skipped {r}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
