#!/usr/bin/env python3
"""Compose the merged just-the-docs site from each IG's built docs site.

    python3 scripts/compose.py --sites sites.json --src <dir> --out _site [--report report.json]

<src>/<path>/ holds each IG's built site as published (its gh-pages main
build). The script:

1. copies each IG to <out>/<path>/, leaving out the `exclude` prefixes
   (previews, branch copies, ast-data);
2. finds asset directories (under assets/) that are byte-identical in two or
   more IGs, moves one copy to <out>/_shared/<hash>/<dir>/ and rewrites the
   references in each IG's text files (html, js, css, json, ...) to the shared
   copy, as site-absolute URLs under `base`;
3. points each page's rail Home at this site's landing page (data-fa-home);
4. writes <out>/index.html, the publications table (scripts/landing.py), and a report of what it shared.

Only whole directories are shared, so files inside a shared directory keep
finding each other by relative path.
"""
import argparse
import hashlib
import html
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import landing  # noqa: E402
from collections import defaultdict

TEXT = (".html", ".htm", ".js", ".mjs", ".css", ".json", ".jsonld", ".svg", ".xml", ".txt", ".webmanifest")


def files_under(root):
    for d, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(d, f)
            yield os.path.relpath(p, root).replace(os.sep, "/")


def copy_ig(src, dst, exclude):
    n = 0
    for rel in files_under(src):
        if rel.startswith(".git/") or any(rel.startswith(e) for e in exclude):
            continue
        to = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(to), exist_ok=True)
        shutil.copy2(os.path.join(src, rel), to)
        n += 1
    return n


def dir_hashes(site):
    """sha256 of every directory under assets/, over its sorted (relative path, file hash) list."""
    root = os.path.join(site, "assets")
    if not os.path.isdir(root):
        return {}
    file_hash = {}
    for rel in files_under(root):
        with open(os.path.join(root, rel), "rb") as fh:
            file_hash[rel] = hashlib.sha256(fh.read()).hexdigest()
    by_dir = defaultdict(list)
    ig = os.path.basename(os.path.normpath(site))
    for rel, h in file_hash.items():
        parts = rel.split("/")
        for i in range(1, len(parts)):
            d = "/".join(parts[:i])
            by_dir[d].append(("/".join(parts[i:]), h))
            if rel.endswith(TEXT):
                TEXT_IN_DIR[(ig, d)] = True
    out = {}
    for d, entries in by_dir.items():
        m = hashlib.sha256()
        for rel, h in sorted(entries):
            m.update(f"{rel}\0{h}\n".encode())
        out[d] = (m.hexdigest()[:16], len(entries), sum(os.path.getsize(os.path.join(root, d, r)) for r, _ in entries))
    return out


VERSION = re.compile(r"^v?\d+(\.\d+)+")


def shareable(d, hashes_by_ig):
    """A directory that can move without breaking relative references INTO or OUT OF it:
    a whole asset package (assets/<name>), a whole versioned package (assets/<name>/<version>),
    or a directory holding no text files (images, fonts, wasm), which reference nothing."""
    parts = d.split("/")
    if len(parts) == 1 or (len(parts) == 2 and VERSION.match(parts[1])):
        return True
    return not any(TEXT_IN_DIR.get((ig, d)) for ig in hashes_by_ig)


TEXT_IN_DIR = {}


def choose_shared(hashes_by_ig):
    """Maximal asset directories identical in at least two IGs: {dir: hash}."""
    count = defaultdict(set)
    for ig, hs in hashes_by_ig.items():
        for d, (h, _, _) in hs.items():
            count[(d, h)].add(ig)
    candidates = {(d, h) for (d, h), igs in count.items() if len(igs) >= 2 and shareable(d, hashes_by_ig)}
    chosen = {}
    for d, h in sorted(candidates, key=lambda x: x[0].count("/")):
        if any(d.startswith(p + "/") for p in chosen):
            continue
        chosen[d] = h
    return chosen


def rewrite_refs(site, ig_path, shared, base):
    """Point each reference to a shared directory at its shared copy. Returns the number of files changed."""
    if not shared:
        return 0
    alts = "|".join(re.escape(d) for d in sorted(shared, key=len, reverse=True))
    # ../../assets/<dir>/  ./assets/<dir>/  assets/<dir>/  /<base>/<ig>/assets/<dir>/
    pat = re.compile(r"(?:(?<=[\"'(=\s,])|^)((?:\.\./)+|\./|" + re.escape(f"{base}/{ig_path}/") + r")?assets/(" + alts + r")/", re.M)
    changed = 0
    for rel in files_under(site):
        if not rel.endswith(TEXT) or rel.startswith("assets/") and any(rel.startswith(f"assets/{d}/") for d in shared):
            continue
        p = os.path.join(site, rel)
        try:
            with open(p, encoding="utf-8") as fh:
                t = fh.read()
        except UnicodeDecodeError:
            continue
        n = pat.sub(lambda m: f"{base}/_shared/{shared[m.group(2)]}/{m.group(2)}/", t)
        if n != t:
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(n)
            changed += 1
    return changed


RAIL_BLOCK = re.compile(r'(<script type="application/json" id="fa-rail" data-fa-root="[^"]*" data-fa-to-root="[^"]*")(?: data-fa-home="[^"]*")?>')


def set_rail_home(site, home):
    """Point each page's rail Home at the merged site's landing page.

    Every IG here is a subgraph of this site's KG (owner, 2026-11-10), so the
    rail's header link goes to `home`, not to the IG's own root. The rail reads
    `data-fa-home` on its `#fa-rail` block (cat-harness-tools `RailPage.home`);
    an IG built before that keeps its own home until it is re-pinned.
    Returns the number of pages changed."""
    changed = 0
    for rel in files_under(site):
        if not rel.endswith((".html", ".htm")):
            continue
        p = os.path.join(site, rel)
        try:
            with open(p, encoding="utf-8") as fh:
                t = fh.read()
        except UnicodeDecodeError:
            continue
        n = RAIL_BLOCK.sub(lambda m: f'{m.group(1)} data-fa-home="{html.escape(home, quote=True)}">', t)
        if n != t:
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(n)
            changed += 1
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", required=True)
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--report")
    ap.add_argument("--catalog", help="landing-page catalogue from scripts/catalog.py")
    a = ap.parse_args()
    cfg = json.load(open(a.sites))
    base = cfg.get("base", "").rstrip("/")
    exclude = cfg.get("exclude", [])
    shutil.rmtree(a.out, ignore_errors=True)
    os.makedirs(a.out)
    report = {"igs": {}, "shared": []}
    for ig in cfg["igs"]:
        n = copy_ig(os.path.join(a.src, ig["path"]), os.path.join(a.out, ig["path"]), exclude)
        report["igs"][ig["path"]] = {"files": n}
    hashes = {ig["path"]: dir_hashes(os.path.join(a.out, ig["path"])) for ig in cfg["igs"]}
    chosen = choose_shared(hashes)
    saved = 0
    for d, h in sorted(chosen.items()):
        target = os.path.join(a.out, "_shared", h, d)
        users = [ig for ig, hs in hashes.items() if hs.get(d, (None,))[0] == h]
        first = os.path.join(a.out, users[0], "assets", d)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copytree(first, target)
        size = hashes[users[0]][d][2]
        for ig in users:
            shutil.rmtree(os.path.join(a.out, ig, "assets", d))
        saved += size * (len(users) - 1)
        report["shared"].append({"dir": f"assets/{d}", "hash": h, "bytes": size, "igs": users})
    for ig in cfg["igs"]:
        mine = {d: h for d, h in chosen.items() if hashes[ig["path"]].get(d, (None,))[0] == h}
        report["igs"][ig["path"]]["rewritten_files"] = rewrite_refs(os.path.join(a.out, ig["path"]), ig["path"], mine, base)
        report["igs"][ig["path"]]["rail_home_pages"] = set_rail_home(os.path.join(a.out, ig["path"]), f"{base}/")
    with open(os.path.join(a.out, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(landing.render(cfg, json.load(open(a.catalog, encoding="utf-8"))["entries"] if a.catalog else None))
    open(os.path.join(a.out, ".nojekyll"), "w").close()
    total = sum(os.path.getsize(os.path.join(a.out, r)) for r in files_under(a.out))
    report["bytes_total"] = total
    report["bytes_saved_by_sharing"] = saved
    if a.report:
        json.dump(report, open(a.report, "w"), indent=2)
    print(f"composed {len(cfg['igs'])} IG(s): {total/1e6:.1f} MB; {len(chosen)} shared asset dir(s) saved {saved/1e6:.1f} MB")
    for ig, r in report["igs"].items():
        print(f"  {ig}: {r['files']} files, {r['rewritten_files']} rewritten, {r['rail_home_pages']} rail homes set")
    return 0


if __name__ == "__main__":
    sys.exit(main())
