#!/bin/bash
# Validate a bundle strictly with the GA4GH gkm-toolkit (validate-bundle.py), in an environment uv builds and caches.
#
# Usage: ./validate-bundle.sh <bundle.json.gz> [--workers N]
#        ./validate-bundle.sh --check-setup
#
# --check-setup only confirms that uv, the toolkit and the schema tree are ready, so a release can find out at the
# start, not hours in.
set -o errexit
set -o nounset
set -o pipefail

[[ $# -ge 1 ]] || { echo "Usage: $0 <bundle.json.gz> [--workers N] | --check-setup" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

command -v uv >/dev/null || { echo "ERROR: uv is not on PATH; it runs the bundle validator (brew install uv)" >&2; exit 1; }

# schema/ links into the va-spec submodule, which a new worktree does not have. Without it every record would fail.
if [[ -n "$(find -L "${REPO_ROOT}/schema" -type l 2>/dev/null || true)" ]]; then
  echo "ERROR: ${REPO_ROOT}/schema has broken links; run: git -C ${REPO_ROOT} submodule update --init --recursive" >&2
  exit 1
fi

TOOLKIT=(uv run --no-project --quiet --python 3.12 --prerelease=allow --with ga4gh.gkm==0.4.0 --with ijson)

if [[ "$1" == "--check-setup" ]]; then
  "${TOOLKIT[@]}" python -c 'import ga4gh.gkm.bundles.schema_validation, ijson, referencing' || {
    echo "ERROR: could not build the bundle validator's environment with uv" >&2
    exit 1
  }
  exit 0
fi

"${TOOLKIT[@]}" python "${SCRIPT_DIR}/validate-bundle.py" "$1" "${REPO_ROOT}" "${@:2}"
