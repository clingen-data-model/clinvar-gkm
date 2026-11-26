"""check-cloud-vrsify.sh (run-release.sh step 1) must pass only when the cloud vrsify output is the translation of
the release's current vi.jsonl.gz, and run-release.sh must start at that check, run it before any gkm_vrs load, and
never run the stages clinvar-ingest now runs (diff, variation_identity, export, translation).

Each test runs the real scripts with fakes on PATH. The fake gcloud serves objects from a temporary directory (<path>
holds an object's content and <path>.meta its "generation,md5,size"); the fake gcloud and bq log every call, and the
fake bq prints $FAKE_BQ_OUT (if set) and exits with $FAKE_BQ_RC (default 1), which stops run-release.sh at its first
BigQuery call.
"""

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "check-cloud-vrsify.sh"
DATE = "2026-11-15"
PREFIX = f"gs://clinvar-gkm/{DATE}/dev"
INPUT = f"{PREFIX}/vi.jsonl.gz"
OUTPUT = f"{PREFIX}/vi-vrs-python.jsonl.gz"

FAKE_GCLOUD = """#!/bin/sh
# gcloud storage objects describe <uri> --format=... | gcloud storage cat <uri>
echo "gcloud GKS_FULL=${GKS_FULL:-} $*" >> "${FAKE_LOG:-/dev/null}"
case "$1 $2" in
  "storage objects") uri="$4"; suffix=".meta" ;;
  "storage cat") uri="$3"; suffix="" ;;
  *) echo "fake gcloud: unexpected call: $*" >&2; exit 2 ;;
esac
f="$FAKE_GCS/${uri#gs://}$suffix"
[ -f "$f" ] || { echo "ERROR: $uri not found: 404." >&2; exit 1; }
cat "$f"
"""

FAKE_BQ = """#!/bin/sh
echo "bq $*" >> "${FAKE_LOG:-/dev/null}"
case " $* " in *" ls "*) echo "  clinvar_2026_11_15_v2_7_1" ;; esac
[ -n "${FAKE_BQ_OUT:-}" ] && printf '%s\\n' "$FAKE_BQ_OUT"
exit "${FAKE_BQ_RC:-1}"
"""

# run-release.sh checks that its python3 has orjson before it starts; the rest is the real python3.
FAKE_PYTHON3 = """#!/bin/sh
[ "$1 $2" = "-c import orjson" ] && exit 0
exec /usr/bin/python3 "$@"
"""


@pytest.fixture
def gcs(tmp_path):
    root = tmp_path / "gcs"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, text in (("gcloud", FAKE_GCLOUD), ("bq", FAKE_BQ), ("python3", FAKE_PYTHON3)):
        fake = bin_dir / name
        fake.write_text(text)
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    return root


def put(root, uri, meta=None, content=""):
    path = root / uri.removeprefix("gs://")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    if meta is not None:
        Path(f"{path}.meta").write_text(meta + "\n")


def provenance(input_meta=("100", "abc==", 23062), uri=INPUT, output=OUTPUT, output_bytes=86508):
    generation, md5, size = input_meta
    record = {
        "inputs": [{"uri": uri, "generation": int(generation), "md5": md5, "size": size}],
        "output": output,
        "records": 749,
        "finished_at": "2026-11-20T06:46:37+00:00",
    }
    if output_bytes is not None:
        record["transfers"] = {"input_bytes": size, "output_bytes": output_bytes}
    return json.dumps(record)


def release(root, input_meta="100,abc==,23062", output_meta="7,out==,86508", prov=None):
    if input_meta:
        put(root, INPUT, input_meta)
    if output_meta:
        put(root, OUTPUT, output_meta)
    if prov is not False:
        put(root, f"{PREFIX}/vi-vrs-python.provenance.json", content=prov or provenance())


def run(root, script=SCRIPT, *args, **env):
    result = subprocess.run(
        [str(script), DATE, *args],
        capture_output=True,
        text=True,
        env={
            "HOME": os.environ.get("HOME", ""),
            "PATH": f"{root.parent / 'bin'}:/usr/bin:/bin",
            "FAKE_GCS": str(root),
            "FAKE_LOG": str(root.parent / "calls.log"),
            **env,
        },
    )
    return result.returncode, result.stdout + result.stderr


def test_matching_provenance_passes(gcs):
    release(gcs)
    code, out = run(gcs)
    assert code == 0, out
    assert "749 records" in out and "rewritten" not in out


def test_reexport_with_same_content_passes_and_says_so(gcs):
    release(gcs, input_meta="200,abc==,23062")
    code, out = run(gcs)
    assert code == 0, out
    assert "rewritten with the same content" in out


def test_changed_input_content_stops(gcs):
    release(gcs, input_meta="200,changed==,23062")
    code, out = run(gcs)
    assert code == 1
    assert "does not match this release's export" in out


def test_changed_input_size_stops(gcs):
    release(gcs, input_meta="100,abc==,99")
    code, out = run(gcs)
    assert code == 1
    assert "does not match this release's export" in out


def test_input_without_md5_stops(gcs):
    release(gcs, input_meta="100,,23062")
    code, out = run(gcs)
    assert code == 1
    assert "md5 none" in out


def test_other_input_uri_stops(gcs):
    release(gcs, prov=provenance(uri=f"{PREFIX}/vi-000000000000.jsonl.gz"))
    code, out = run(gcs)
    assert code == 1
    assert "its inputs are" in out


def test_other_output_uri_stops(gcs):
    release(gcs, prov=provenance(output=f"{PREFIX}/elsewhere.jsonl.gz"))
    code, out = run(gcs)
    assert code == 1
    assert "its output is" in out


def test_replaced_output_stops(gcs):
    release(gcs, output_meta="8,other==,1234")
    code, out = run(gcs)
    assert code == 1
    assert "it wrote 86508 bytes" in out


def test_provenance_without_transfers_skips_the_size_check(gcs):
    release(gcs, output_meta="8,other==,1234", prov=provenance(output_bytes=None))
    code, out = run(gcs)
    assert code == 0, out


def test_missing_output_stops(gcs):
    release(gcs, output_meta=None)
    code, out = run(gcs)
    assert code == 1
    assert "is not there yet" in out


def test_missing_provenance_stops(gcs):
    release(gcs, prov=False)
    code, out = run(gcs)
    assert code == 1
    assert "is not there yet" in out


def test_missing_input_stops(gcs):
    release(gcs, input_meta=None)
    code, out = run(gcs)
    assert code == 1
    assert f"{INPUT} does not exist" in out


def test_bad_date_stops(gcs):
    result = subprocess.run([str(SCRIPT), "2026-11"], capture_output=True, text=True)
    assert result.returncode == 1
    assert "invalid release date" in result.stderr


# --- run-release.sh: four steps, starting at the check; the upstream stages are gone -----------------------------

RUN_RELEASE = SCRIPT.parent / "run-release.sh"
UPSTREAM_WORK = ("dataset_diff_on", "variation_identity", "variation_vrs_changed", "extract")


def release_run(root, *args, **env):
    """Run run-release.sh in dry-run; returns (exit code, output, [bq calls], [gcloud calls])."""
    code, out = run(root, RUN_RELEASE, "--dry-run", *args, **env)
    log = root.parent / "calls.log"
    calls = log.read_text().splitlines() if log.exists() else []
    bq = [c for c in calls if c.startswith("bq ")]
    assert not any(w in c for c in bq for w in UPSTREAM_WORK), bq  # never run here any more
    return code, out, bq, [c for c in calls if c.startswith("gcloud ")]


def test_release_starts_at_the_check(gcs):
    release(gcs)
    code, out, bq, _ = release_run(gcs)
    assert code != 0  # the fake bq fails the lookup check, the first BigQuery call after the vrsify check
    assert "start-step=1" in out and "[1/4] check-cloud-vrsify.sh" in out and "matches" in out
    assert "[2/4] check-clinsig-lookup.sh" in out and "could not read" in out
    assert len(bq) == 1 and "gkm_pipeline_version" not in bq[0], bq


def test_an_outdated_lookup_stops_the_release_before_the_version_stamp(gcs):
    release(gcs)
    code, out, bq, _ = release_run(gcs, FAKE_BQ_RC="0", FAKE_BQ_OUT="problem\nsci t1: retired system name")
    assert code == 1
    assert "does not carry the codings" in out and "sci t1: retired system name" in out
    assert len(bq) == 1 and "gkm_pipeline_version" not in bq[0], bq


def test_release_stops_fast_without_the_cloud_output(gcs):
    release(gcs, output_meta=None)
    code, out, bq, _ = release_run(gcs)
    assert code == 1
    assert "is not there yet" in out
    assert bq == []


def test_start_step_2_still_runs_the_check(gcs):
    release(gcs, input_meta="200,changed==,23062")
    code, out, bq, _ = release_run(gcs, "--start-step", "2")
    assert code == 1
    assert "does not match this release's export" in out
    assert bq == []


def test_full_procs_checks_then_loads_the_cloud_output_with_full_procs(gcs):
    release(gcs)
    code, out, bq, gcloud = release_run(gcs, "--full-procs", FAKE_BQ_RC="0")
    assert code != 0  # the fake gcloud refuses the Cloud Run transform that starts vrs-to-bq-table.sh
    assert "[2/4] vrs-to-bq-table.sh" in out
    assert "gkm_pipeline_version" in " ".join(bq)
    jobs = [c for c in gcloud if " run jobs execute " in c]
    assert len(jobs) == 1 and "GKS_FULL=true" in jobs[0] and OUTPUT in jobs[0], gcloud


@pytest.mark.parametrize("step", ["3", "4"])
def test_later_start_skips_the_check_and_the_load(gcs, step):
    code, out, bq, gcloud = release_run(gcs, "--start-step", step)
    assert code != 0  # the fake bq fails the dataset lookup that steps 3 and 4 start with
    assert gcloud == []
    assert bq and bq[0].startswith("bq ls") and "gkm_pipeline_version" not in " ".join(bq), bq


@pytest.mark.parametrize("flag", ["--full", "--with-upstream-stages", "--allow-unchecked-vrs"])
def test_removed_flags_are_unknown(gcs, flag):
    code, out, bq, gcloud = release_run(gcs, flag)
    assert code == 1
    assert f"unknown flag: {flag}" in out
    assert bq == [] and gcloud == []


@pytest.mark.parametrize("step", ["0", "5", "6", "x"])
def test_start_step_is_1_to_4(gcs, step):
    code, out, bq, gcloud = release_run(gcs, "--start-step", step)
    assert code == 1
    assert "--start-step must be 1-4" in out
    assert bq == [] and gcloud == []
