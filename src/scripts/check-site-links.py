#!/usr/bin/env python3
"""Check internal links and #fragments in the built docs site.

`zensical build --strict` checks Markdown links between pages, but not `#anchor`
fragments, and not links written in raw HTML (iframes, diagram boxes, the
DuckDB console, presentations). This script fills that gap by checking the
*built* site.

For every `.html` file under the site directory (pages and `assets/**/*.html`),
every internal `href` / `src` / `xlink:href` / `srcset` / `poster` / `data` URL
is resolved against that file:

  * the target file must exist (a directory URL resolves to its `index.html`);
  * a `#fragment` must match an `id` or `name` attribute in the target page.

External URLs (any scheme such as http/https/mailto/data/javascript, or a
`//host` URL) are skipped, as are unrendered Jinja expressions (the theme
override templates under docs/overrides/ are copied into site/ verbatim). Links are normally relative; a root-absolute path
(`/clinvar-gkm/...`) is resolved by stripping the site's base path, which is
read from `site_url` in `zensical.toml` (or given with `--base-path`). A
root-absolute path outside the base path is reported, since it would 404 in
production.

Usage:
    zensical build --clean --strict
    python src/scripts/check-site-links.py            # checks ./site
    python src/scripts/check-site-links.py site --base-path /clinvar-gkm/

Exits 1 and lists every broken link if any are found. Stdlib only.
"""

import argparse
import os
import sys
import time
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

URL_ATTRS = {"href", "src", "xlink:href", "poster", "data"}
# Fragments a browser resolves without a matching element (HTML spec: "top").
IMPLICIT_FRAGMENTS = {"", "top"}


class PageParser(HTMLParser):
    """Collect element ids/names and outgoing URLs (with line numbers)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.urls = []  # (line, url)

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        for key, value in attrs:
            if value is None:
                continue
            if key in ("id", "name"):
                self.ids.add(value)
            elif key in URL_ATTRS:
                self.urls.append((line, value.strip()))
            elif key == "srcset":
                for candidate in value.split(","):
                    parts = candidate.split()
                    if parts:
                        self.urls.append((line, parts[0]))

    handle_startendtag = handle_starttag


def read_base_path(config_path):
    """Return the URL path of `site_url` in zensical.toml, or '/' if unavailable."""
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        return "/"
    try:
        with open(config_path, "rb") as fh:
            site_url = tomllib.load(fh).get("project", {}).get("site_url", "")
    except (OSError, ValueError):
        return "/"
    path = urlsplit(site_url).path or "/"
    return path if path.endswith("/") else path + "/"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("site", nargs="?", default="site", help="built site directory (default: site)")
    ap.add_argument(
        "--base-path",
        help="URL path the site is served under, e.g. /clinvar-gkm/ "
        "(default: from site_url in --config)",
    )
    ap.add_argument("--config", default="zensical.toml", help="Zensical config (default: zensical.toml)")
    args = ap.parse_args()

    start = time.monotonic()
    site = os.path.realpath(args.site)
    if not os.path.isdir(site):
        sys.exit(f"error: site directory not found: {args.site} (run `zensical build` first)")
    base_path = args.base_path or read_base_path(args.config)
    if not base_path.startswith("/"):
        base_path = "/" + base_path
    if not base_path.endswith("/"):
        base_path += "/"

    pages = []
    for root, _dirs, files in os.walk(site):
        pages.extend(os.path.join(root, f) for f in files if f.endswith(".html"))
    pages.sort()

    cache = {}

    def parse(path):
        if path not in cache:
            parser = PageParser()
            with open(path, encoding="utf-8", errors="replace") as fh:
                parser.feed(fh.read())
            parser.close()
            cache[path] = parser
        return cache[path]

    broken = []  # (source rel path, line, url, reason)
    checked = 0
    for page in pages:
        for line, url in parse(page).urls:
            parts = urlsplit(url)
            if parts.scheme or parts.netloc or url.startswith("//"):
                continue  # external
            if "{{" in url or "{%" in url:
                continue  # unrendered template source (theme overrides copied into site/)
            path = unquote(parts.path)
            fragment = unquote(parts.fragment)
            checked += 1

            if not path:
                target = page
            elif path.startswith("/"):
                if not (path + "/").startswith(base_path):
                    broken.append((page, line, url, f"absolute path outside base path {base_path}"))
                    continue
                target = os.path.join(site, path[len(base_path):])
            else:
                target = os.path.join(os.path.dirname(page), path)
            target = os.path.normpath(target)

            if target != site and not target.startswith(site + os.sep):
                broken.append((page, line, url, "resolves outside the site directory"))
                continue
            if os.path.isdir(target):
                target = os.path.join(target, "index.html")
            if not os.path.isfile(target):
                broken.append((page, line, url, f"missing file {os.path.relpath(target, site)}"))
                continue
            if fragment in IMPLICIT_FRAGMENTS or not target.endswith(".html"):
                continue
            if fragment not in parse(target).ids:
                broken.append((page, line, url, f"no id/name '{fragment}' in {os.path.relpath(target, site)}"))

    elapsed = time.monotonic() - start
    for page, line, url, reason in broken:
        print(f"{os.path.relpath(page, site)}:{line}: {url}  ->  {reason}")
    status = "FAIL" if broken else "OK"
    print(
        f"{status}: {len(pages)} pages, {checked} internal links checked, "
        f"{len(broken)} broken ({elapsed:.1f}s, base path {base_path})"
    )
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
