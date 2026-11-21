#!/bin/bash
#
# check-cloud-vrsify.sh — stage 3 of run-release.sh: confirm that the upstream cloud vrsify has translated THIS
# release's variation_identity export, so that stage 4 (vrs-to-bq-table.sh) can load its output. Read-only.
#
# The clinvar-ingest Cloud Run job clinvar-ingest-vrsify (project clingen-dev, region us-east1) runs every 15
# minutes. It takes each release whose upstream stored procedures have finished, translates
# gs://<bucket>/<date>/dev/vi.jsonl.gz with vrs-python (on Cloud Batch, against a RefgetStore) and writes beside it:
#
#   vi-vrs-python.jsonl.gz            one {"in": <vi record>, "out": <VRS object>} line per input record
#   vi-vrs-python.provenance.json     inputs = [{uri, generation, md5, size}], output, transfers, libraries, ...
#
# The check passes only when both exist, the provenance names this release's vi.jsonl.gz as its one input with the
# md5 and size that object has NOW, and names vi-vrs-python.jsonl.gz as its output (with its current size, when the
# provenance records one). The generation is reported but need not match: a re-export of identical content (as
# happened for 2026-11-08) is a new generation with the same md5. A vi.jsonl.gz rewritten with different content
# after the cloud run fails the check, and the cloud job will not redo the release by itself: it takes each release
# once, and vrsify never replaces an existing output.
#
# USAGE:
#   ./src/scripts/check-cloud-vrsify.sh YYYY-MM-DD
#
# ENV OVERRIDES:
#   PROJECT_ID    GCP project (default clingen-dev)
#   BUCKET_NAME   GCS bucket (default clinvar-gkm)

set -o errexit
set -o nounset
set -o pipefail

PROJECT_ID="${PROJECT_ID:-clingen-dev}"
export CLOUDSDK_CORE_PROJECT="${PROJECT_ID}"
BUCKET_NAME="${BUCKET_NAME:-clinvar-gkm}"

DATE="${1:?Usage: $0 YYYY-MM-DD}"
if ! [[ "${DATE}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  echo "ERROR: invalid release date '${DATE}', expected YYYY-MM-DD" >&2
  exit 1
fi

prefix="gs://${BUCKET_NAME}/${DATE}/dev"
input="${prefix}/vi.jsonl.gz"
output="${prefix}/vi-vrs-python.jsonl.gz"
provenance="${prefix}/vi-vrs-python.provenance.json"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

# "generation,md5,size" of a GCS object, or empty if it does not exist. A comma, not a tab: an empty md5 (composite
# objects have none) must not shift the fields.
object_meta() {
  gcloud storage objects describe "$1" --format='value[separator=","](generation,md5_hash,size)' 2>/dev/null || true
}

in_meta="$(object_meta "${input}")"
[[ -n "${in_meta}" ]] || fail "${input} does not exist. The upstream stored procedures job exports it (or" \
  "stage 2 of run-release.sh)."
IFS=, read -r in_gen in_md5 in_size <<<"${in_meta}"

out_meta="$(object_meta "${output}")"
prov_json="$(gcloud storage cat "${provenance}" 2>/dev/null || true)"
if [[ -z "${out_meta}" || -z "${prov_json}" ]]; then
  fail "the cloud vrsify output for ${DATE} is not there yet (need ${output} and ${provenance})." \
    "The Cloud Run job clinvar-ingest-vrsify (clingen-dev, us-east1) runs every 15 minutes and takes a release once" \
    "its stored procedures have finished and ${input} has been written. Run this stage again" \
    "(run-release.sh ${DATE} ...) once both objects exist."
fi
IFS=, read -r _ _ out_size <<<"${out_meta}"

# Compare the provenance with the objects as they are now. Prints the verdict; exits 1 on a mismatch.
check_py="$(cat <<'PY'
import json, sys
inp, gen, md5, size, out, out_size = sys.argv[1:]
p = json.load(sys.stdin)
inputs = p.get('inputs') or []
uris = [i.get('uri') for i in inputs]
problems = []
if uris != [inp]:
    problems.append('its inputs are %s, not [%r]' % (uris, inp))
else:
    i = inputs[0]
    if not md5 or i.get('md5') != md5 or str(i.get('size')) != size:
        problems.append('it translated %s as md5 %s, size %s (generation %s), but that object is now md5 %s, size %s'
                        ' (generation %s)' % (inp, i.get('md5'), i.get('size'), i.get('generation'), md5 or 'none',
                                              size, gen))
if p.get('output') != out:
    problems.append('its output is %r, not %r' % (p.get('output'), out))
written = (p.get('transfers') or {}).get('output_bytes')
if written is not None and str(written) != out_size:
    problems.append('it wrote %s bytes, but %s is now %s bytes' % (written, out, out_size))
if problems:
    print('; '.join(problems))
    sys.exit(1)
note = ''
if str(inputs[0].get('generation')) != gen:
    note = '; %s was rewritten with the same content since (generation %s, translated generation %s)' % (
        inp, gen, inputs[0].get('generation'))
print('%s records, finished %s%s' % (p.get('records'), p.get('finished_at'), note))
PY
)"

if ! verdict="$(printf '%s' "${prov_json}" \
    | python3 -I -c "${check_py}" "${input}" "${in_gen}" "${in_md5}" "${in_size}" "${output}" "${out_size}" 2>&1)"; then
  fail "${provenance} does not match this release's export: ${verdict}." \
    "Do not load this output. The cloud job does not redo a release by itself; translate the current ${input}" \
    "again (upstream: clinvar-ingest vrsify-submit ${DATE} with --overwrite, or the local fallback in" \
    "src/vrsify/README.md), then run this stage again."
fi
echo "cloud vrsify output matches ${input}: ${output} (${verdict})"
