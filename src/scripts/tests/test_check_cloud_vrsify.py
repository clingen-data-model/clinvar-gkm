"""check-cloud-vrsify.sh (run-release.sh stage 3) must pass only when the cloud vrsify output is the translation of
the release's current vi.jsonl.gz.

Each test runs the real script with a fake gcloud on PATH that serves objects from a temporary directory: <path> holds
an object's content and <path>.meta its "generation,md5,size".
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
case "$1 $2" in
  "storage objects") uri="$4"; suffix=".meta" ;;
  "storage cat") uri="$3"; suffix="" ;;
  *) echo "fake gcloud: unexpected call: $*" >&2; exit 2 ;;
esac
f="$FAKE_GCS/${uri#gs://}$suffix"
[ -f "$f" ] || { echo "ERROR: $uri not found: 404." >&2; exit 1; }
cat "$f"
"""


@pytest.fixture
def gcs(tmp_path):
    root = tmp_path / "gcs"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gcloud = bin_dir / "gcloud"
    gcloud.write_text(FAKE_GCLOUD)
    gcloud.chmod(gcloud.stat().st_mode | stat.S_IEXEC)
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


def run(root):
    result = subprocess.run(
        [str(SCRIPT), DATE],
        capture_output=True,
        text=True,
        env={
            "HOME": os.environ.get("HOME", ""),
            "PATH": f"{root.parent / 'bin'}:/usr/bin:/bin",
            "FAKE_GCS": str(root),
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
