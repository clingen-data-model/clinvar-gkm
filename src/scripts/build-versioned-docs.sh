#!/usr/bin/env bash
# Build one version of the docs site (ADR 0011).
#
# Usage: build-versioned-docs.sh <ref> <version> <out_dir>
#
#   <ref>      git ref whose docs to build: a release tag (1.1.0) or HEAD/main for dev
#   <version>  the docs version to build it as: "dev" or a release line "X.Y"
#   <out_dir>  where the built site goes (replaced); publish it as <version>/ at the
#              gh-pages root
#
# The ref's tree is exported to a scratch folder (the ref itself is never changed), then
# the files this feature owns are overlaid from THIS checkout, so an older release
# tag built before versioned docs existed still gets the version selector, the
# version notice and the colours:
#   - OVERLAY (below): template overrides, versions.js and versions.css;
#   - src/scripts/docs-ref-patches/<ref>/*.patch: content fixes for that ref's docs,
#     such as release notes written after the tag (1.1.0's changelog lacks its own
#     1.1.0 section);
#   - zensical.toml: site_url becomes <site_url of this checkout><version>/, the
#     [project.extra.version] table is added when the ref's config lacks it, and
#     [project.extra.source] names the ref the version was built from (`main` for dev,
#     else <ref>), which the header's repository widget shows and links; edit_uri
#     points at the same ref;
#   - links in the pages to this repository's files on `main` (/blob/main/...,
#     /tree/main/..., /raw/main/...) are rewritten to <ref> for a release version
#     (pin-repo-links.py; a path the ref doesn't have stays on main);
#   - the Roadmap table is regenerated from GitHub Discussions with this checkout's
#     generate-roadmap.py (non-fatal: without GH_TOKEN or on an API error the ref's
#     committed table stays).
# Then `zensical build --clean --strict` and check-site-links.py run on the result.
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

if ! [[ "$VERSION" =~ ^(dev|[0-9]+\.[0-9]+)$ ]]; then
  echo "error: version must be 'dev' or a release line like 1.1 (got '$VERSION')" >&2
  exit 2
fi

REPO=$(cd "$(dirname "$0")/../.." && pwd)
OVERLAY="docs/overrides/main.html
docs/overrides/404.html
docs/overrides/partials/header.html
docs/overrides/partials/source.html
docs/assets/js/versions.js
docs/stylesheets/versions.css"

SITE_URL=$("$PYTHON" -c 'import sys, tomllib; print(tomllib.load(open(sys.argv[1], "rb"))["project"]["site_url"])' \
  "$REPO/zensical.toml")
case "$SITE_URL" in */) ;; *) SITE_URL="$SITE_URL/" ;; esac
VERSION_URL="$SITE_URL$VERSION/"

# The ref the version's pages show and link to: dev is main (labelled with the commit it
# was built from); a release is the tag (or other ref) it was built from.
if [ "$VERSION" = "dev" ]; then
  SOURCE_REF=main
  SOURCE_LABEL="main ($(git -C "$REPO" rev-parse --short "$REF^{commit}"))"
else
  SOURCE_REF=$REF
  SOURCE_LABEL=$REF
fi

TMP=$(mktemp -d "${TMPDIR:-/tmp}/versioned-docs.XXXXXX")
trap 'rm -rf "${TMP:?}"' EXIT

echo "== Building docs version '$VERSION' from '$REF' (site_url $VERSION_URL, source $SOURCE_LABEL)"
git -C "$REPO" archive --format=tar "$REF" | tar -x -C "$TMP"

for f in $OVERLAY; do
  mkdir -p "$TMP/$(dirname "$f")"
  cp "$REPO/$f" "$TMP/$f"
done

# Per-ref content fixes: src/scripts/docs-ref-patches/<ref>/*.patch are applied (in name
# order) to that ref's exported tree, e.g. to add release notes written after the tag was
# cut. A patch that doesn't apply stops the build.
PATCHES="$REPO/src/scripts/docs-ref-patches/$REF"
if [ -d "$PATCHES" ]; then
  for p in "$PATCHES"/*.patch; do
    [ -e "$p" ] || continue
    echo "== Applying $(basename "$p") to $REF"
    (cd "$TMP" && git apply --verbose "$p")
  done
fi

"$PYTHON" - "$TMP/zensical.toml" "$VERSION_URL" "$SOURCE_REF" "$SOURCE_LABEL" <<'EOF'
import json, re, sys
path, url, ref, label = sys.argv[1:]
text = open(path, encoding="utf-8").read()
text, n = re.subn(r'(?m)^site_url\s*=.*$', f'site_url = "{url}"', text, count=1)
if n != 1:
    sys.exit(f"error: no site_url line in {path}")
edit = "edit/main/docs/" if ref == "main" else f"blob/{ref}/docs/"  # a tag can't be edited
text = re.sub(r'(?m)^edit_uri\s*=.*$', f'edit_uri = "{edit}"', text, count=1)
if "[project.extra.version]" not in text:
    text = text.rstrip("\n") + '\n\n[project.extra.version]\nprovider = "mike"\nalias = true\n'
if "[project.extra.source]" in text:
    sys.exit(f"error: {path} already has [project.extra.source]")
text = text.rstrip("\n") + f'\n\n[project.extra.source]\nref = {json.dumps(ref)}\nlabel = {json.dumps(label)}\n'
open(path, "w", encoding="utf-8").write(text)
EOF

if [ "$SOURCE_REF" != "main" ]; then
  "$PYTHON" "$REPO/src/scripts/pin-repo-links.py" "$TMP/docs" "$REF" --repo "$REPO"
fi

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
