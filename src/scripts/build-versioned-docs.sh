#!/usr/bin/env bash
# Build one version of the docs site (ADR 0011).
#
# Usage: build-versioned-docs.sh <ref> <version> <out_dir>
#
#   <ref>      git ref whose docs to build: a release tag (1.1.0), or a commit
#   <version>  the docs version to build it as: a release line "X.Y"
#   <out_dir>  where the built site goes (replaced); publish it as <version>/ at the
#              gh-pages root
#
# The ref's tree is exported to a scratch folder (the ref itself is never changed), then
# the files this feature owns are overlaid from THIS checkout, so an older release
# tag built before versioned docs existed still gets the version selector, the
# version notice and the colours:
#   - OVERLAY (below): template overrides, versions.js and versions.css, and the
#     release browser (r2-browser.js) and live query console (duckdb-console.html),
#     which pick the data line from the docs version in the page URL, so an older
#     version's download tables and console show its own line;
#   - zensical.toml: site_url becomes <site_url of this checkout><version>/, the
#     [project.extra.version] table is added when the ref's config lacks it, and
#     [project.extra.source] names the release the version shows (<ref>, or the line's
#     label), which the header's repository widget shows and links; edit_uri points at
#     the ref the pages come from;
#   - links in the pages to this repository's files on `main` (/blob/main/...,
#     /tree/main/..., /raw/main/...) are rewritten to the ref the pages come from
#     (pin-repo-links.py; a path the ref doesn't have stays on main);
#   - the Roadmap table is regenerated from GitHub Discussions with this checkout's
#     generate-roadmap.py (non-fatal: without GH_TOKEN or on an API error the ref's
#     committed table stays).
# Then `zensical build --clean --strict` and check-site-links.py run on the result.
#
# A release line listed in docs-line-sources.txt is always built from the source ref
# given there and shown as its label, whatever <ref> is passed: every trigger (release,
# schedule, dispatch) then builds the same docs for that line.
#
# Env: ZENSICAL (default: zensical), PYTHON (default: python3), GH_TOKEN (roadmap).
set -euo pipefail

if [ $# -ne 3 ]; then
  echo "usage: $0 <ref> <version> <out_dir>" >&2
  exit 2
fi
REF=$1
VERSION=$2
OUT=$3
ZENSICAL=${ZENSICAL:-zensical}
PYTHON=${PYTHON:-python3}

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+$ ]]; then
  echo "error: version must be a release line like 1.2 (got '$VERSION')" >&2
  exit 2
fi

REPO=$(cd "$(dirname "$0")/../.." && pwd)
OVERLAY="docs/overrides/main.html
docs/overrides/404.html
docs/overrides/partials/header.html
docs/overrides/partials/source.html
docs/assets/js/versions.js
docs/stylesheets/versions.css
docs/assets/js/r2-browser.js
docs/assets/duckdb-console.html"

SITE_URL=$("$PYTHON" -c 'import sys, tomllib; print(tomllib.load(open(sys.argv[1], "rb"))["project"]["site_url"])' \
  "$REPO/zensical.toml")
case "$SITE_URL" in */) ;; *) SITE_URL="$SITE_URL/" ;; esac
VERSION_URL="$SITE_URL$VERSION/"

# The release the version's header shows and links: the tag it was built from, unless
# docs-line-sources.txt maps its line to another source ref, shown as the line's label.
SOURCE_REF=$REF
while read -r line src label; do
  if [ "$line" = "$VERSION" ]; then
    echo "== $VERSION: building the docs from $src, shown as $label ($REF requested; docs-line-sources.txt)"
    REF=$src
    SOURCE_REF=$label
  fi
done < <(grep -v '^#' "$REPO/src/scripts/docs-line-sources.txt")
SOURCE_LABEL=$SOURCE_REF

TMP=$(mktemp -d "${TMPDIR:-/tmp}/versioned-docs.XXXXXX")
trap 'rm -rf "${TMP:?}"' EXIT

echo "== Building docs version '$VERSION' from '$REF' (site_url $VERSION_URL, source $SOURCE_LABEL)"
git -C "$REPO" archive --format=tar "$REF" | tar -x -C "$TMP"

for f in $OVERLAY; do
  mkdir -p "$TMP/$(dirname "$f")"
  cp "$REPO/$f" "$TMP/$f"
done

"$PYTHON" - "$TMP/zensical.toml" "$VERSION_URL" "$SOURCE_REF" "$SOURCE_LABEL" "$REF" <<'EOF'
import json, re, sys
path, url, ref, label, content = sys.argv[1:]
text = open(path, encoding="utf-8").read()
text, n = re.subn(r'(?m)^site_url\s*=.*$', f'site_url = "{url}"', text, count=1)
if n != 1:
    sys.exit(f"error: no site_url line in {path}")
# a tag can't be edited: view the page source at the ref the pages come from
text = re.sub(r'(?m)^edit_uri\s*=.*$', f'edit_uri = "blob/{content}/docs/"', text, count=1)
if "[project.extra.version]" not in text:
    text = text.rstrip("\n") + '\n\n[project.extra.version]\nprovider = "mike"\nalias = true\n'
if "[project.extra.source]" in text:
    sys.exit(f"error: {path} already has [project.extra.source]")
text = text.rstrip("\n") + f'\n\n[project.extra.source]\nref = {json.dumps(ref)}\nlabel = {json.dumps(label)}\n'
open(path, "w", encoding="utf-8").write(text)
EOF

"$PYTHON" "$REPO/src/scripts/pin-repo-links.py" "$TMP/docs" "$REF" --repo "$REPO"

mkdir -p "$TMP/src/scripts"
cp "$REPO/src/scripts/generate-roadmap.py" "$TMP/src/scripts/generate-roadmap.py"
(cd "$TMP" && "$PYTHON" src/scripts/generate-roadmap.py) \
  || echo "warning: roadmap not regenerated; keeping the committed table" >&2

(cd "$TMP" && "$ZENSICAL" build --clean --strict)
(cd "$TMP" && "$PYTHON" "$REPO/src/scripts/check-site-links.py" site)

rm -rf "${OUT:?}"
mkdir -p "$(dirname "$OUT")"
mv "$TMP/site" "$OUT"
echo "== Built '$VERSION' into $OUT"
