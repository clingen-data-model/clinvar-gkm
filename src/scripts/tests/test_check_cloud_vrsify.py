"""check-cloud-vrsify.sh (run-release.sh stage 3) must pass only when the cloud vrsify output is the translation of
the release's current vi.jsonl.gz, and run-release.sh must start at that check, run it before any gkm_vrs load, and
stop --full there.

Each test runs the real scripts with fakes on PATH. The fake gcloud serves objects from a temporary directory (<path>
holds an object's content and <path>.meta its "generation,md5,size"); the fake gcloud and bq log every call, and the
fake bq exits with $FAKE_BQ_RC (default 1), which stops run-release.sh at its first BigQuery call.
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


# --- run-release.sh: where the release starts, the check before the gkm_vrs load, --full ------------------------

RUN_RELEASE = SCRIPT.parent / "run-release.sh"


def release_run(root, *args, **env):
    """Run run-release.sh in dry-run; returns (exit code, output, [bq calls], [gcloud calls])."""
    code, out = run(root, RUN_RELEASE, "--dry-run", *args, **env)
    log = root.parent / "calls.log"
    calls = log.read_text().splitlines() if log.exists() else []
    return code, out, [c for c in calls if c.startswith("bq ")], [c for c in calls if c.startswith("gcloud ")]


def test_release_starts_at_the_check_by_default(gcs):
    release(gcs)
    code, out, bq, gcloud = release_run(gcs)
    assert code != 0  # the fake bq fails the version stamp, the first BigQuery call after the check
    assert "start-step=3" in out and "matches" in out
    assert len(bq) == 1 and "gkm_pipeline_version" in bq[0], bq


def test_release_stops_fast_without_the_cloud_output(gcs):
    release(gcs, output_meta=None)
    code, out, bq, _ = release_run(gcs)
    assert code == 1
    assert "is not there yet" in out
    assert bq == []


def test_with_upstream_stages_starts_at_stage_0(gcs):
    code, out, bq, _ = release_run(gcs, "--with-upstream-stages")
    assert code != 0
    assert "start-step=1" in out
    assert len(bq) == 1 and "dataset_diff_on" in bq[0], bq


@pytest.mark.parametrize("step", ["1", "2"])
def test_upstream_stages_need_the_opt_in(gcs, step):
    code, out, bq, gcloud = release_run(gcs, "--start-step", step)
    assert code == 1
    assert "--with-upstream-stages" in out
    assert bq == [] and gcloud == []


def test_with_upstream_stages_rejects_a_later_start(gcs):
    code, out, bq, gcloud = release_run(gcs, "--with-upstream-stages", "--start-step", "3")
    assert code == 1
    assert "starts after them" in out
    assert bq == [] and gcloud == []


def test_full_stops_at_stage_3(gcs):
    release(gcs)
    code, out, bq, gcloud = release_run(gcs, "--full")
    assert code == 1
    assert "--full stops at stage 3" in out
    assert bq == [] and gcloud == []


def test_full_with_upstream_stages_rebuilds_then_stops_at_stage_3(gcs):
    release(gcs)
    code, out, bq, gcloud = release_run(gcs, "--full", "--with-upstream-stages", FAKE_BQ_RC="0")
    assert code == 1
    assert "--full stops at stage 3" in out
    queries = " ".join(bq)
    assert "dataset_diff_on" in queries and "variation_identity`(DATE" in queries
    assert "variation_identity_incremental" not in queries
    assert any("extract" in c and "vi-*.jsonl.gz" in c for c in bq), bq
    assert "gkm_pipeline_version" not in queries and gcloud == []


@pytest.mark.parametrize("step", ["4", "5"])
def test_full_rejects_a_start_after_stage_3(gcs, step):
    code, out, bq, gcloud = release_run(gcs, "--full", "--start-step", step)
    assert code == 1
    assert "--full stops at stage 3" in out and "--full-procs" in out
    assert bq == [] and gcloud == []


def test_start_step_4_runs_the_check(gcs):
    release(gcs, input_meta="200,changed==,23062")
    code, out, bq, _ = release_run(gcs, "--start-step", "4")
    assert code == 1
    assert "does not match this release's export" in out
    assert bq == []


def test_allow_unchecked_vrs_skips_the_check(gcs):
    code, out, bq, gcloud = release_run(gcs, "--start-step", "4", "--allow-unchecked-vrs")
    assert code != 0
    assert "NOT checking" in out
    assert gcloud == []
    assert len(bq) == 1 and "gkm_pipeline_version" in bq[0], bq


def test_allow_unchecked_vrs_rejects_a_start_after_stage_4(gcs):
    code, out, bq, gcloud = release_run(gcs, "--start-step", "5", "--allow-unchecked-vrs")
    assert code == 1
    assert "starts after it" in out
    assert bq == [] and gcloud == []


def test_full_procs_checks_then_loads_the_cloud_output_with_full_procs(gcs):
    release(gcs)
    code, out, bq, gcloud = release_run(gcs, "--full-procs", FAKE_BQ_RC="0")
    assert code != 0  # the fake gcloud refuses the Cloud Run transform that starts stage 4
    assert "gkm_pipeline_version" in " ".join(bq)
    jobs = [c for c in gcloud if " run jobs execute " in c]
    assert len(jobs) == 1 and "GKS_FULL=true" in jobs[0] and OUTPUT in jobs[0], gcloud
