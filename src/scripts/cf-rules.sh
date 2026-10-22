#!/bin/bash
# cf-rules.sh — Cloudflare cache rules and the path-allowlist WAF rule for the NCBI-style R2 layout (r2_layout.py).
#
#   ./cf-rules.sh show                      # read-only: each rule's live expression next to the proposed one
#   ./cf-rules.sh apply [--dry-run] [--drop-archive]
#                                           # PATCH the rules whose expression differs (user-confirmed step)
#
# Cache rules (zone clinvar-gkm.org; the LAST matching rule wins, so the order is 1, 2, 3):
#   1 "R2 immutable artifacts"  every path: edge 1 month, browser 1 day (unchanged). Dated monthlies, deltas,
#                               archive/ and v1/1.0/ are write-once. A rollover MOVES deltas and archives monthlies to
#                               new keys and purges the old ones, so the long TTL stays safe.
#   2 "R2 mutable pointers"     bypass: anything with 00-latest (incl. 00-latest_weekly), every index.json,
#                               feed.xml and README.txt, and everything under a weekly/ folder (deleted at month end).
#   3 "Parquet"                 any line's parquet/ (overwritten every release): edge 1 day, purged on each rebuild.
# Path allowlist (WAF custom rule "PATH ALLOWLIST"): /v1/ covers both lines; /archive/ (the root archive/1.0.1/)
# is empty after the migration's cleanup. --drop-archive removes it from the allowlist (optional).
#
# Tokens come from CF_ENV_FILE: CF_CACHE_TOKEN (Zone > Cache Rules > Edit), CF_WAF_TOKEN (Zone WAF > Edit) and
# CF_ZONE_ID. They reach curl on stdin (-K -) and are never printed.
set -euo pipefail

CMD="${1:-show}"; [[ $# -gt 0 ]] && shift
DRY_RUN=false; DROP_ARCHIVE=false
for arg in "$@"; do case "$arg" in
  --dry-run) DRY_RUN=true ;;
  --drop-archive) DROP_ARCHIVE=true ;;
  *) echo "ERROR: unknown argument '${arg}'" >&2; exit 1 ;;
esac; done
CF_ENV_FILE="${CF_ENV_FILE:-${HOME}/.config/clinvar-gkm/cloudflare.env}"
[[ -r "${CF_ENV_FILE}" ]] || { echo "ERROR: ${CF_ENV_FILE} not readable" >&2; exit 1; }

H='http.host eq "data.clinvar-gkm.org"'
P='http.request.uri.path'
EXPR_MUTABLE="(${H}) and (${P} contains \"00-latest\" or ends_with(${P}, \"/index.json\") or ends_with(${P}, \"/feed.xml\") or ends_with(${P}, \"/README.txt\") or ${P} contains \"/weekly/\")"
EXPR_PARQUET="(${H} and starts_with(${P}, \"/v1/\") and ${P} contains \"/parquet/\")"
if ${DROP_ARCHIVE}; then
  EXPR_ALLOW="(${H} and not (starts_with(${P}, \"/v1/\") or starts_with(${P}, \"/.well-known/\") or ${P} in {\"/\" \"/index.json\"}))"
else
  EXPR_ALLOW="(${H} and not (starts_with(${P}, \"/v1/\") or starts_with(${P}, \"/archive/\") or starts_with(${P}, \"/.well-known/\") or ${P} in {\"/\" \"/index.json\"}))"
fi

TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
# description prefix | proposed expression, per phase
printf '%s\t%s\n' "R2 mutable pointers" "${EXPR_MUTABLE}" "Latest Parquet" "${EXPR_PARQUET}" > "${TMP}/cache.tsv"
printf '%s\t%s\n' "PATH ALLOWLIST" "${EXPR_ALLOW}" > "${TMP}/waf.tsv"

(
  set +x
  # shellcheck disable=SC1090
  . "${CF_ENV_FILE}"
  : "${CF_ZONE_ID:?CF_ZONE_ID not set}" "${CF_CACHE_TOKEN:?CF_CACHE_TOKEN not set}" "${CF_WAF_TOKEN:?CF_WAF_TOKEN not set}"
  api() {  # token method path [body_file]
    { printf 'url = "https://api.cloudflare.com/client/v4%s"\nrequest = "%s"\nheader = "Authorization: Bearer %s"\nheader = "Content-Type: application/json"\n' "$3" "$2" "$1"
    } | if [[ -n "${4:-}" ]]; then curl -sS --max-time 60 -K - --data-binary "@$4"; else curl -sS --max-time 60 -K -; fi
  }
  for spec in "cache http_request_cache_settings CF_CACHE_TOKEN" "waf http_request_firewall_custom CF_WAF_TOKEN"; do
    read -r name phase tokvar <<< "${spec}"
    tok="${!tokvar}"
    api "${tok}" GET "/zones/${CF_ZONE_ID}/rulesets/phases/${phase}/entrypoint" > "${TMP}/${name}.json"
    python3 - "${TMP}/${name}.json" "${TMP}/${name}.tsv" "${TMP}/${name}.patch" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
if not d.get("success"):
    sys.exit(f"ERROR reading ruleset: {d.get('errors')}")
r = d["result"]
want = [l.rstrip("\n").split("\t", 1) for l in open(sys.argv[2]) if l.strip()]
out = open(sys.argv[3], "w")
for desc, expr in want:
    hit = [x for x in r["rules"] if x.get("description", "").startswith(desc)]
    if len(hit) != 1:
        print(f"  {desc}: {len(hit)} matching rules -- fix by hand"); continue
    x = hit[0]
    same = " ".join(x["expression"].split()) == " ".join(expr.split())
    print(f"  {x['description']}\n    live:     {' '.join(x['expression'].split())}\n    proposed: {expr}\n    -> {'unchanged' if same else 'CHANGE'}")
    if not same:
        body = {k: x[k] for k in ("action", "action_parameters", "description", "enabled") if k in x}
        body["expression"] = expr
        out.write(json.dumps({"path": f"/rulesets/{r['id']}/rules/{x['id']}", "body": body}) + "\n")
PY
  done
  [[ "${CMD}" == "apply" ]] || exit 0
  for name in cache waf; do
    tokvar=CF_CACHE_TOKEN; [[ "${name}" == waf ]] && tokvar=CF_WAF_TOKEN
    tok="${!tokvar}"
    while IFS= read -r line; do
      path="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["path"])' "${line}")"
      python3 -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1])["body"]))' "${line}" > "${TMP}/body.json"
      if ${DRY_RUN}; then echo "  [dry-run] PATCH /zones/<zone>${path}"; continue; fi
      api "${tok}" PATCH "/zones/${CF_ZONE_ID}${path}" "${TMP}/body.json" \
        | python3 -c 'import json,sys; d=json.load(sys.stdin); print("  PATCH", sys.argv[1], "OK" if d.get("success") else "FAILED " + str(d.get("errors")))' "${path}"
    done < "${TMP}/${name}.patch"
  done
)
