"""validate-bundle must pass a good bundle and fail every kind of bad one, since a pass lets a release upload.

The end-to-end tests run the real toolkit through validate-bundle.sh, and are skipped when --check-setup says it
isn't ready (no uv, or a worktree without the va-spec submodule).
"""

import gzip
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
WRAPPER = SCRIPTS / "validate-bundle.sh"
VERSION = json.loads((SCRIPTS.parents[1] / "schema/clinvar-gkm/clinvar-gkm-bundle.schema.json").read_text())[
    "properties"
]["schema_version"]["const"]

SUBMITTER = {"id": "clinvar.submitter:508969", "name": "Example Lab", "type": "Agent"}
SEQUENCE = {
    "moleculeType": "mRNA",
    "name": "NM_001034853.2",
    "refgetAccession": "SQ.I8T1QACHfV_rADwXq_tRoBbfhWN3nb-I",
    "residueAlphabet": "na",
    "type": "SequenceReference",
}


def write(tmp_path, bundle):
    path = tmp_path / "bundle.json.gz"
    with gzip.open(path, "wt") as f:
        json.dump(bundle, f)
    return path


def good():
    return {
        "schema_version": VERSION,
        "sequenceReference": {SEQUENCE["refgetAccession"]: SEQUENCE},
        "submitter": {SUBMITTER["id"]: SUBMITTER},
    }


def test_records_keep_keys_containing_dots(tmp_path):
    pytest.importorskip("ijson")
    spec = importlib.util.spec_from_file_location("validate_bundle", SCRIPTS / "validate-bundle.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = write(
        tmp_path,
        {
            "schema_version": VERSION,
            "location": {"ga4gh:SL.x": {"a": {"b": 1}}},
            "condition": {"clinvar.trait:1": {"c": [1, {"d": 2}]}},
            "scv": {"clinvar.submission:SCV1.2": {"e": 3}},
        },
    )
    seen = []
    assert list(module.records(path, seen)) == [
        ("schema_version", None, VERSION),
        ("location", "ga4gh:SL.x", {"a": {"b": 1}}),
        ("condition", "clinvar.trait:1", {"c": [1, {"d": 2}]}),
        ("scv", "clinvar.submission:SCV1.2", {"e": 3}),
    ]
    assert seen == ["location", "condition", "scv"]


@pytest.fixture
def stubbed_release(tmp_path):
    """The real release-gkm-delta.sh among stubs that log their name, so nothing can reach GCS or R2."""
    scripts = tmp_path / "repo/src/scripts"
    scripts.mkdir(parents=True)
    (scripts / "release-gkm-delta.sh").write_text((SCRIPTS / "release-gkm-delta.sh").read_text())
    (scripts / "release-gkm-delta.sh").chmod(0o755)
    log = tmp_path / "calls.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = f'#!/bin/sh\necho "$(basename "$0")" >> "{log}"\n'
    for path in (bin_dir / "gsutil", scripts / "export-gkm-dicts.sh", scripts / "upload-gkm-delta-to-r2.sh"):
        path.write_text(stub)
        path.chmod(0o755)
    # release-gkm-delta.sh runs the two .py files with python3, so they log from Python instead.
    py = f'import os, sys\nopen({str(log)!r}, "a").write(os.path.basename(sys.argv[0]) + "\\n")\n'
    (scripts / "assemble-gkm-dicts.py").write_text(py)
    (scripts / "build-delta-manifest.py").write_text(py)

    def run(validate_exit, *args):
        (scripts / "validate-bundle.sh").write_text(f"{stub}exit {validate_exit}\n")
        (scripts / "validate-bundle.sh").chmod(0o755)
        log.write_text("")
        result = subprocess.run(
            [scripts / "release-gkm-delta.sh", "2026-01-01", "v0", *args],
            capture_output=True,
            text=True,
            env={"PATH": f"{bin_dir}:/usr/bin:/bin", "STAGE_DIR": str(tmp_path)},
        )
        return result.returncode, result.stdout + result.stderr, log.read_text().split()

    return run


def test_failed_validation_blocks_the_upload(stubbed_release):
    code, out, calls = stubbed_release(1)
    assert code == 1 and "nothing was uploaded" in out
    assert "validate-bundle.sh" in calls
    assert "upload-gkm-delta-to-r2.sh" not in calls


def test_passed_validation_uploads_after_it(stubbed_release):
    code, _, calls = stubbed_release(0)
    assert code == 0
    assert calls.index("assemble-gkm-dicts.py") < calls.index("validate-bundle.sh") < calls.index("upload-gkm-delta-to-r2.sh")


def test_build_then_publish_validates_once_and_uploads_once(stubbed_release):
    """The two calls run-release.sh makes: --no-upload before R2 changes, then --start-step=3 after the monthly."""
    code, _, calls = stubbed_release(0, "--no-upload")
    assert code == 0 and "validate-bundle.sh" in calls and "upload-gkm-delta-to-r2.sh" not in calls
    code, _, calls = stubbed_release(1, "--start-step=3")
    assert code == 0 and calls == ["build-delta-manifest.py", "upload-gkm-delta-to-r2.sh"]


@pytest.fixture(scope="module")
def toolkit():
    if subprocess.run([WRAPPER, "--check-setup"], capture_output=True).returncode != 0:
        pytest.skip("validate-bundle.sh --check-setup is not ready")


def validate(path):
    result = subprocess.run([WRAPPER, str(path), "--workers", "1"], capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def test_good_bundle_passes(tmp_path, toolkit):
    code, out = validate(write(tmp_path, good()))
    assert code == 0 and out.rstrip().endswith("PASS")
    assert "records: 2  failing: 0" in out


def test_bad_record_fails_and_is_named(tmp_path, toolkit):
    bundle = good()
    bundle["submitter"]["clinvar.submitter:2"] = {"id": "clinvar.submitter:2", "type": "NotAType"}
    code, out = validate(write(tmp_path, bundle))
    assert code == 1 and "failing: 1" in out
    assert "submitter/clinvar.submitter:2" in out


def test_wrong_schema_version_fails(tmp_path, toolkit):
    bundle = good()
    bundle["schema_version"] = "0.0.0"
    code, out = validate(write(tmp_path, bundle))
    assert code == 1 and "MISMATCH" in out


def test_empty_section_fails(tmp_path, toolkit):
    bundle = good()
    bundle["condition"] = {}
    code, out = validate(write(tmp_path, bundle))
    assert code == 1 and "EMPTY sections: condition" in out


def test_bundle_with_no_records_fails(tmp_path, toolkit):
    code, out = validate(write(tmp_path, {"schema_version": VERSION}))
    assert code == 1 and out.rstrip().endswith("FAIL")


def test_unreadable_bundle_fails(tmp_path, toolkit):
    path = tmp_path / "bundle.json.gz"
    with gzip.open(path, "wt") as f:
        f.write('{"schema_version": "' + VERSION + '", "submitter": {"a"')
    code, _ = validate(path)
    assert code != 0
