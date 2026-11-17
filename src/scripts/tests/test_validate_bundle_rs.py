"""validate-bundle.sh --engine rs must give the toolkit's verdict, read only the assembler's layout, and gate every full.

The end-to-end tests run the real engines through validate-bundle.sh, and are skipped when --check-setup says an engine
isn't ready (no uv, or a worktree without the va-spec submodule). The equivalence test runs both engines on a bundle
with planted violations and needs both.
"""

import copy
import gzip
import json
import re
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


def good():
    return {
        "schema_version": VERSION,
        "sequenceReference": {SEQUENCE["refgetAccession"]: SEQUENCE},
        "submitter": {SUBMITTER["id"]: SUBMITTER},
    }


def assembled(bundle):
    """The bundle as assemble-gkm-dicts.py writes it: one compact record per line."""
    lines = ["{\n", f'  "schema_version": {json.dumps(bundle["schema_version"])}']
    for section, records in bundle.items():
        if section == "schema_version":
            continue
        body = ",\n".join(f"    {json.dumps(k)}: {json.dumps(r, separators=(',', ':'))}" for k, r in records.items())
        lines.append(f',\n  "{section}": {{\n' + body + ("\n" if body else "") + "  }")
    return "".join(lines) + "\n}\n"


def write(tmp_path, text):
    path = tmp_path / "bundle.json.gz"
    with gzip.open(path, "wt") as f:
        f.write(text)
    return path


def ready(engine):
    if subprocess.run([WRAPPER, "--check-setup", "--engine", engine], capture_output=True).returncode != 0:
        pytest.skip(f"validate-bundle.sh --check-setup --engine {engine} is not ready")


@pytest.fixture(scope="module")
def rs():
    ready("rs")


@pytest.fixture(scope="module")
def toolkit():
    ready("toolkit")


def validate(path, engine="rs"):
    result = subprocess.run([WRAPPER, str(path), "--engine", engine, "--workers", "1", "--max-print", "100"],
                            capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def failing_keys(out):
    return sorted(re.findall(r"^  FAIL (\S+): ", out, flags=re.MULTILINE))


def test_good_bundle_passes(tmp_path, rs):
    code, out = validate(write(tmp_path, assembled(good())))
    assert code == 0 and out.rstrip().endswith("PASS"), out
    assert "engine: rs" in out and "records: 2  failing: 0" in out


def test_bad_record_fails_and_is_named(tmp_path, rs):
    bundle = good()
    bundle["submitter"]["clinvar.submitter:2"] = {"id": "clinvar.submitter:2", "type": "NotAType"}
    code, out = validate(write(tmp_path, assembled(bundle)))
    assert code == 1 and "failing: 1" in out
    assert failing_keys(out) == ["submitter/clinvar.submitter:2"]


def test_wrong_schema_version_fails(tmp_path, rs):
    bundle = good()
    bundle["schema_version"] = "0.0.0"
    code, out = validate(write(tmp_path, assembled(bundle)))
    assert code == 1 and "MISMATCH" in out


def test_empty_section_fails(tmp_path, rs):
    bundle = good()
    bundle["condition"] = {}
    code, out = validate(write(tmp_path, assembled(bundle)))
    assert code == 1 and "EMPTY sections: condition" in out


def test_bundle_with_no_records_fails(tmp_path, rs):
    code, out = validate(write(tmp_path, assembled({"schema_version": VERSION})))
    assert code == 1 and out.rstrip().endswith("FAIL")


def test_repeated_key_fails(tmp_path, rs):
    text = assembled(good()).replace(
        f"    {json.dumps(SUBMITTER['id'])}:", f"    {json.dumps(SUBMITTER['id'])}: {{}},\n    {json.dumps(SUBMITTER['id'])}:"
    )
    code, out = validate(write(tmp_path, text))
    assert code == 1 and "2 record lines hold 1 distinct records" in out


@pytest.mark.parametrize(
    "text",
    [
        json.dumps(good()),  # one line: the toolkit reads it, rs must not pretend to
        json.dumps(good(), indent=2),  # a record spread over several lines
        json.dumps(good(), indent=4),  # records indented as the assembler indents them, but not one per line
        assembled(good())[:-3],  # truncated before the closing brace
    ],
    ids=["one-line", "indent-2", "indent-4", "truncated"],
)
def test_other_layouts_are_rejected_not_skipped(tmp_path, rs, text):
    code, out = validate(write(tmp_path, text))
    assert code != 0 and "PASS" not in out


def test_unreadable_bundle_fails(tmp_path, rs):
    path = tmp_path / "bundle.json.gz"
    path.write_bytes(gzip.compress(assembled(good()).encode())[:-20])
    code, _ = validate(path)
    assert code != 0


def planted():
    """A good bundle plus one violation of each kind in the two small sections, with distinct keys."""
    bundle = good()

    def submitter(key, **change):
        record = dict(SUBMITTER, id=key, **change)
        bundle["submitter"][key] = {k: v for k, v in record.items() if v is not None}

    def sequence(tag, **change):
        key = f"SQ.{tag:A<32}"  # a well-formed refget accession, so only the planted change can fail
        record = dict(SEQUENCE, refgetAccession=key, **change)
        bundle["sequenceReference"][key] = {k: v for k, v in record.items() if v is not None}

    submitter("clinvar.submitter:1")  # valid
    submitter("clinvar.submitter:2", type="NotAType")
    submitter("clinvar.submitter:3", bogus=1)  # unknown property
    submitter("clinvar.submitter:4", name=123)  # wrong type
    submitter("not-a-submitter-key")  # key outside the section's patternProperties
    sequence("valid")
    sequence("alphabet", residueAlphabet="xyz")  # not in the enum
    sequence("notype", type=None)  # missing required type
    sequence("extension", extensions=[{"name": "x"}])  # extension without a value
    bundle["sequenceReference"][f"SQ.{'list':A<32}"] = [copy.deepcopy(SEQUENCE)]  # not an object
    return bundle


PLANTED = sorted(
    ["submitter/clinvar.submitter:2", "submitter/clinvar.submitter:3", "submitter/clinvar.submitter:4",
     "submitter/not-a-submitter-key"]
    + [f"sequenceReference/SQ.{tag:A<32}" for tag in ("alphabet", "notype", "extension", "list")]
)


def test_engines_name_the_same_failing_records(tmp_path, rs, toolkit):
    path = write(tmp_path, assembled(planted()))
    rs_code, rs_out = validate(path, "rs")
    tk_code, tk_out = validate(path, "toolkit")
    assert rs_code == tk_code == 1, rs_out + tk_out
    assert failing_keys(rs_out) == failing_keys(tk_out) == PLANTED, rs_out + tk_out
    counts = re.compile(r"records: \S+  failing: \S+")
    assert counts.search(rs_out).group() == counts.search(tk_out).group()


@pytest.fixture
def stubbed_full_release(tmp_path):
    """The real release-gkm.sh among stubs that log their name and arguments, so nothing can reach GCS or R2."""
    scripts = tmp_path / "repo/src/scripts"
    scripts.mkdir(parents=True)
    (scripts / "release-gkm.sh").write_text((SCRIPTS / "release-gkm.sh").read_text())
    (scripts / "release-gkm.sh").chmod(0o755)
    log = tmp_path / "calls.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = f'#!/bin/sh\necho "$(basename "$0") $*" >> "{log}"\n'
    for path in (bin_dir / "gsutil", scripts / "export-gkm-dicts.sh", scripts / "upload-gkm-to-r2.sh"):
        path.write_text(stub)
        path.chmod(0o755)
    # release-gkm.sh runs the assembler with python3, so it logs from Python instead.
    (scripts / "assemble-gkm-dicts.py").write_text(
        f'import os, sys\nopen({str(log)!r}, "a").write(os.path.basename(sys.argv[0]) + "\\n")\n'
    )

    def run(validate_exit, *args):
        (scripts / "validate-bundle.sh").write_text(f"{stub}exit {validate_exit}\n")
        (scripts / "validate-bundle.sh").chmod(0o755)
        log.write_text("")
        result = subprocess.run(
            [scripts / "release-gkm.sh", "2026-01-01", "v0", *args],
            capture_output=True,
            text=True,
            env={"PATH": f"{bin_dir}:/usr/bin:/bin", "STAGE_DIR": str(tmp_path)},
        )
        calls = [line.split() for line in log.read_text().splitlines()]
        return result.returncode, result.stdout + result.stderr, calls

    return run


def names(calls):
    return [c[0] for c in calls]


def test_full_is_validated_with_rs_before_upload(stubbed_full_release):
    code, _, calls = stubbed_full_release(0, "--weekly")
    assert code == 0
    assert names(calls) == ["gsutil", "export-gkm-dicts.sh", "assemble-gkm-dicts.py", "validate-bundle.sh",
                            "upload-gkm-to-r2.sh"]
    assert calls[3][-2:] == ["--engine", "rs"]


def test_failed_full_validation_blocks_the_upload(stubbed_full_release):
    code, out, calls = stubbed_full_release(1, "--month-label=2026-01")
    assert code == 1 and "nothing was uploaded" in out
    assert "upload-gkm-to-r2.sh" not in names(calls)


def test_full_build_then_publish(stubbed_full_release):
    """The two calls run-release.sh makes: --no-upload before R2 changes, then --start-step=3 after the rollover."""
    code, _, calls = stubbed_full_release(0, "--weekly", "--no-upload")
    assert code == 0 and "validate-bundle.sh" in names(calls) and "upload-gkm-to-r2.sh" not in names(calls)
    code, _, calls = stubbed_full_release(1, "--weekly", "--start-step=3")
    assert code == 0 and names(calls) == ["upload-gkm-to-r2.sh"]


def test_dry_run_validates_nothing(stubbed_full_release):
    code, out, calls = stubbed_full_release(1, "--weekly", "--dry-run")
    assert code == 0 and "[dry-run] Would run: validate-bundle.sh" in out
    assert names(calls) == ["upload-gkm-to-r2.sh"]
