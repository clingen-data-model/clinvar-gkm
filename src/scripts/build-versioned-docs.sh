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
#   - zensical.toml: site_url becomes <site_url of this checkout><version>/, and the
#     [project.extra.version] table is added when the ref's config lacks it;
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
docs/assets/js/versions.js
docs/stylesheets/versions.css"

SITE_URL=$("$PYTHON" -c 'import sys, tomllib; print(tomllib.load(open(sys.argv[1], "rb"))["project"]["site_url"])' \
  "$REPO/zensical.toml")
case "$SITE_URL" in */) ;; *) SITE_URL="$SITE_URL/" ;; esac
VERSION_URL="$SITE_URL$VERSION/"

TMP=$(mktemp -d "${TMPDIR:-/tmp}/versioned-docs.XXXXXX")
trap 'rm -rf "${TMP:?}"' EXIT

echo "== Building docs version '$VERSION' from '$REF' (site_url $VERSION_URL)"
git -C "$REPO" archive --format=tar "$REF" | tar -x -C "$TMP"

for f in $OVERLAY; do
  mkdir -p "$TMP/$(dirname "$f")"
  cp "$REPO/$f" "$TMP/$f"
done

"$PYTHON" - "$TMP/zensical.toml" "$VERSION_URL" <<'EOF'
import re, sys
path, url = sys.argv[1:]
text = open(path, encoding="utf-8").read()
text, n = re.subn(r'(?m)^site_url\s*=.*$', f'site_url = "{url}"', text, count=1)
if n != 1:
    sys.exit(f"error: no site_url line in {path}")
if "[project.extra.version]" not in text:
    text = text.rstrip("\n") + '\n\n[project.extra.version]\nprovider = "mike"\nalias = true\n'
open(path, "w", encoding="utf-8").write(text)
EOF

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
