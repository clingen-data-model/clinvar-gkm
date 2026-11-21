#!/bin/bash
# Validate a bundle strictly, every record, in an environment uv builds and caches. Two engines run the same check
# (same bundle schema, same schema/ registry, same per-record document, Draft 2020-12, formats not asserted):
#
#   rs (default)       validate-bundle-rs.py: jsonschema-rs. The validator of record: it gates every published bundle,
#                      full and delta (a full takes minutes). It reads only the assembler's one-record-per-line layout
#                      and stops on any other.
#   toolkit            validate-bundle.py: the official GA4GH gkm-toolkit (ga4gh.gkm validate_bundle_schema on
#                      python-jsonschema). By hand only: on the 1.2.0 profiles it checks about 24 records/s per vCPU
#                      (about 17 h on 64 vCPUs for a full), because python-jsonschema re-evaluates every allOf/$ref
#                      layer for each unevaluatedProperties; jsonschema-rs does not.
#
# Usage: ./validate-bundle.sh <bundle.json.gz> [--engine toolkit|rs] [--workers N] [--chunk N] [--max-print N]
#        ./validate-bundle.sh --check-setup [--engine toolkit|rs]
#
# --check-setup only confirms that uv, the engine's environment and the schema tree are ready, so a release can find
# out at the start, not hours in. Without --engine it checks both engines.
set -o errexit
set -o nounset
set -o pipefail

USAGE="Usage: $0 <bundle.json.gz> [--engine toolkit|rs] [--workers N] | --check-setup [--engine toolkit|rs]"
[[ $# -ge 1 ]] || { echo "${USAGE}" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

CHECK_SETUP=false
BUNDLE=""
if [[ "$1" == "--check-setup" ]]; then CHECK_SETUP=true; else BUNDLE="$1"; fi
shift
ENGINE=""
PASS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --engine) [[ $# -ge 2 ]] || { echo "${USAGE}" >&2; exit 1; }; ENGINE="$2"; shift 2 ;;
    --engine=*) ENGINE="${1#--engine=}"; shift ;;
    *) PASS+=("$1"); shift ;;
  esac
done
case "${ENGINE}" in
  ""|toolkit|rs) ;;
  *) echo "ERROR: --engine must be toolkit or rs, got '${ENGINE}'" >&2; exit 1 ;;
esac
if $CHECK_SETUP && [[ ${#PASS[@]} -gt 0 ]]; then echo "${USAGE}" >&2; exit 1; fi

command -v uv >/dev/null || { echo "ERROR: uv is not on PATH; it runs the bundle validator (brew install uv)" >&2; exit 1; }

# schema/ links into the va-spec submodule, which a new worktree does not have. Without it every record would fail.
if [[ -n "$(find -L "${REPO_ROOT}/schema" -type l 2>/dev/null || true)" ]]; then
  echo "ERROR: ${REPO_ROOT}/schema has broken links; run: git -C ${REPO_ROOT} submodule update --init --recursive" >&2
  exit 1
fi

TOOLKIT_VERSION="0.4.0"
RS_VERSION="0.61.1"
TOOLKIT=(uv run --no-project --quiet --python 3.12 --prerelease=allow --with "ga4gh.gkm==${TOOLKIT_VERSION}" --with ijson)
RS=(uv run --no-project --quiet --python 3.12 --with "jsonschema-rs==${RS_VERSION}" --with orjson)

if $CHECK_SETUP; then
  if [[ "${ENGINE}" != "rs" ]]; then
    "${TOOLKIT[@]}" python -c 'import ga4gh.gkm.bundles.schema_validation, ijson, referencing' || {
      echo "ERROR: could not build the toolkit engine's environment with uv" >&2
      exit 1
    }
  fi
  if [[ "${ENGINE}" != "toolkit" ]]; then
    "${RS[@]}" python -c 'import jsonschema_rs, orjson' || {
      echo "ERROR: could not build the rs engine's environment with uv" >&2
      exit 1
    }
  fi
  exit 0
fi

if [[ "${ENGINE}" == "toolkit" ]]; then
  echo "engine: toolkit (ga4gh.gkm ${TOOLKIT_VERSION}, the GA4GH gkm-toolkit)"
  "${TOOLKIT[@]}" python "${SCRIPT_DIR}/validate-bundle.py" "${BUNDLE}" "${REPO_ROOT}" ${PASS[@]+"${PASS[@]}"}
else
  echo "engine: rs (jsonschema-rs ${RS_VERSION})"
  "${RS[@]}" python "${SCRIPT_DIR}/validate-bundle-rs.py" "${BUNDLE}" "${REPO_ROOT}" ${PASS[@]+"${PASS[@]}"}
fi
