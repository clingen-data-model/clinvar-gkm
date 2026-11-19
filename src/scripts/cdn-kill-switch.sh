#!/bin/bash
#
# cdn-kill-switch.sh — one-command pause for public reads of data.clinvar-gkm.org.
#
# Flips a single Cloudflare WAF custom rule that blocks every request to data.clinvar-gkm.org at the edge
# (cached hits included), so no public read reaches R2 and Class B costs stop. Nothing in R2 changes; turning
# the switch off restores service within seconds. See ADR 0005 ("Spend alert and kill switch").
#
# USAGE:
#   ./src/scripts/cdn-kill-switch.sh status   # show the rule and probe the public URL
#   ./src/scripts/cdn-kill-switch.sh on       # block all public reads (creates the rule if missing)
#   ./src/scripts/cdn-kill-switch.sh off      # restore public reads
#   ./src/scripts/cdn-kill-switch.sh init     # create the rule DISABLED, if missing (safe to re-run)
#
# CREDENTIALS (never printed): read from $CF_ENV_FILE (default ~/.config/clinvar-gkm/cloudflare.env):
#   CF_ZONE_ID    the clinvar-gkm.org zone id (shared with the purge flow)
#   CF_WAF_TOKEN  an API token scoped to zone clinvar-gkm.org with
#                 Zone → Zone WAF → Edit  and  Zone → Firewall Services → Edit
#
# Only the rule this script owns is ever modified. It is found by its exact description and is never
# created twice. The zone's rate-limiting rule lives in a different phase and is not touched.

set -o errexit -o nounset -o pipefail

API="https://api.cloudflare.com/client/v4"
PHASE="http_request_firewall_custom"
HOST="data.clinvar-gkm.org"
PROBE_URL="https://${HOST}/v1/index.json"
DESC="KILL SWITCH - block all public data (cdn-kill-switch.sh)"
EXPR="(http.host eq \"${HOST}\")"

usage() { sed -n '9,13p' "$0" | sed 's/^# //'; exit 2; }
[ $# -eq 1 ] || usage
CMD="$1"
case "$CMD" in status|on|off|init) ;; *) usage ;; esac

command -v jq >/dev/null || { echo "❌ jq is required" >&2; exit 1; }
CF_ENV_FILE="${CF_ENV_FILE:-$HOME/.config/clinvar-gkm/cloudflare.env}"
# shellcheck disable=SC1090
[ -f "$CF_ENV_FILE" ] && source "$CF_ENV_FILE"
: "${CF_ZONE_ID:?CF_ZONE_ID not set (expected in $CF_ENV_FILE)}"
: "${CF_WAF_TOKEN:?CF_WAF_TOKEN not set (expected in $CF_ENV_FILE); see the header for its permissions}"

# cf METHOD PATH [JSON] -> prints the response body; exits on an API error.
cf() {
  local method="$1" path="$2" body="${3:-}" out
  if [ -n "$body" ]; then
    out=$(curl -sS -X "$method" "${API}${path}" -H "Authorization: Bearer ${CF_WAF_TOKEN}" \
      -H "Content-Type: application/json" --data "$body")
  else
    out=$(curl -sS -X "$method" "${API}${path}" -H "Authorization: Bearer ${CF_WAF_TOKEN}")
  fi
  printf '%s' "$out"
}

api_ok() { printf '%s' "$1" | jq -e '.success == true' >/dev/null; }
api_err() { printf '%s' "$1" | jq -r '[.errors[]? | "\(.code): \(.message)"] | join("; ")'; }

rule_json() {  # rule_json true|false
  jq -nc --arg d "$DESC" --arg e "$EXPR" --argjson en "$1" \
    '{description: $d, expression: $e, action: "block", enabled: $en}'
}

# Load the zone's custom-rules entry point. Sets RULESET_ID ("" if none), RULE_ID, RULE_ENABLED.
load() {
  local resp
  resp=$(cf GET "/zones/${CF_ZONE_ID}/rulesets/phases/${PHASE}/entrypoint")
  RULESET_ID="" RULE_ID="" RULE_ENABLED=""
  if api_ok "$resp"; then
    RULESET_ID=$(printf '%s' "$resp" | jq -r '.result.id')
    RULE_ID=$(printf '%s' "$resp" | jq -r --arg d "$DESC" '[.result.rules[]? | select(.description == $d)][0].id // ""')
    RULE_ENABLED=$(printf '%s' "$resp" | jq -r --arg d "$DESC" '[.result.rules[]? | select(.description == $d)][0].enabled // ""')
  elif printf '%s' "$resp" | jq -e \
       '[.errors[]? | select(.code == 10003 or (.message | test("could not find"; "i")))] | length > 0' >/dev/null; then
    :  # no custom-rules entry point yet; it is created on demand
  else
    echo "❌ Cloudflare API: $(api_err "$resp")" >&2
    echo "   (an authentication error means CF_WAF_TOKEN lacks the permissions listed in the header)" >&2
    exit 1
  fi
}

# Create the rule (first in the phase) with the given enabled state.
create() {
  local enabled="$1" resp
  if [ -z "$RULESET_ID" ]; then
    resp=$(cf POST "/zones/${CF_ZONE_ID}/rulesets" "$(jq -nc --arg p "$PHASE" --argjson r "$(rule_json "$enabled")" \
      '{name: "default", kind: "zone", phase: $p, rules: [$r]}')")
  else
    resp=$(cf POST "/zones/${CF_ZONE_ID}/rulesets/${RULESET_ID}/rules" \
      "$(rule_json "$enabled" | jq -c '. + {position: {before: ""}}')")
  fi
  api_ok "$resp" || { echo "❌ create failed: $(api_err "$resp")" >&2; exit 1; }
  load
}

set_enabled() {
  local enabled="$1" resp
  resp=$(cf PATCH "/zones/${CF_ZONE_ID}/rulesets/${RULESET_ID}/rules/${RULE_ID}" "$(rule_json "$enabled")")
  api_ok "$resp" || { echo "❌ update failed: $(api_err "$resp")" >&2; exit 1; }
  load
}

probe() {
  local code
  local code note=""
  code=$(curl -s -o /dev/null -w '%{http_code}' -A "clinvar-gkm-kill-switch" "$PROBE_URL" || true)
  case "$code" in 403) note="(blocked)" ;; 200) note="(serving)" ;; esac
  echo "  probe ${PROBE_URL} -> HTTP ${code} ${note}"
}

report() {
  if [ -z "$RULE_ID" ]; then
    echo "Kill switch: NOT CREATED (run '$0 init')"
  elif [ "$RULE_ENABLED" = "true" ]; then
    echo "Kill switch: ON — all public reads of ${HOST} are blocked"
  else
    echo "Kill switch: OFF — ${HOST} is serving normally"
  fi
  probe
}

load
case "$CMD" in
  status) ;;
  init)   [ -n "$RULE_ID" ] || create false ;;
  on)     if [ -z "$RULE_ID" ]; then create true; elif [ "$RULE_ENABLED" != "true" ]; then set_enabled true; fi ;;
  off)    if [ -n "$RULE_ID" ] && [ "$RULE_ENABLED" = "true" ]; then set_enabled false; fi ;;
esac
# give the edge a moment before probing after a change
[ "$CMD" = status ] || sleep 5
report
