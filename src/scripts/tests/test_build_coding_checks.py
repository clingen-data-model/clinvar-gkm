"""check-clinsig-lookup.sh and check-scv-codings.sh: the build checks for the SCV statement profile codings (ADR 0015).

run-release.sh runs the lookup check before its version stamp (step 2) and the output check before any export (step
3), on this release and, unless the release starts a line, on the delta's baseline. Each test runs the real scripts
with a fake bq on PATH that answers each query from FAKE_BQ_ANSWERS: a JSON list of [substring, exit code, stdout],
the first whose substring is in the call wins (no match: exit 1). Every call is logged to FAKE_LOG.
"""

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
LOOKUP_CHECK = SCRIPTS / "check-clinsig-lookup.sh"
CODINGS_CHECK = SCRIPTS / "check-scv-codings.sh"
RUN_RELEASE = SCRIPTS / "run-release.sh"

FAKE_BQ = """#!/usr/bin/python3
import json, os, sys
call = " ".join(sys.argv[1:])
with open(os.environ["FAKE_LOG"], "a") as log:
    log.write("bq " + call.replace("\\n", " ") + "\\n")
for needle, code, out in json.loads(os.environ.get("FAKE_BQ_ANSWERS", "[]")):
    if needle in call:
        if out:
            print(out)
        sys.exit(code)
print("fake bq: no answer for: " + call, file=sys.stderr)
sys.exit(1)
"""

# run-release.sh checks that its python3 has orjson before it starts; the rest is the real python3.
FAKE_PYTHON3 = """#!/bin/sh
[ "$1 $2" = "-c import orjson" ] && exit 0
exec /usr/bin/python3 "$@"
"""

DATE, PREV = "2026-11-29", "2026-11-22"
DS, BASE = "clinvar_2026_11_29_v2_7_1", "clinvar_2026_11_22_v2_7_1"
COUNTS_HEADER = "old_codes,strength_system,tier_name,aggregate_old_codes"


def release(date, dataset, prev):
    return [f"schema_on`(DATE '{date}')", 0, f"schema_name,prev_release_date\n{dataset},{prev}"]


def name_field(dataset, present=True):
    return [f"{dataset}.INFORMATION_SCHEMA", 0, f"n\n{1 if present else 0}"]


def counts(dataset, values="0,0,0,0"):
    return [f"{dataset}.gkm_dict_scv", 0, f"{COUNTS_HEADER}\n{values}"]


def built(dataset, values="0,0,0,0"):
    return [name_field(dataset), counts(dataset, values)]


@pytest.fixture
def fake(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, text in (("bq", FAKE_BQ), ("python3", FAKE_PYTHON3)):
        path = bin_dir / name
        path.write_text(text)
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return tmp_path


def run(tmp, script, *args, answers=()):
    result = subprocess.run(
        [str(script), *args],
        capture_output=True,
        text=True,
        env={
            "HOME": os.environ.get("HOME", ""),
            "PATH": f"{tmp / 'bin'}:/usr/bin:/bin",
            "FAKE_LOG": str(tmp / "calls.log"),
            "FAKE_BQ_ANSWERS": json.dumps(list(answers)),
        },
    )
    log = tmp / "calls.log"
    return result.returncode, result.stdout + result.stderr, log.read_text().splitlines() if log.exists() else []


# --- check-clinsig-lookup.sh ---------------------------------------------------------------------------------------

def test_lookup_with_the_profile_codings_passes(fake):
    code, out, calls = run(fake, LOOKUP_CHECK, answers=[["clinvar_clinsig_types", 0, "problem"]])
    assert code == 0, out
    assert "carries the profile codings" in out
    assert len(calls) == 1 and "--format=csv" in calls[0]


def test_lookup_check_reads_the_shared_table_and_asks_for_every_profile_coding(fake):
    run(fake, LOOKUP_CHECK, answers=[["clinvar_clinsig_types", 0, ""]])
    (call,) = (fake / "calls.log").read_text().splitlines()
    assert "`clinvar_ingest.clinvar_clinsig_types`" in call
    for needle in ("'tier iv'", "'SVC v4'", "'(AAC)'", "ACMG/AMP/CAP/ClinGen SVCv4.0", "'AMP/ASCO/CAP Guidelines, 2017'",
                   "'vus-high'", "'pathogenic/likely pathogenic'", "LOWER(classification_code)"):
        assert needle in call, needle


def test_outdated_lookup_stops_and_names_each_problem(fake):
    # as bq writes CSV: a value with a comma or a quote is quoted, and its quotes doubled
    problems = 'problem\n"sci t1: retired system name ""AMP/ASCO/CAP (AAC) Guidelines, 2017"""\nsci tier i: missing'
    code, out, _ = run(fake, LOOKUP_CHECK, answers=[["clinvar_clinsig_types", 0, problems]])
    assert code == 1
    assert "does not carry the codings" in out
    assert '    sci t1: retired system name "AMP/ASCO/CAP (AAC) Guidelines, 2017"\n' in out
    assert "    sci tier i: missing" in out
    assert "00-setup-translation-tables.sql" in out


def test_unreadable_lookup_stops(fake):
    code, out, _ = run(fake, LOOKUP_CHECK, answers=[["clinvar_clinsig_types", 1, ""]])
    assert code == 1
    assert "could not read clinvar_ingest.clinvar_clinsig_types" in out


# --- check-scv-codings.sh ------------------------------------------------------------------------------------------

def test_release_and_baseline_with_the_profile_codings_pass(fake):
    answers = [release(DATE, DS, PREV), release(PREV, BASE, "2026-11-15"), *built(DS), *built(BASE)]
    code, out, _ = run(fake, CODINGS_CHECK, DATE, "--with-baseline", answers=answers)
    assert code == 0, out
    assert f"{DS}: SCV profile codings OK (old_codes=0 strength_system=0 tier_name=0 aggregate_old_codes=0)" in out
    assert f"{BASE} (the delta's baseline): SCV profile codings OK" in out


def test_without_with_baseline_only_the_release_is_checked(fake):
    code, out, calls = run(fake, CODINGS_CHECK, DATE, answers=[release(DATE, DS, PREV), *built(DS)])
    assert code == 0, out
    assert not any(BASE in c or PREV in c for c in calls), calls


def test_old_codes_in_the_release_stop(fake):
    answers = [release(DATE, DS, PREV), *built(DS, "1752,0,1752,3592")]
    code, out, _ = run(fake, CODINGS_CHECK, DATE, answers=answers)
    assert code == 1
    assert f"ERROR: {DS}: old_codes=1752 strength_system=0 tier_name=1752 aggregate_old_codes=3592" in out
    assert "--full-procs" in out


def test_a_baseline_built_before_1_3_0_stops(fake):
    answers = [release(DATE, DS, PREV), release(PREV, BASE, "2026-11-15"), *built(DS), name_field(BASE, False)]
    code, out, calls = run(fake, CODINGS_CHECK, DATE, "--with-baseline", answers=answers)
    assert code == 1
    assert f"ERROR: {BASE} (the delta's baseline): built before schema 1.3.0" in out
    assert f"{DS}: SCV profile codings OK" in out
    assert not any(f"{BASE}.gkm_dict_scv" in c for c in calls), calls


def test_a_release_without_a_previous_one_checks_only_itself(fake):
    code, out, _ = run(fake, CODINGS_CHECK, DATE, "--with-baseline", answers=[release(DATE, DS, ""), *built(DS)])
    assert code == 0, out
    assert f"{DATE} has no previous release" in out


def test_unreadable_counts_stop(fake):
    answers = [release(DATE, DS, PREV), name_field(DS), [f"{DS}.gkm_dict_scv", 1, ""]]
    code, out, _ = run(fake, CODINGS_CHECK, DATE, answers=answers)
    assert code == 1
    assert f"ERROR: {DS}: could not be read" in out


def test_no_release_dataset_stops(fake):
    code, out, _ = run(fake, CODINGS_CHECK, DATE, answers=[[f"schema_on`(DATE '{DATE}')", 0, "schema_name,prev_release_date"]])
    assert code == 1
    assert f"no release dataset for {DATE}" in out


@pytest.mark.parametrize("args", [("2026-1-29",), (DATE, "--baseline")])
def test_bad_arguments_stop(fake, args):
    code, out, calls = run(fake, CODINGS_CHECK, *args)
    assert code == 1
    assert calls == []


# --- run-release.sh step 3 -----------------------------------------------------------------------------------------

def step_3(fake, *flags, answers):
    ls = ["ls --project_id", 0, f"  {DS}"]
    return run(fake, RUN_RELEASE, DATE, "--dry-run", "--start-step", "3", *flags, answers=[ls, *answers])


def test_step_3_checks_the_release_and_the_baseline_before_any_export(fake):
    answers = [release(DATE, DS, PREV), release(PREV, BASE, "2026-11-15"), *built(DS), name_field(BASE, False)]
    code, out, _ = step_3(fake, answers=answers)
    assert code == 1
    assert "the delta's baseline): built before schema 1.3.0" in out
    assert "is started" not in out and "building and validating" not in out


def test_step_3_of_a_line_checkpoint_checks_only_the_release(fake):
    code, out, calls = step_3(fake, "--bootstrap-monthly=2026-12", answers=[release(DATE, DS, PREV), *built(DS, "8,0,0,0")])
    assert code == 1
    assert f"ERROR: {DS}: old_codes=8" in out
    assert not any(PREV in c for c in calls), calls
