# shellcheck shell=bash
# r2-common.sh — shared R2 and Cloudflare helpers for the publishing scripts. Sourced, never run.
#
# Every helper takes bucket-relative keys (e.g. v1/1.1/weekly/clinvar-gkm_2026-1018.json.gz). Every write
# (put, copy, move, delete, purge) honours DRY_RUN=true by printing what it would do. The path rules of a
# version line live in r2_layout.py; R2_LINE selects the line (default: the current line, v1/1.1/).
#
# R2 gaps (see .claude/rules/scripts.md): multipart copy calls GetObjectTagging and single-part copy with
# --copy-props none sends x-amz-tagging-directive, neither of which R2 implements, so r2_copy is size-aware.
# Cloudflare credentials (CF_ZONE_ID, CF_PURGE_TOKEN) come from the environment or CF_ENV_FILE and reach
# curl on stdin (-K -), never on a command line, and are never printed.

R2_BUCKET="clinvar-gkm"
R2_ENDPOINT="https://09208aa33790838db213a21f630c33e7.r2.cloudflarestorage.com"
R2_PROFILE="r2"
R2_PUBLIC_URL="${R2_PUBLIC_URL:-https://data.clinvar-gkm.org}"
CF_PUBLIC_HOST="${CF_PUBLIC_HOST:-data.clinvar-gkm.org}"
CF_ENV_FILE="${CF_ENV_FILE:-${HOME}/.config/clinvar-gkm/cloudflare.env}"
R2_LINE="${R2_LINE:-v1/1.1/}"
DRY_RUN="${DRY_RUN:-false}"
R2_COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
R2_PYTHON="${R2_PYTHON:-python3}"

r2_layout() { "${R2_PYTHON}" "${R2_COMMON_DIR}/r2_layout.py" "$@"; }
aws_r2() { aws --endpoint-url "${R2_ENDPOINT}" --profile "${R2_PROFILE}" "$@"; }
r2_human() { awk -v b="$1" 'BEGIN { printf "%.2f GB", b / 1e9 }'; }

# Recursive listing of a prefix ("DATE TIME SIZE KEY" lines) into a file. An empty prefix is not an error, but an
# unreachable bucket is: a planner fed an empty listing would plan the wrong thing.
r2_listing() {
  local prefix="$1" out="$2"
  if ! aws_r2 s3 ls "s3://${R2_BUCKET}/${prefix}" --recursive > "${out}" 2>/dev/null; then
    if [[ -s "${out}" ]]; then return 0; fi
    aws_r2 s3api head-bucket --bucket "${R2_BUCKET}" >/dev/null 2>&1 \
      || { echo "ERROR: cannot list s3://${R2_BUCKET}/ (credentials or network)" >&2; return 1; }
    : > "${out}"
  fi
}

# Size of an object in bytes, or empty when it does not exist.
r2_size() {
  aws_r2 s3api head-object --bucket "${R2_BUCKET}" --key "$1" --query ContentLength --output text 2>/dev/null || true
}

r2_cat() { aws_r2 s3 cp "s3://${R2_BUCKET}/$1" - 2>/dev/null; }

# Mirror the small files of a line (sha256 sidecars, index.json, parquet/manifest.json) into a local directory.
r2_mirror_small() {
  local line="$1" dir="$2"
  mkdir -p "${dir}"
  aws_r2 s3 cp "s3://${R2_BUCKET}/${line}" "${dir}/" --recursive --quiet \
    --exclude "*" --include "*.sha256" --include "index.json" --include "parquet/manifest.json" 2>/dev/null || true
}

r2_put() {   # local_file key content_type
  local src="$1" key="$2" ctype="${3:-application/gzip}"
  if ${DRY_RUN}; then echo "  [dry-run] upload: ${key}"; return 0; fi
  aws_r2 s3 cp "${src}" "s3://${R2_BUCKET}/${key}" --content-type "${ctype}" --quiet
}

r2_copy() {  # src_key dst_key [size]
  local src="$1" dst="$2" size="${3:-}"
  if ${DRY_RUN}; then echo "  [dry-run] copy: ${src} -> ${dst}${size:+ (${size} B)}"; return 0; fi
  [[ -n "${size}" ]] || size="$(r2_size "${src}")"
  [[ -n "${size}" ]] || { echo "ERROR: copy source missing: ${src}" >&2; return 1; }
  if [[ "${size}" -ge 2147483648 ]]; then
    aws_r2 s3 cp "s3://${R2_BUCKET}/${src}" "s3://${R2_BUCKET}/${dst}" --copy-props none --quiet
  else
    aws_r2 s3api copy-object --bucket "${R2_BUCKET}" --key "${dst}" --copy-source "${R2_BUCKET}/${src}" >/dev/null
  fi
}

r2_rm() {    # key
  if ${DRY_RUN}; then echo "  [dry-run] delete: $1"; return 0; fi
  aws_r2 s3 rm "s3://${R2_BUCKET}/$1" --quiet
}

# Copy, check the copy's size, then delete the source. Never deletes when the copy is short or missing.
r2_move() {  # src_key dst_key size
  local src="$1" dst="$2" size="$3" got
  if ${DRY_RUN}; then echo "  [dry-run] move: ${src} -> ${dst} (${size} B)"; return 0; fi
  r2_copy "${src}" "${dst}" "${size}"
  got="$(r2_size "${dst}")"
  [[ "${got}" == "${size}" ]] || { echo "ERROR: ${dst} is ${got:-missing}, expected ${size} B; ${src} kept" >&2; return 1; }
  r2_rm "${src}"
}

# A sha256 sidecar in `sha256sum -c` format: "<sha>  <file name>".
r2_put_sidecar() {  # sha key_of_the_bundle
  local tmp
  tmp="$(mktemp)"
  printf '%s  %s\n' "$1" "${2##*/}" > "${tmp}"
  r2_put "${tmp}" "$2.sha256" "text/plain"
  rm -f "${tmp}"
}

# Purge CDN copies. cf_purge files <key>... purges https://host/<key>; cf_purge prefixes <key-prefix>... purges
# host/<prefix>. Batches of 30 per request. Never fatal: a failed purge warns, because the R2 write already happened.
cf_purge() {
  local kind="$1"; shift
  [[ $# -gt 0 ]] || return 0
  if ${DRY_RUN}; then
    local k; for k in "$@"; do echo "  [dry-run] purge ${kind}: ${CF_PUBLIC_HOST}/${k}"; done; return 0
  fi
  (
    set +x
    if [[ -z "${CF_ZONE_ID:-}" || -z "${CF_PURGE_TOKEN:-}" ]] && [[ -r "${CF_ENV_FILE}" ]]; then
      # shellcheck disable=SC1090
      . "${CF_ENV_FILE}"
    fi
    if [[ -z "${CF_ZONE_ID:-}" || -z "${CF_PURGE_TOKEN:-}" ]]; then
      echo "  WARNING: CF_ZONE_ID / CF_PURGE_TOKEN not set (env or ${CF_ENV_FILE}); CDN purge skipped" >&2; exit 0
    fi
    local body; body="$(mktemp)"
    local batch=()
    _post() {
      "${R2_PYTHON}" -c 'import json,sys; k=sys.argv[1]; h=sys.argv[2]; v=sys.argv[3:]
print(json.dumps({k: [("https://" if k == "files" else "") + h + "/" + x for x in v]}))' \
        "${kind}" "${CF_PUBLIC_HOST}" "${batch[@]}" > "${body}"
      printf 'url = "https://api.cloudflare.com/client/v4/zones/%s/purge_cache"\nrequest = "POST"\nheader = "Authorization: Bearer %s"\nheader = "Content-Type: application/json"\n' \
        "${CF_ZONE_ID}" "${CF_PURGE_TOKEN}" \
        | curl -sS --max-time 60 -K - --data-binary "@${body}" \
        | "${R2_PYTHON}" -c 'import json,sys; d=json.load(sys.stdin); print("  purge", sys.argv[1], sys.argv[2], "OK" if d.get("success") else "FAILED " + str(d.get("errors")))' \
            "${kind}" "${#batch[@]}" || echo "  WARNING: CDN purge request failed" >&2
    }
    local k
    for k in "$@"; do
      batch+=("${k}")
      if [[ ${#batch[@]} -eq 30 ]]; then _post; batch=(); fi
    done
    if [[ ${#batch[@]} -gt 0 ]]; then _post; fi
    rm -f "${body}"
  )
}
