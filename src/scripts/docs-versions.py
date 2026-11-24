#!/usr/bin/env python3
"""Maintain the root of the versioned docs site (ADR 0011).

The gh-pages branch holds one folder per release line (`1.1/`, `1.2/`, ...)
and a few root files this script writes:

  versions.json  the version list the theme's version selector reads (mike
                 format). The highest release line gets the alias `latest`,
                 so a patch to an older line can't take `latest` from a newer
                 one. A version that isn't a release line (`dev`, retired
                 2026-11-20) is dropped, and its folder removed.
  index.html     redirects the site root to the latest release, keeping the
                 query and #fragment.
  404.html       GitHub Pages serves it for every missing path. An unversioned
                 link (`/clinvar-gkm/reference/changelog/`, every URL from
                 before versioned docs) goes to the same page in the latest
                 release, or to its home when the page isn't there;
                 `/clinvar-gkm/latest/...` and `/clinvar-gkm/dev/...` (links to
                 the retired dev docs) go to the same page in the latest
                 release, or its home; a missing page inside a version goes to
                 that version's home. When the site is at the domain root
                 (ADR 0013), a path that still starts with the former base
                 path `/clinvar-gkm/` goes to the same path without it.

Anything else at the root is removed (the unversioned site that predates
versioned docs), except `CNAME`, `.nojekyll` and `.git`.

Usage:
    python src/scripts/docs-versions.py PAGES_DIR [--add VERSION ...] [--base-path /clinvar-gkm/]

`--add` registers a version whose folder is already in PAGES_DIR. The base
path defaults to the URL path of `site_url` in zensical.toml. Stdlib only.
"""

import argparse
import html
import json
import re
import shutil
import sys
from pathlib import Path

RELEASE = re.compile(r"^(\d+)\.(\d+)$")
KEEP = {"versions.json", "index.html", "404.html", "CNAME", ".nojekyll", ".git"}
# The base path the site was served under before it moved to the root of clinvar-gkm.org (ADR 0013).
FORMER_BASE = "/clinvar-gkm/"


def read_base_path(config_path):
    import tomllib
    from urllib.parse import urlsplit

    with open(config_path, "rb") as fh:
        url = tomllib.load(fh)["project"]["site_url"]
    path = urlsplit(url).path or "/"
    return path if path.endswith("/") else path + "/"


def update_versions(versions, add, pages):
    for version in add:
        if not RELEASE.match(version):
            sys.exit(f"error: version must be a release line X.Y, got {version!r}")
    known = {}
    for v in versions:
        if RELEASE.match(v["version"]):
            known[v["version"]] = v
        else:
            print(f"dropping {v['version']!r} from versions.json: not a release line", file=sys.stderr)
    for version in add:
        known.setdefault(version, {"version": version, "title": version, "aliases": []})
    for version in list(known):
        if not (pages / version).is_dir():
            print(f"warning: dropping {version!r} from versions.json: no {version}/ folder", file=sys.stderr)
            del known[version]

    releases = sorted(
        (v for v in known if RELEASE.match(v)),
        key=lambda v: tuple(int(p) for p in v.split(".")),
        reverse=True,
    )
    for entry in known.values():
        entry["aliases"] = []
    if releases:
        known[releases[0]]["aliases"] = ["latest"]
    # Newest release first.
    return [known[v] for v in releases]


INDEX = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Redirecting to the ClinVar-GKM docs</title>
<link rel="canonical" href="{target}">
<script>location.replace({target_js} + location.search + location.hash);</script>
<noscript><meta http-equiv="refresh" content="0; url={target}"></noscript>
</head>
<body>
<p>Redirecting to <a href="{target}">the ClinVar-GKM docs ({title})</a>.</p>
</body>
</html>
"""

NOT_FOUND = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ClinVar-GKM docs</title>
<script>
(function () {{
  var BASE = {base_js}, LATEST = {latest_js}, VERSIONS = {versions_js}, FORMER = {former_js};
  var home = BASE + LATEST + "/";
  var path = location.pathname, tail = location.search + location.hash;
  // A link from before the move to the domain root (ADR 0013): the same path without the former base path.
  if (FORMER && (path + "/").indexOf(FORMER) === 0) {{ location.replace(BASE + path.slice(FORMER.length) + tail); return; }}
  if (path.indexOf(BASE) !== 0) {{ location.replace(home); return; }}
  var rest = path.slice(BASE.length), first = rest.split("/")[0];
  if (first === "latest") {{ location.replace(home + rest.slice(first.length + 1) + tail); return; }}
  if (VERSIONS.indexOf(first) >= 0) {{ location.replace(BASE + first + "/"); return; }}
  // The retired dev docs: the same page in the latest release, or its home.
  if (first === "dev") rest = rest.slice(first.length + 1);
  var target = home + rest;
  fetch(target, {{ method: "HEAD" }})
    .then(function (r) {{ location.replace(r.ok ? target + tail : home); }})
    .catch(function () {{ location.replace(home); }});
}})();
</script>
</head>
<body>
<p>Page not found. Redirecting to <a href="{home}">the ClinVar-GKM docs ({title})</a>.</p>
</body>
</html>
"""


def write_root(pages, versions, base):
    # Redirect to the latest release; before any release is published, to the first entry.
    default = next((v for v in versions if "latest" in v["aliases"]), versions[0] if versions else None)
    if default is None:
        sys.exit("error: no versions to publish")
    home = f"{base}{default['version']}/"
    title = html.escape(default["title"])
    (pages / "index.html").write_text(
        INDEX.format(target=html.escape(home), target_js=json.dumps(home), title=title), encoding="utf-8"
    )
    (pages / "404.html").write_text(
        NOT_FOUND.format(
            base_js=json.dumps(base),
            former_js=json.dumps(FORMER_BASE if base == "/" else None),
            latest_js=json.dumps(default["version"]),
            versions_js=json.dumps([v["version"] for v in versions]),
            home=html.escape(home),
            title=title,
        ),
        encoding="utf-8",
    )
    (pages / "versions.json").write_text(json.dumps(versions, indent=2) + "\n", encoding="utf-8")
    (pages / ".nojekyll").touch()


def prune(pages, versions):
    keep = KEEP | {v["version"] for v in versions}
    for entry in sorted(pages.iterdir()):
        if entry.name in keep:
            continue
        print(f"removing unversioned {entry.name}")
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pages", type=Path, help="checkout of the gh-pages branch")
    ap.add_argument("--add", action="append", default=[], metavar="VERSION", help="register a version folder")
    ap.add_argument("--base-path", help="site URL path (default: from site_url in --config)")
    ap.add_argument("--config", default="zensical.toml", help="Zensical config (default: zensical.toml)")
    args = ap.parse_args()

    base = args.base_path or read_base_path(args.config)
    if not base.startswith("/") or not base.endswith("/"):
        sys.exit(f"error: base path must start and end with '/', got {base!r}")

    vfile = args.pages / "versions.json"
    versions = json.loads(vfile.read_text(encoding="utf-8")) if vfile.exists() else []
    versions = update_versions(versions, args.add, args.pages)
    write_root(args.pages, versions, base)
    prune(args.pages, versions)
    latest = next((v["version"] for v in versions if "latest" in v["aliases"]), "none")
    print(f"versions: {', '.join(v['version'] for v in versions)}; latest: {latest}")


if __name__ == "__main__":
    main()
