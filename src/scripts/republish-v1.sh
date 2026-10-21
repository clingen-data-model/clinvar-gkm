#!/bin/bash
# republish-v1.sh — the 1.1.0 migration of the R2 bucket to the NCBI-style layout (r2_layout.py), per version line:
#
#   v1/1.0/   the 1.0.1 generation, FROZEN (moved from archive/1.0.1/): monthlies 2026-07..10 + 00-latest at the
#             top, every delta under deltas/YYYY-MM/, MANIFEST.json + README.txt + index.json + feed.xml
#   v1/1.1/   the 1.1.0 republish, CURRENT: 4 monthlies + 00-latest, weekly/ (October's weekly fulls 10-04, 10-11,
#             10-18 + 00-latest_weekly), deltas/ (October's deltas at the top, July-September in deltas/YYYY-MM/),
#             parquet/ (one set, from 10-18, + manifest.json), index.json, feed.xml, README.txt
#   index.json (bucket root) lists both lines.
# Everything else (v1/datasets/, v1/deltas/, v1/index.json, v1/feed.xml, v1/README.txt, archive/1.0.1/, any
# _backup/) is deleted by `cleanup` once `verify` passes.
#
# Run AFTER the 17 datasets are rebuilt and gated (runbook 2026-10-20-1.1.0-rebuild-runbook.md). Each step that
# writes to R2 or Cloudflare is a separate, user-confirmed step and honours --dry-run. Steps, in order:
#   ./republish-v1.sh list
#   ./republish-v1.sh plan                               # read-only: the whole plan with counts and GB (live listing)
#   ./republish-v1.sh verify-archive                     # 1. archive/1.0.1/MANIFEST.json covers every live v1/ bundle
#   ./republish-v1.sh move-1.0                [--dry-run] # 2. archive/1.0.1/ -> v1/1.0/ (server-side copies + sidecars,
#                                                       #    MANIFEST.json, README.txt, index.json, feed.xml)
#   ./republish-v1.sh stage   <target>                  # 3. export + assemble, NO upload (STAGE_DIR)
#   ./republish-v1.sh upload  <target>        [--dry-run] # 3-4. into v1/1.1/ (monthly first: deltas need their sources)
#   ./republish-v1.sh index                   [--dry-run] # 5. v1/1.1 + v1/1.0 index.json/feed.xml, root index.json
#   ./republish-v1.sh verify                             # 5. both lines complete; delta chain, checkpoint_full, sha256
#   ./republish-v1.sh cleanup                 [--dry-run] # 6. delete every key outside the plan; refuses unless verify passes
#   ./republish-v1.sh purge                   [--dry-run] # 7. Cloudflare purge_everything
#
# <target>: all | monthly | weekly | deltas | parquet | a monthly label (2026-07) | a date (2026-10-04: its delta,
# and its weekly full when it has one). "all" runs monthly, weekly, deltas (date order), then parquet.
# STAGE_DIR (default /tmp): a full is about 4.8 GB, the Parquet set about 13 GB; stage one at a time if short.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STAGE_DIR="${STAGE_DIR:-/tmp}"
export STAGE_DIR

# Official monthly label | source release | dataset version (ADR 0002, checked against ClinVar's index 2026-10-20).
# The same mapping holds for the 1.0.1 generation (v1/1.0/).
FULLS="
2026-07 2026-06-27 v2_5_0
2026-08 2026-08-04 v2_5_0
2026-09 2026-08-29 v2_6_0
2026-10 2026-09-28 v2_6_0
"
# Weekly full bundles of the current month (October 2026): release | dataset version.
WEEKLY="
2026-10-04 v2_6_0
2026-10-11 v2_6_0
2026-10-18 v2_6_0
"
# Delta release | dataset version.
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
FIRST_BASELINE="2026-06-27"      # the 2026-07-06 delta's baseline_release
LATEST_SOURCE="${LATEST_SOURCE:-2026-10-18 v2_6_0}"   # the Parquet set is built from the newest dataset
NEW_LINE="v1/1.1/"
OLD_LINE="v1/1.0/"
ARCHIVE="${ARCHIVE:-archive/1.0.1/}"
CURRENT_MONTH="2026-10"          # the month of the newest release: its deltas sit at deltas/, earlier ones in deltas/YYYY-MM/

CMD="${1:-}"; [[ $# -gt 0 ]] && shift
TARGET=""; DRY_RUN=false
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    -*) echo "ERROR: unknown flag '${arg}'" >&2; exit 1 ;;
    *) TARGET="$arg" ;;
  esac
done
export DRY_RUN
R2_LINE="${NEW_LINE}"
# shellcheck source=r2-common.sh
. "${SCRIPT_DIR}/r2-common.sh"
export R2_LINE
SCHEMA_VERSION="$(sed -n 's/^SCHEMA_VERSION = "\(.*\)"$/\1/p' "${SCRIPT_DIR}/assemble-gkm-dicts.py")"

usage() { sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

fulls_for()  { echo "$FULLS"  | awk -v t="$1" 'NF==3 && (t=="all" || t=="monthly" || $1==t)'; }
weekly_for() { echo "$WEEKLY" | awk -v t="$1" 'NF==2 && (t=="all" || t=="weekly" || $1==t)'; }
deltas_for() { echo "$DELTAS" | awk -v t="$1" 'NF==2 && (t=="all" || t=="deltas" || $1==t)'; }
source_args() { echo "$FULLS" | awk 'NF==3 {printf "--source %s=%s ", $1, $2}'; }
compact() { echo "${1:0:4}-${1:5:2}${1:8:2}"; }

require_target() {
  [[ -n "$TARGET" ]] || { echo "ERROR: ${CMD} needs a target (see: $0 list)" >&2; exit 1; }
  [[ "$TARGET" == "parquet" ]] && return 0
  if [[ -z "$(fulls_for "$TARGET")$(weekly_for "$TARGET")$(deltas_for "$TARGET")" ]]; then
    echo "ERROR: unknown target '${TARGET}' (see: $0 list)" >&2; exit 1
  fi
}

# --- verify-archive: every live v1/ bundle, delta manifest, index and feed is in the archive MANIFEST ---------
verify_archive() {
  local tmp; tmp="$(mktemp -d)"
  r2_cat "${ARCHIVE}MANIFEST.json" > "${tmp}/MANIFEST.json"
  r2_listing "v1/" "${tmp}/live.txt"
  echo "$(r2_size index.json) index.json" | awk '{print "x x", $1, $2}' >> "${tmp}/live.txt"
  r2_listing "${ARCHIVE}" "${tmp}/archived.txt"
  local rc=0
  "${R2_PYTHON}" - "${tmp}" "${ARCHIVE}" <<'PY' || rc=1
import json, re, sys
tmp, archive = sys.argv[1:3]
man = json.load(open(f"{tmp}/MANIFEST.json"))
entries = {e["original_key"]: e for e in man["files"]}
def listing(p):
    out = {}
    for line in open(p):
        parts = line.split()
        if len(parts) >= 4: out[parts[3]] = int(parts[2])
    return out
archived, live_all = listing(f"{tmp}/archived.txt"), listing(f"{tmp}/live.txt")
# The pre-1.1.0 /v1/ files a consumer could have fetched: bundles, delta manifests, index, feed. Parquet,
# sidecars and README are not archived; the new lines (v1/1.0/, v1/1.1/) are not part of the 1.0.1 generation.
skip = re.compile(r"^v1/(_backup/|1\.\d+/|.*\.parquet$|.*/source\.json$|README\.txt$|.*\.sha256$)")
live = {k: s for k, s in live_all.items() if k == "index.json" or (k.startswith("v1/") and not skip.match(k))}
missing = [k for k in live if k not in entries]
size_bad = [k for k in live if k in entries and entries[k]["size"] != live[k]]
obj_bad = [e["archive_key"] for e in man["files"] if archived.get(e["archive_key"]) != e["size"]]
print(f"  MANIFEST: schema_version={man.get('schema_version')} file_count={man.get('file_count')} "
      f"entries={len(man['files'])} total_size={man.get('total_size')}")
print(f"  live files that must be archived (bundles, delta manifests, indexes, feed): {len(live)}")
print(f"  missing from MANIFEST: {len(missing)}   size differs from MANIFEST: {len(size_bad)}   "
      f"archive object missing or wrong size: {len(obj_bad)}")
for k in (missing + size_bad + obj_bad)[:20]: print("   -", k)
sys.exit(1 if (missing or size_bad or obj_bad or man.get("file_count") != len(man["files"])) else 0)
PY
  rm -rf "${tmp}"
  if [[ $rc -eq 0 ]]; then echo "PASS: ${ARCHIVE} holds every live v1/ bundle file at its live size."
  else echo "FAIL: the archive is incomplete (see above)" >&2; return 1; fi
}

# --- move-1.0: archive/1.0.1/ -> frozen line v1/1.0/ -----------------------------------------------------------
# Server-side copies (the bytes, and so the sha256s, are unchanged), .sha256 sidecars written from the archive
# MANIFEST (no download), a new MANIFEST.json and README.txt, then v1/1.0/index.json + feed.xml. Idempotent: a copy
# whose destination already exists at the same size is skipped. archive/1.0.1/ itself is deleted by `cleanup`.
readme_10() {
  cat <<'EOF'
ClinVar-GKM v1/1.0 (schema 1.0.1) -- FROZEN
===========================================

This line holds the 1.0.1 generation of ClinVar-GKM, frozen on its move here from archive/1.0.1/
during the 1.1.0 release. Nothing under v1/1.0/ will be changed, added or deleted.

It is superseded by v1/1.1 (schema 1.1.x):
  https://data.clinvar-gkm.org/v1/1.1/index.json
  https://data.clinvar-gkm.org/index.json   (all lines)

What is here
  clinvar-gkm_YYYY-MM.json.gz            official monthly full bundles 2026-07 .. 2026-10 (+ .sha256)
  clinvar-gkm_00-latest.json.gz          the same bytes as clinvar-gkm_2026-10.json.gz (+ .sha256)
  deltas/YYYY-MM/clinvar-gkm-delta_YYYY-MMDD.json.gz        weekly deltas (+ .sha256)
  deltas/YYYY-MM/clinvar-gkm-delta_YYYY-MMDD.manifest.json  each delta's manifest
  index.json, feed.xml                   this line's listing
  MANIFEST.json                          every file: key, size, sha256, and the key it was first published at

Monthly source releases (ADR 0002): 2026-07 <- 2026-06-27, 2026-08 <- 2026-08-04, 2026-09 <- 2026-08-29,
2026-10 <- 2026-09-28. To replay deltas, start from the newest monthly whose source release is on or before
a delta's baseline_release.

Known issues kept as published (the files are byte-identical to 1.0.1):
  * every delta manifest's checkpoint_full says 2026-10; use the mapping above instead.
  * paths inside the delta manifests and bundles name the original v1/datasets/ and v1/deltas/ keys.
  * there is no Parquet for this line.

Changelog: https://dataexchange.clinicalgenome.org/clinvar-gkm/reference/changelog/
EOF
}

move_10() {
  local tmp; tmp="$(mktemp -d)"
  echo "=== move-1.0: ${ARCHIVE} -> ${OLD_LINE} (frozen) ==="
  r2_cat "${ARCHIVE}MANIFEST.json" > "${tmp}/MANIFEST.json"
  [[ -s "${tmp}/MANIFEST.json" ]] || { echo "ERROR: ${ARCHIVE}MANIFEST.json not readable" >&2; return 1; }
  r2_listing "${OLD_LINE}" "${tmp}/dest.txt"
  r2_layout move-1.0 --manifest "${tmp}/MANIFEST.json" --archive "${ARCHIVE}" --dest "${OLD_LINE}" \
    --out-dir "${tmp}/out" > "${tmp}/plan.txt"
  sed -n 's/^# /  /p' "${tmp}/plan.txt"
  awk '$1 == "COPY" {n++; b += $2} END {printf "  copies: %d objects, %.2f GB (server-side)\n", n, b / 1e9}' "${tmp}/plan.txt"
  local op size src dst have n=0 skipped=0
  while read -r op size src dst; do
    [[ "${op}" == "COPY" ]] || continue
    have="$(awk -v k="${dst}" '$4 == k {print $3}' "${tmp}/dest.txt")"
    if [[ "${have}" == "${size}" ]]; then skipped=$((skipped + 1)); continue; fi
    r2_copy "${src}" "${dst}" "${size}"
    if ! ${DRY_RUN}; then
      have="$(r2_size "${dst}")"
      [[ "${have}" == "${size}" ]] || { echo "ERROR: ${dst} is ${have:-missing} B, expected ${size}" >&2; return 1; }
    fi
    n=$((n + 1))
  done < "${tmp}/plan.txt"
  echo "  copied ${n}, already in place ${skipped}"
  local f key
  while IFS= read -r f; do
    key="${f#"${tmp}/out/"}"
    case "${key}" in
      *.sha256) r2_put "${f}" "${key}" "text/plain" ;;
      *MANIFEST.json) r2_put "${f}" "${key}" "application/json" ;;
    esac
  done < <(find "${tmp}/out" -type f | sort)
  readme_10 > "${tmp}/README.txt"
  r2_put "${tmp}/README.txt" "${OLD_LINE}README.txt" "text/plain"
  local idx=(--line "${OLD_LINE}" --no-root); ${DRY_RUN} && idx+=(--dry-run)
  # shellcheck disable=SC2046
  "${SCRIPT_DIR}/generate-r2-index.sh" "${idx[@]}" $(source_args)
  rm -rf "${tmp}"
}

# --- stage / upload ---------------------------------------------------------------------------------------------
stage() {
  require_target
  local label date ver
  if [[ "$TARGET" == "parquet" ]]; then
    read -r date ver <<< "${LATEST_SOURCE}"
    echo "=== stage the Parquet set from ${date} (${ver}) -> ${STAGE_DIR} ==="
    "${SCRIPT_DIR}/release-gkm-parquet.sh" "$date" "$ver" --no-upload
    return
  fi
  while read -r label date ver; do
    [[ -n "$label" ]] || continue
    echo "=== stage monthly ${label} (from ${date}, ${ver}) -> ${STAGE_DIR} ==="
    "${SCRIPT_DIR}/release-gkm.sh" "$date" "$ver" "--month-label=${label}" --no-upload
  done < <(fulls_for "$TARGET")
  while read -r date ver; do
    [[ -n "$date" ]] || continue
    echo "=== stage weekly full ${date} (${ver}) -> ${STAGE_DIR} ==="
    "${SCRIPT_DIR}/release-gkm.sh" "$date" "$ver" --weekly --no-upload
  done < <(weekly_for "$TARGET")
  while read -r date ver; do
    [[ -n "$date" ]] || continue
    echo "=== stage delta ${date} (${ver}) -> ${STAGE_DIR} ==="
    "${SCRIPT_DIR}/release-gkm-delta.sh" "$date" "$ver" --no-upload
  done < <(deltas_for "$TARGET")
  [[ "$TARGET" == "all" ]] && { TARGET=parquet; stage; }
  return 0
}

upload() {
  require_target
  local flags=() label date ver
  ${DRY_RUN} && flags+=(--dry-run)
  if [[ "$TARGET" == "parquet" ]]; then
    read -r date ver <<< "${LATEST_SOURCE}"
    local pq="${STAGE_DIR}/clinvar-gkm-parquet-latest-${date}"
    ${DRY_RUN} || [[ -d "$pq" ]] || { echo "ERROR: Parquet not staged (${pq}/)" >&2; exit 1; }
    echo "=== upload the Parquet set (from ${date}) -> ${NEW_LINE}parquet/ ==="
    "${SCRIPT_DIR}/upload-gkm-parquet-to-r2.sh" "$date" "$ver" "$pq" "${flags[@]+"${flags[@]}"}"
    return
  fi
  while read -r label date ver; do
    [[ -n "$label" ]] || continue
    local bundle="${STAGE_DIR}/clinvar-gkm-${date}.json.gz"
    ${DRY_RUN} || [[ -f "$bundle" ]] || { echo "ERROR: ${label} not staged (${bundle})" >&2; exit 1; }
    echo "=== upload monthly ${label} (source ${date}) ==="
    "${SCRIPT_DIR}/upload-gkm-to-r2.sh" "$date" "$ver" "$bundle" "--month-label=${label}" "${flags[@]+"${flags[@]}"}"
  done < <(fulls_for "$TARGET")
  while read -r date ver; do
    [[ -n "$date" ]] || continue
    local bundle="${STAGE_DIR}/clinvar-gkm-${date}.json.gz"
    ${DRY_RUN} || [[ -f "$bundle" ]] || { echo "ERROR: weekly full ${date} not staged (${bundle})" >&2; exit 1; }
    echo "=== upload weekly full ${date} ==="
    "${SCRIPT_DIR}/upload-gkm-to-r2.sh" "$date" "$ver" "$bundle" --weekly "${flags[@]+"${flags[@]}"}"
  done < <(weekly_for "$TARGET")
  while read -r date ver; do
    [[ -n "$date" ]] || continue
    local bundle="${STAGE_DIR}/clinvar-gkm-delta-${date}.json.gz"
    local manifest="${STAGE_DIR}/clinvar-gkm-delta-${date}-manifest.json"
    ${DRY_RUN} || [[ -f "$bundle" && -f "$manifest" ]] || { echo "ERROR: delta ${date} not staged (${bundle}, ${manifest})" >&2; exit 1; }
    echo "=== upload delta ${date} ==="
    CURRENT_MONTH="${CURRENT_MONTH}" "${SCRIPT_DIR}/upload-gkm-delta-to-r2.sh" "$date" "$bundle" "$manifest" "${flags[@]+"${flags[@]}"}"
  done < <(deltas_for "$TARGET")
  [[ "$TARGET" == "all" ]] && { TARGET=parquet; upload; }
  return 0
}

index() {
  local args=(); ${DRY_RUN} && args+=(--dry-run)
  # shellcheck disable=SC2046
  "${SCRIPT_DIR}/generate-r2-index.sh" --line "${NEW_LINE}" "${args[@]+"${args[@]}"}" $(source_args)
  # shellcheck disable=SC2046
  "${SCRIPT_DIR}/generate-r2-index.sh" --line "${OLD_LINE}" --no-root "${args[@]+"${args[@]}"}" $(source_args)
}

# --- verify: both lines hold exactly the planned files, and the 1.1 delta chain is correct ----------------------
verify() {
  local tmp; tmp="$(mktemp -d)"
  echo "=== verify ${NEW_LINE} and ${OLD_LINE} ==="
  r2_listing "v1/" "${tmp}/listing.txt"
  r2_cat index.json > "${tmp}/root.json" || true
  r2_cat "${NEW_LINE}index.json" > "${tmp}/new-index.json" || true
  r2_cat "${OLD_LINE}MANIFEST.json" > "${tmp}/old-manifest.json" || true
  r2_cat "${NEW_LINE}parquet/manifest.json" > "${tmp}/parquet.json" || true
  mkdir -p "${tmp}/sidecars" "${tmp}/manifests"
  r2_mirror_small "${NEW_LINE}" "${tmp}/sidecars/${NEW_LINE}"
  r2_mirror_small "${OLD_LINE}" "${tmp}/sidecars/${OLD_LINE}"
  local key
  while read -r _ _ _ key; do
    case "${key}" in "${NEW_LINE}"deltas/*.manifest.json) r2_cat "${key}" > "${tmp}/manifests/${key##*/}" ;; esac
  done < "${tmp}/listing.txt"
  local rc=0
  echo "$FULLS" | awk 'NF==3' > "${tmp}/fulls.txt"
  echo "$WEEKLY" | awk 'NF==2' > "${tmp}/weekly.txt"
  echo "$DELTAS" | awk 'NF==2' > "${tmp}/deltas.txt"
  "${R2_PYTHON}" - "${tmp}" "${NEW_LINE}" "${OLD_LINE}" "${CURRENT_MONTH}" "${FIRST_BASELINE}" "${SCHEMA_VERSION}" <<'PY' || rc=1
import json, os, sys
tmp, new, old, cur, first_baseline, schema = sys.argv[1:7]
L = {}
for line in open(f"{tmp}/listing.txt"):
    p = line.split()
    if len(p) >= 4: L[p[3]] = int(p[2])
def load(p):
    try: return json.load(open(p))
    except Exception: return None
def sha(key):
    p = os.path.join(tmp, "sidecars", key + ".sha256")
    return open(p).read().split()[0] if os.path.isfile(p) else None
fulls = [l.split() for l in open(f"{tmp}/fulls.txt")]
weekly = [l.split()[0] for l in open(f"{tmp}/weekly.txt")]
deltas = [l.split()[0] for l in open(f"{tmp}/deltas.txt")]
c = lambda d: f"{d[:4]}-{d[5:7]}{d[8:10]}"
fails = []
def need(key, why=""):
    if key not in L: fails.append(f"missing {key} {why}")
def ddir(line, d): return f"{line}deltas/" if d[:7] >= cur else f"{line}deltas/{d[:7]}/"

# --- v1/1.1 -------------------------------------------------------------------------------------------------
for f in ("index.json", "feed.xml", "README.txt", "parquet/manifest.json"): need(new + f)
for label, src, _ in fulls:
    k = f"{new}clinvar-gkm_{label}.json.gz"; need(k); need(k + ".sha256")
lat = f"{new}clinvar-gkm_00-latest.json.gz"; need(lat); need(lat + ".sha256")
newest = f"{new}clinvar-gkm_{fulls[-1][0]}.json.gz"
if L.get(lat) != L.get(newest) or sha(lat) != sha(newest): fails.append("00-latest differs from the newest monthly")
for d in weekly:
    k = f"{new}weekly/clinvar-gkm_{c(d)}.json.gz"; need(k); need(k + ".sha256")
wl = f"{new}weekly/clinvar-gkm_00-latest_weekly.json.gz"; need(wl); need(wl + ".sha256")
if L.get(wl) != L.get(f"{new}weekly/clinvar-gkm_{c(weekly[-1])}.json.gz"): fails.append("00-latest_weekly differs from the newest weekly full")
for d in deltas:
    base = f"{ddir(new, d)}clinvar-gkm-delta_{c(d)}"
    for s in (".json.gz", ".json.gz.sha256", ".manifest.json"): need(base + s, "(delta folder rule)")
idx = load(f"{tmp}/new-index.json") or {}
srcs = {m["release"]: m.get("source_release") for m in (idx.get("datasets") or {}).get("monthly", []) if not m.get("latest")}
for label, src, _ in fulls:
    if srcs.get(label) != src: fails.append(f"index source_release {label}={srcs.get(label)}, expected {src}")
if idx.get("schema_version") != schema: fails.append(f"index schema_version {idx.get('schema_version')} != {schema}")
pq = load(f"{tmp}/parquet.json") or {}
for f in pq.get("files", []):
    if L.get(f"{new}parquet/{f['name']}") != f["size"]: fails.append(f"parquet/{f['name']} size differs from manifest")
extra_pq = [k for k in L if k.startswith(new + "parquet/") and k.endswith(".parquet")
            and k.rsplit("/", 1)[1] not in {f["name"] for f in pq.get("files", [])}]
if extra_pq: fails.append(f"parquet files not in manifest: {extra_pq}")
# delta chain + checkpoint_full + sha256 + schema_version
prev = first_baseline
for d in deltas:
    m = load(f"{tmp}/manifests/clinvar-gkm-delta_{c(d)}.manifest.json")
    if not m: fails.append(f"manifest {d} unreadable"); prev = d; continue
    exp = max((f for f in fulls if f[1] <= m.get("baseline_release", "")), key=lambda f: f[1], default=None)
    cp = m.get("checkpoint_full") or {}
    row = (f"  {d}: baseline={m.get('baseline_release')} compare={m.get('compare_release')} "
           f"checkpoint={cp.get('month')}<-{cp.get('release')} schema={m.get('schema_version')}")
    bad = []
    if m.get("release") != d: bad.append("release")
    if m.get("baseline_release") != prev: bad.append(f"baseline!={prev}")
    if m.get("compare_release") != d: bad.append("compare")
    if not exp or cp.get("release") != exp[1] or cp.get("month") != exp[0] or cp.get("path") != f"{new}clinvar-gkm_{exp[0]}.json.gz":
        bad.append(f"checkpoint!={exp and exp[0]}")
    if m.get("sha256") != sha(f"{ddir(new, d)}clinvar-gkm-delta_{c(d)}.json.gz"): bad.append("sha256!=sidecar")
    if m.get("schema_version") != schema: bad.append("schema_version")
    print(row + ("  OK" if not bad else "  BAD " + ",".join(bad)))
    if bad: fails.append(f"delta {d}: {bad}")
    prev = d

# --- v1/1.0 (frozen) ----------------------------------------------------------------------------------------
om = load(f"{tmp}/old-manifest.json") or {"files": []}
if not om["files"]: fails.append(f"{old}MANIFEST.json missing")
for f in om["files"]:
    if L.get(f["key"]) != f["size"]: fails.append(f"{f['key']} missing or wrong size")
    if f["key"].endswith(".json.gz") and sha(f["key"]) != f["sha256"]: fails.append(f"{f['key']}.sha256 wrong")
for f in ("index.json", "feed.xml", "README.txt"): need(old + f)
if any(k.startswith(old + p) for k in L for p in ("weekly/", "parquet/")): fails.append(f"{old} has weekly/ or parquet/")

# --- root index ---------------------------------------------------------------------------------------------
root = load(f"{tmp}/root.json") or {}
vs = root.get("versions") or {}
cur_v = [v for v in vs.values() if v.get("status") == "current"]
if len(cur_v) != 1 or cur_v[0].get("index") != new + "index.json" or cur_v[0].get("schema") != schema:
    fails.append(f"root: exactly one current version, index {new}index.json, schema {schema}")
o = vs.get(old.split("/")[1]) or {}
if o.get("status") != "frozen" or o.get("superseded_by") != new.rstrip("/") or o.get("index") != old + "index.json":
    fails.append("root entry for the frozen line")

n_new = sum(1 for k in L if k.startswith(new)); n_old = sum(1 for k in L if k.startswith(old))
print(f"  {new}: {n_new} objects, {sum(s for k, s in L.items() if k.startswith(new)) / 1e9:.2f} GB; "
      f"{old}: {n_old} objects, {sum(s for k, s in L.items() if k.startswith(old)) / 1e9:.2f} GB")
for f in fails[:40]: print("  FAIL", f)
sys.exit(1 if fails else 0)
PY
  rm -rf "${tmp}"
  if [[ $rc -eq 0 ]]; then echo "PASS: both lines match the plan."; else echo "FAIL: see above" >&2; return 1; fi
}

# --- cleanup: delete every key outside the plan --------------------------------------------------------------
cleanup() {
  local tmp; tmp="$(mktemp -d)"
  r2_listing "" "${tmp}/all.txt"
  r2_layout cleanup --listing "${tmp}/all.txt" > "${tmp}/del.txt"
  echo "=== cleanup: keys outside v1/1.0/, v1/1.1/ and the root index.json ==="
  grep '^# ' "${tmp}/del.txt" | sed 's/^# /  /' || true
  awk '$1 == "DELETE" { k = $3; sub("/[^/]*$", "/", k); if (k !~ /\//) k = "(root) " $3; d[k] += $2; c[k]++ }
       END { for (k in d) printf "  %-45s %4d objects %9.2f GB\n", k, c[k], d[k] / 1e9 }' "${tmp}/del.txt" | sort
  awk '$1 == "DELETE" {n++; b += $2} END {printf "  TOTAL: %d objects, %.2f GB\n", n, b / 1e9}' "${tmp}/del.txt"
  local ok=true
  if ! verify > "${tmp}/verify.log" 2>&1; then ok=false; fi
  if ${DRY_RUN}; then
    if ${ok}; then echo "  guard (verify): PASS"; else echo "  guard (verify): FAIL -- a real run would refuse"; tail -5 "${tmp}/verify.log" | sed 's/^/    /'; fi
    rm -rf "${tmp}"; return 0
  fi
  ${ok} || { cat "${tmp}/verify.log"; echo "ERROR: refusing to delete: verify failed" >&2; rm -rf "${tmp}"; exit 1; }
  local op size key n=0
  while read -r op size key; do
    [[ "${op}" == "DELETE" ]] || continue
    r2_rm "${key}"; n=$((n + 1))
  done < "${tmp}/del.txt"
  echo "  deleted ${n} objects."
  rm -rf "${tmp}"
}

# --- plan: the whole migration from the live listing (read-only) ------------------------------------------------
plan() {
  local tmp; tmp="$(mktemp -d)"
  r2_listing "" "${tmp}/all.txt"
  r2_cat "${ARCHIVE}MANIFEST.json" > "${tmp}/MANIFEST.json"
  echo "=== migration plan (read-only, live listing $(date -u +%Y-%m-%dT%H:%MZ)) ==="
  awk '{n++; b += $3} END {printf "  bucket now: %d objects, %.2f GB\n", n, b / 1e9}' "${tmp}/all.txt"
  echo "--- 2. move-1.0: ${ARCHIVE} -> ${OLD_LINE} ---"
  r2_layout move-1.0 --manifest "${tmp}/MANIFEST.json" --archive "${ARCHIVE}" --dest "${OLD_LINE}" \
    --out-dir "${tmp}/out" > "${tmp}/move.txt"
  awk '$1 == "COPY" {n++; b += $2} END {printf "  server-side copies: %d objects, %.2f GB\n", n, b / 1e9}' "${tmp}/move.txt"
  echo "  new small files: $(find "${tmp}/out" -type f | wc -l | tr -d ' ') (sidecars + MANIFEST.json) + README.txt + index.json + feed.xml"
  sed -n 's/^# /  /p' "${tmp}/move.txt"
  awk '$1 == "COPY" {print "    " $3 " -> " $4}' "${tmp}/move.txt"
  echo "--- 3-4. uploads into ${NEW_LINE} (sizes estimated from the live 1.0.1 objects) ---"
  "${R2_PYTHON}" - "${tmp}/all.txt" "${NEW_LINE}" "${CURRENT_MONTH}" <<PY
import sys
L = {}
for line in open(sys.argv[1]):
    p = line.split()
    if len(p) >= 4: L[p[3]] = int(p[2])
new, cur = sys.argv[2], sys.argv[3]
fulls = [l.split() for l in """${FULLS}""".split("\n") if l.split()]
weekly = [l.split()[0] for l in """${WEEKLY}""".split("\n") if l.split()]
deltas = [l.split()[0] for l in """${DELTAS}""".split("\n") if l.split()]
c = lambda d: f"{d[:4]}-{d[5:7]}{d[8:10]}"
full_est = L.get("v1/datasets/clinvar-gkm_2026-10.json.gz", 4.83e9)
up = copy = 0; n_up = n_copy = 0
print("  monthly (upload; 00-latest is a server-side copy of the newest):")
for label, src, _ in fulls:
    s = L.get(f"v1/datasets/clinvar-gkm_{label}.json.gz", full_est); up += s; n_up += 2
    print(f"    {new}clinvar-gkm_{label}.json.gz (+.sha256)  <- {src}  ~{s/1e9:.2f} GB")
copy += full_est; n_copy += 1; n_up += 1
print(f"    {new}clinvar-gkm_00-latest.json.gz (+.sha256)  = 2026-10  ~{full_est/1e9:.2f} GB copy")
print("  weekly fulls (upload; 00-latest_weekly is a copy of the newest):")
for d in weekly:
    up += full_est; n_up += 2
    print(f"    {new}weekly/clinvar-gkm_{c(d)}.json.gz (+.sha256)  ~{full_est/1e9:.2f} GB (estimate)")
copy += full_est; n_copy += 1; n_up += 1
print(f"    {new}weekly/clinvar-gkm_00-latest_weekly.json.gz (+.sha256)  = {weekly[-1]}  copy")
print("  deltas (bundle + .sha256 + .manifest.json):")
for d in deltas:
    folder = "deltas/" if d[:7] >= cur else f"deltas/{d[:7]}/"
    b = L.get(f"v1/deltas/{c(d)}/clinvar-gkm-delta_{c(d)}.json.gz"); m = L.get(f"v1/deltas/{c(d)}/manifest.json")
    est = (b or 0) + (m or 0); up += est; n_up += 3
    print(f"    {new}{folder}clinvar-gkm-delta_{c(d)}.*  ~{est/1e6:.1f} MB" + ("" if b else " (new in 1.1.0; size unknown)"))
pq = sum(s for k, s in L.items() if k.startswith("v1/datasets/parquet/00-latest/") and k.endswith(".parquet"))
up += pq; n_up += 23
print(f"  parquet: {new}parquet/ 22 sections + manifest.json  ~{pq/1e9:.2f} GB")
print(f"  plus index.json, feed.xml, README.txt; root index.json")
print(f"  UPLOAD TOTAL: ~{n_up} objects, ~{up/1e9:.2f} GB; server-side copies {n_copy}, ~{copy/1e9:.2f} GB")
PY
  echo "--- 6. cleanup (every key now in the bucket except the root index.json, which is rewritten) ---"
  r2_layout cleanup --listing "${tmp}/all.txt" > "${tmp}/del.txt"
  awk '$1 == "DELETE" { k = $3; sub("/[^/]*$", "/", k); if (k !~ /\//) k = "(root)"; d[k] += $2; c[k]++ }
       END { for (k in d) printf "  %-45s %4d objects %9.2f GB\n", k, c[k], d[k] / 1e9 }' "${tmp}/del.txt" | sort
  awk '$1 == "DELETE" {n++; b += $2} END {printf "  DELETE TOTAL: %d objects, %.2f GB\n", n, b / 1e9}' "${tmp}/del.txt"
  echo "--- 7. purge: purge_everything on data.clinvar-gkm.org ---"
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
    echo "monthly (label  source  version):"; echo "$FULLS" | awk 'NF' | sed 's/^/  /'
    echo "weekly fulls (date  version):"; echo "$WEEKLY" | awk 'NF' | sed 's/^/  /'
    echo "deltas (date  version; ${CURRENT_MONTH} at deltas/, earlier months in deltas/YYYY-MM/):"; echo "$DELTAS" | awk 'NF' | sed 's/^/  /'
    echo "parquet (one set, built from): ${LATEST_SOURCE}" ;;
  plan) plan ;;
  verify-archive) verify_archive ;;
  move-1.0) move_10 ;;
  stage) stage ;;
  upload) upload ;;
  index) index ;;
  verify) verify ;;
  cleanup) cleanup ;;
  purge) purge ;;
  *) usage ;;
esac
