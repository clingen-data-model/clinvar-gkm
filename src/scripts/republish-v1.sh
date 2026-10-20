#!/bin/bash
# republish-v1.sh — runbook driver for the 1.1.0 in-place republish of /v1/ (ADR 0006, ADR 0008):
# the 4 monthly fulls + 00-latest and the 16 deltas are re-published as bundles, and Parquet becomes a
# single latest derived set built from the newest dataset. Run AFTER the 17 datasets are rebuilt and every
# gate in docs/superpowers/plans/2026-10-18-proposition-reorganization.md §6.4 passes. Each step that writes
# to R2 or Cloudflare is a separate, user-confirmed step and honours --dry-run.
#
# Steps, in order:
#   ./republish-v1.sh list
#   ./republish-v1.sh backup                 [--dry-run]  # index.json, v1/index.json, v1/feed.xml -> v1/_backup/pre-1.1.0/
#   ./republish-v1.sh verify-archive                       # archive/1.0.1/MANIFEST.json covers every live bundle (count + sizes)
#   ./republish-v1.sh archive-latest-parquet [--dry-run]  # 1.0.1's latest Parquet -> archive/1.0.1/ + MANIFEST sha256
#   ./republish-v1.sh stage   <target|all|parquet>        # export + assemble (or build Parquet), NO upload (STAGE_DIR)
#   ./republish-v1.sh upload  <target|all|parquet> [--dry-run]
#   ./republish-v1.sh delete-dated-parquet   [--dry-run]  # every dated Parquet object (~52 GB, 440 objects); guarded
#   ./republish-v1.sh index                  [--dry-run]  # regenerate v1/index.json, root manifest, v1/feed.xml
#   ./republish-v1.sh purge                  [--dry-run]  # Cloudflare purge_everything (credentials from CF_ENV_FILE)
#
# <target> is a monthly label (2026-07) or a delta date (2026-07-06); "all" runs fulls (month order) then
# deltas (date order), so each 00-latest ends on the newest; "parquet" is the single latest Parquet set,
# built from LATEST_SOURCE (the newest dataset). The bundle archive of the 1.0.1 generation (archive/1.0.1/,
# MANIFEST.json with sha256) replaces a bundle backup; archive-latest-parquet adds the Parquet set built from
# 1.0.1's latest bundle, and must run before `upload parquet` replaces it (upload refuses otherwise).
# STAGE_DIR (default /tmp): a full is about 4.8 GB, the Parquet set about 12 GB; stage one at a time if short.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STAGE_DIR="${STAGE_DIR:-/tmp}"
export STAGE_DIR

# monthly label | source release date | dataset version (ADR 0002 mapping; matches the published index)
FULLS="
2026-07 2026-06-27 v2_5_0
2026-08 2026-08-04 v2_5_0
2026-09 2026-08-29 v2_6_0
2026-10 2026-09-28 v2_6_0
"
# delta release date | dataset version
DELTAS="
2026-07-06 v2_5_0
2026-07-15 v2_5_0
2026-07-20 v2_5_0
2026-07-27 v2_5_0
2026-08-04 v2_5_0
2026-08-08 v2_5_0
2026-08-16 v2_5_0
2026-08-22 v2_5_0
2026-08-29 v2_6_0
2026-09-05 v2_6_0
2026-09-13 v2_6_0
2026-09-23 v2_6_0
2026-09-28 v2_6_0
2026-10-04 v2_6_0
2026-10-11 v2_6_0
2026-10-18 v2_6_0
"
# The newest dataset: the latest Parquet set is built from it (date version).
LATEST_SOURCE="${LATEST_SOURCE:-2026-10-18 v2_6_0}"

R2_BUCKET="clinvar-gkm"
R2_ENDPOINT="https://09208aa33790838db213a21f630c33e7.r2.cloudflarestorage.com"
R2_PROFILE="r2"
R2_PREFIX="${R2_PREFIX:-v1/}"
BACKUP_PREFIX="${R2_PREFIX}_backup/pre-1.1.0/"
ARCHIVE="${ARCHIVE:-archive/1.0.1/}"
LATEST_PARQUET="${R2_PREFIX}datasets/parquet/00-latest/"
CF_ENV_FILE="${CF_ENV_FILE:-${HOME}/.config/clinvar-gkm/cloudflare.env}"

CMD="${1:-}"; [[ $# -gt 0 ]] && shift
TARGET=""
DRY_RUN=false
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    -*) echo "ERROR: unknown flag '${arg}'" >&2; exit 1 ;;
    *) TARGET="$arg" ;;
  esac
done

usage() { sed -n '2,27p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

fulls_for() { echo "$FULLS" | awk -v t="$1" 'NF==3 && (t=="all" || $1==t)'; }
deltas_for() { echo "$DELTAS" | awk -v t="$1" 'NF==2 && (t=="all" || $1==t)'; }

require_target() {
  [[ -n "$TARGET" ]] || { echo "ERROR: ${CMD} needs a target (see: $0 list)" >&2; exit 1; }
  [[ "$TARGET" == "parquet" ]] && return 0
  if [[ -z "$(fulls_for "$TARGET")$(deltas_for "$TARGET")" ]]; then
    echo "ERROR: unknown target '${TARGET}' (see: $0 list)" >&2; exit 1
  fi
}

aws_r2() { aws --endpoint-url "${R2_ENDPOINT}" --profile "${R2_PROFILE}" "$@"; }
# "SIZE KEY" for every object under a prefix (recursive).
r2_list() { aws_r2 s3 ls "s3://${R2_BUCKET}/$1" --recursive | awk '{print $3, $4}'; }

r2_copy() {   # size-aware server-side copy (.claude/rules/scripts.md): src dest size
  if [[ "$3" -ge 2147483648 ]]; then
    aws_r2 s3 cp "s3://${R2_BUCKET}/$1" "s3://${R2_BUCKET}/$2" --copy-props none --quiet
  else
    aws_r2 s3api copy-object --bucket "${R2_BUCKET}" --key "$2" --copy-source "${R2_BUCKET}/$1" >/dev/null
  fi
}

human() { awk -v b="$1" 'BEGIN { printf "%.1f GB", b / 1e9 }'; }

# --- backup: only the small index/manifest/feed files (bundles are in the archive; Parquet is deleted) ----
backup() {
  local key size
  echo "=== backup: index.json, ${R2_PREFIX}index.json, ${R2_PREFIX}feed.xml -> ${BACKUP_PREFIX} ==="
  for key in index.json "${R2_PREFIX}index.json" "${R2_PREFIX}feed.xml"; do
    size="$(aws_r2 s3api head-object --bucket "${R2_BUCKET}" --key "$key" --query ContentLength --output text)"
    if $DRY_RUN; then echo "  [dry-run] copy ${key} -> ${BACKUP_PREFIX}${key} (${size} B)"; continue; fi
    r2_copy "$key" "${BACKUP_PREFIX}${key}" "$size"
    echo "  ${key} -> ${BACKUP_PREFIX}${key} (${size} B)"
  done
}

# --- verify-archive: every live bundle/manifest/index file is in the archive MANIFEST, same size ----------
verify_archive() {
  local tmp; tmp="$(mktemp -d)"
  aws_r2 s3 cp "s3://${R2_BUCKET}/${ARCHIVE}MANIFEST.json" "${tmp}/MANIFEST.json" --quiet
  r2_list "${R2_PREFIX}" > "${tmp}/live.txt"
  aws_r2 s3api head-object --bucket "${R2_BUCKET}" --key index.json --query ContentLength --output text \
    | awk '{print $1, "index.json"}' >> "${tmp}/live.txt"
  r2_list "${ARCHIVE}" > "${tmp}/archived.txt"
  local rc=0
  python3 - "${tmp}" "${R2_PREFIX}" "${ARCHIVE}" <<'PY' || rc=1
import json, re, sys
tmp, prefix, archive = sys.argv[1:4]
man = json.load(open(f"{tmp}/MANIFEST.json"))
entries = {e["original_key"]: e for e in man["files"]}
archived = {}
for line in open(f"{tmp}/archived.txt"):
    size, key = line.split(None, 1); archived[key.strip()] = int(size)
skip = re.compile(rf"^{re.escape(prefix)}(_backup/|.*\.parquet$|.*/source\.json$|README\.txt$|.*\.sha256$)")
live = {}
for line in open(f"{tmp}/live.txt"):
    size, key = line.split(None, 1); key = key.strip()
    if key == "index.json" or (key.startswith(prefix) and not skip.match(key)):
        live[key] = int(size)
missing = [k for k in live if k not in entries]
size_bad = [k for k in live if k in entries and entries[k]["size"] != live[k]]
obj_bad = [e["archive_key"] for e in man["files"] if archived.get(e["archive_key"]) != e["size"]]
print(f"  MANIFEST: schema_version={man.get('schema_version')} file_count={man.get('file_count')} "
      f"entries={len(man['files'])} total_size={man.get('total_size')}")
print(f"  live files that must be archived (bundles, delta manifests, indexes, feed): {len(live)}")
print(f"  missing from MANIFEST: {len(missing)}   size differs from MANIFEST: {len(size_bad)}   "
      f"archive object missing or wrong size: {len(obj_bad)}")
print(f"  MANIFEST file_count matches entries: {man.get('file_count') == len(man['files'])}")
for k in (missing + size_bad + obj_bad)[:20]: print("   -", k)
sys.exit(1 if (missing or size_bad or obj_bad or man.get("file_count") != len(man["files"])) else 0)
PY
  rm -rf "${tmp}"
  if [[ $rc -eq 0 ]]; then echo "PASS: ${ARCHIVE} holds every live bundle file at its live size."
  else echo "FAIL: the archive is incomplete (see above)" >&2; return 1; fi
}

# --- archive-latest-parquet: keep the Parquet set built from 1.0.1's latest bundle --------------------------
# Server-side copy of every object under v1/datasets/parquet/00-latest/ into the archive, then each archived
# object's sha256 is computed by streaming it (never stored on disk) and added to the archive MANIFEST.json.
# Idempotent: objects already in the MANIFEST at the same size are skipped.
archive_latest_parquet() {
  local tmp; tmp="$(mktemp -d)"
  aws_r2 s3 cp "s3://${R2_BUCKET}/${ARCHIVE}MANIFEST.json" "${tmp}/MANIFEST.json" --quiet
  r2_list "${LATEST_PARQUET}" > "${tmp}/src.txt"
  local n=0 bytes=0 size key dest sha lm
  : > "${tmp}/new.tsv"
  echo "=== archive-latest-parquet: ${LATEST_PARQUET} -> ${ARCHIVE}${LATEST_PARQUET} ==="
  while read -r size key; do
    [[ -n "${key:-}" ]] || continue
    if python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); sys.exit(0 if any(e["original_key"]==sys.argv[2] and e["size"]==int(sys.argv[3]) for e in m["files"]) else 1)' \
        "${tmp}/MANIFEST.json" "$key" "$size"; then
      echo "  already archived: ${key}"; continue
    fi
    dest="${ARCHIVE}${key}"
    n=$((n + 1)); bytes=$((bytes + size))
    if $DRY_RUN; then echo "  [dry-run] copy ${key} -> ${dest} (${size} B), then stream it for sha256"; continue; fi
    lm="$(aws_r2 s3api head-object --bucket "${R2_BUCKET}" --key "$key" --query LastModified --output text)"
    r2_copy "$key" "$dest" "$size"
    sha="$(aws_r2 s3 cp "s3://${R2_BUCKET}/${dest}" - | shasum -a 256 | awk '{print $1}')"
    printf '%s\t%s\t%s\t%s\t%s\n' "$key" "$dest" "$size" "$sha" "$lm" >> "${tmp}/new.tsv"
    echo "  ${key} -> ${dest}  sha256=${sha}"
  done < "${tmp}/src.txt"
  if $DRY_RUN; then echo "  ${n} objects, $(human "$bytes") would be archived."
  else echo "  ${n} objects, $(human "$bytes") archived."; fi
  if ! $DRY_RUN && [[ -s "${tmp}/new.tsv" ]]; then
    python3 - "${tmp}/MANIFEST.json" "${tmp}/new.tsv" <<'PY'
import json, sys
path, tsv = sys.argv[1:3]
m = json.load(open(path))
for line in open(tsv):
    key, dest, size, sha, lm = line.rstrip("\n").split("\t")
    m["files"].append({"original_key": key, "archive_key": dest, "size": int(size), "sha256": sha,
                       "original_last_modified": lm, "schema_version": None})
m["file_count"] = len(m["files"])
m["total_size"] = sum(e["size"] for e in m["files"])
note = "The Parquet set built from this generation's latest bundle (v1/datasets/parquet/00-latest/) is included."
m["notes"] = m["notes"].replace("Parquet not archived", "only the latest Parquet set archived")
if note not in m["notes"]:
    m["notes"] += " " + note
json.dump(m, open(path, "w"), indent=1)
PY
    aws_r2 s3 cp "${tmp}/MANIFEST.json" "s3://${R2_BUCKET}/${ARCHIVE}MANIFEST.json" \
      --content-type application/json --quiet
    aws_r2 s3 cp "s3://${R2_BUCKET}/${ARCHIVE}README.txt" "${tmp}/README.txt" --quiet
    if ! grep -q "datasets/parquet/00-latest" "${tmp}/README.txt"; then
      printf '\nParquet: v1/datasets/parquet/00-latest/ holds the one Parquet set built from this\ngeneration'"'"'s latest bundle (Parquet is derived; only the latest set is kept per generation).\n' \
        >> "${tmp}/README.txt"
      aws_r2 s3 cp "${tmp}/README.txt" "s3://${R2_BUCKET}/${ARCHIVE}README.txt" --content-type text/plain --quiet
    fi
    echo "  ${ARCHIVE}MANIFEST.json and README.txt updated."
  fi
  rm -rf "${tmp}"
}

# Has archive-latest-parquet run? (the archive MANIFEST lists 00-latest Parquet objects)
latest_parquet_archived() {
  aws_r2 s3 cp "s3://${R2_BUCKET}/${ARCHIVE}MANIFEST.json" - 2>/dev/null \
    | python3 -c 'import json,sys; p=sys.argv[1]; sys.exit(0 if any(e["original_key"].startswith(p) for e in json.load(sys.stdin)["files"]) else 1)' \
      "${LATEST_PARQUET}"
}

stage() {
  require_target
  local label date ver
  if [[ "$TARGET" == "parquet" ]]; then
    read -r date ver <<< "${LATEST_SOURCE}"
    echo "=== stage latest Parquet from ${date} (${ver}) -> ${STAGE_DIR} ==="
    "${SCRIPT_DIR}/release-gkm-parquet.sh" "$date" "$ver" --no-upload
    return
  fi
  while read -r label date ver; do
    [[ -n "$label" ]] || continue
    echo "=== stage full ${label} (from ${date}, ${ver}) -> ${STAGE_DIR} ==="
    "${SCRIPT_DIR}/release-gkm.sh" "$date" "$ver" "--month-label=${label}" --no-upload
  done < <(fulls_for "$TARGET")
  while read -r date ver; do
    [[ -n "$date" ]] || continue
    echo "=== stage delta ${date} (${ver}) -> ${STAGE_DIR} ==="
    "${SCRIPT_DIR}/release-gkm-delta.sh" "$date" "$ver" --no-upload
  done < <(deltas_for "$TARGET")
}

upload() {
  require_target
  local flags=() label date ver
  $DRY_RUN && flags+=(--dry-run)
  if [[ "$TARGET" == "parquet" ]]; then
    read -r date ver <<< "${LATEST_SOURCE}"
    local pq="${STAGE_DIR}/clinvar-gkm-parquet-latest-${date}"
    if ! latest_parquet_archived; then
      echo "ERROR: run archive-latest-parquet first: ${LATEST_PARQUET} (1.0.1's latest Parquet) is not in ${ARCHIVE}MANIFEST.json" >&2
      $DRY_RUN || exit 1
    fi
    $DRY_RUN || [[ -d "$pq" ]] || { echo "ERROR: latest Parquet not staged (${pq}/)" >&2; exit 1; }
    echo "=== upload latest Parquet (from ${date}) ==="
    "${SCRIPT_DIR}/upload-gkm-parquet-to-r2.sh" "$date" "$ver" "$pq" "${flags[@]+"${flags[@]}"}"
    return
  fi
  while read -r label date ver; do
    [[ -n "$label" ]] || continue
    local bundle="${STAGE_DIR}/clinvar-gkm-${date}.json.gz"
    $DRY_RUN || [[ -f "$bundle" ]] || { echo "ERROR: ${label} not staged (${bundle})" >&2; exit 1; }
    echo "=== upload full ${label} ==="
    "${SCRIPT_DIR}/upload-gkm-to-r2.sh" "$date" "$ver" "$bundle" "--month-label=${label}" "${flags[@]+"${flags[@]}"}"
  done < <(fulls_for "$TARGET")
  while read -r date ver; do
    [[ -n "$date" ]] || continue
    local bundle="${STAGE_DIR}/clinvar-gkm-delta-${date}.json.gz"
    local manifest="${STAGE_DIR}/clinvar-gkm-delta-${date}-manifest.json"
    $DRY_RUN || [[ -f "$bundle" && -f "$manifest" ]] || { echo "ERROR: delta ${date} not staged (${bundle}, ${manifest})" >&2; exit 1; }
    echo "=== upload delta ${date} ==="
    "${SCRIPT_DIR}/upload-gkm-delta-to-r2.sh" "$date" "$bundle" "$manifest" "${flags[@]+"${flags[@]}"}"
  done < <(deltas_for "$TARGET")
}

# --- delete-dated-parquet ------------------------------------------------------------------------------------
# Deletes every dated Parquet object: v1/datasets/parquet/<YYYY-MM>/, v1/archives/*/parquet/ and every
# v1/deltas/*/parquet/ (incl. deltas/00-latest/parquet/). Guarded: runs for real only when 1.0.1's latest set is
# in the archive AND the new latest set is in place (source.json names LATEST_SOURCE, the four proposition*
# tables are there and no var*-proposition table is). --dry-run lists every object and the total size.
delete_dated_parquet() {
  local tmp; tmp="$(mktemp -d)"
  r2_list "${R2_PREFIX}" | awk -v p="${R2_PREFIX}" '
      index($2, p "datasets/parquet/") == 1 && $2 !~ "/00-latest/" { print; next }
      $2 ~ "^" p "deltas/[^/]+/parquet/" || $2 ~ "^" p "archives/[^/]+/parquet/" { print }' > "${tmp}/del.txt"
  local n bytes
  n="$(wc -l < "${tmp}/del.txt" | tr -d ' ')"
  bytes="$(awk '{s += $1} END {print s + 0}' "${tmp}/del.txt")"
  echo "=== delete-dated-parquet: ${n} objects, ${bytes} bytes ($(human "$bytes")) ==="
  awk '{ sub("/[^/]*$", "/", $2); d[$2] += $1; c[$2]++ } END { for (k in d) printf "  %-40s %4d files  %8.1f MB\n", k, c[k], d[k] / 1e6 }' \
    "${tmp}/del.txt" | sort

  local ok=true src_rel names
  latest_parquet_archived || { echo "  guard: ${LATEST_PARQUET} is not archived in ${ARCHIVE} (run archive-latest-parquet)"; ok=false; }
  src_rel="$(aws_r2 s3 cp "s3://${R2_BUCKET}/${LATEST_PARQUET}source.json" - 2>/dev/null \
    | sed -n 's/^ *"release": *"\([0-9-]*\)".*/\1/p' | head -n1 || true)"
  names="$(aws_r2 s3 ls "s3://${R2_BUCKET}/${LATEST_PARQUET}" | awk '{print $NF}')"
  [[ "$src_rel" == "${LATEST_SOURCE%% *}" ]] || { echo "  guard: ${LATEST_PARQUET}source.json names '${src_rel:-none}', not ${LATEST_SOURCE%% *}"; ok=false; }
  [[ "$(echo "$names" | grep -c '^proposition[A-Za-z]*\.parquet$')" -eq 4 ]] || { echo "  guard: ${LATEST_PARQUET} lacks the four proposition*.parquet tables"; ok=false; }
  if echo "$names" | grep -q -- '-proposition\.parquet$'; then echo "  guard: ${LATEST_PARQUET} still holds a var*-proposition table"; ok=false; fi

  if $DRY_RUN; then
    sed 's/^/  [dry-run] delete: /' "${tmp}/del.txt"
    if $ok; then echo "  guards: PASS"; else echo "  guards: FAIL (a real run would refuse)"; fi
    rm -rf "${tmp}"; return 0
  fi
  $ok || { echo "ERROR: refusing to delete (guards above)" >&2; rm -rf "${tmp}"; exit 1; }
  local size key
  while read -r size key; do
    aws_r2 s3 rm "s3://${R2_BUCKET}/${key}" --quiet
  done < "${tmp}/del.txt"
  echo "  deleted ${n} objects ($(human "$bytes"))."
  rm -rf "${tmp}"
}

# --- purge: Cloudflare purge_everything (the zone serves only this bucket; every path changes) -------------
# Credentials come from CF_ENV_FILE (CF_PURGE_TOKEN, CF_ZONE_ID) and are never printed or put on a command
# line: curl reads the URL and the Authorization header from stdin (-K -).
purge() {
  [[ -r "$CF_ENV_FILE" ]] || { echo "ERROR: ${CF_ENV_FILE} not readable" >&2; exit 1; }
  (
    set +x
    # shellcheck disable=SC1090
    . "$CF_ENV_FILE"
    [[ -n "${CF_PURGE_TOKEN:-}" && -n "${CF_ZONE_ID:-}" ]] || { echo "ERROR: CF_PURGE_TOKEN / CF_ZONE_ID not set in ${CF_ENV_FILE}" >&2; exit 1; }
    echo "=== purge: everything on the data.clinvar-gkm.org zone (credentials from ${CF_ENV_FILE}) ==="
    if $DRY_RUN; then
      local verify
      verify="$(printf 'url = "https://api.cloudflare.com/client/v4/user/tokens/verify"\nheader = "Authorization: Bearer %s"\n' \
        "$CF_PURGE_TOKEN" | curl -sS -K - | python3 -c 'import json,sys; d=json.load(sys.stdin); print((d.get("result") or {}).get("status") or ("error: " + str(d.get("errors"))))' 2>/dev/null || echo unreachable)"
      echo "  [dry-run] token present, zone id present; token status: ${verify}"
      echo "  [dry-run] would POST /zones/<zone>/purge_cache {\"purge_everything\": true}"
      exit 0
    fi
    printf 'url = "https://api.cloudflare.com/client/v4/zones/%s/purge_cache"\nrequest = "POST"\nheader = "Authorization: Bearer %s"\nheader = "Content-Type: application/json"\ndata = "{\\"purge_everything\\":true}"\n' \
      "$CF_ZONE_ID" "$CF_PURGE_TOKEN" | curl -sS -K - \
      | python3 -c 'import json,sys; d=json.load(sys.stdin); print("  purge:", "OK" if d.get("success") else "FAILED " + str(d.get("errors"))); sys.exit(0 if d.get("success") else 1)'
  )
}

case "$CMD" in
  list)
    echo "fulls (label  source  version):"; echo "$FULLS" | awk 'NF' | sed 's/^/  /'
    echo "deltas (date  version):"; echo "$DELTAS" | awk 'NF' | sed 's/^/  /'
    echo "parquet (latest, built from): ${LATEST_SOURCE}" ;;
  backup) backup ;;
  verify-archive) verify_archive ;;
  archive-latest-parquet) archive_latest_parquet ;;
  stage) stage ;;
  upload) upload ;;
  delete-dated-parquet) delete_dated_parquet ;;
  index)
    args=(); $DRY_RUN && args+=(--dry-run)
    "${SCRIPT_DIR}/generate-r2-index.sh" "${args[@]+"${args[@]}"}" ;;
  purge) purge ;;
  *) usage ;;
esac
