"""docs/assets/scripts/recode-1-3-0.py gives an older line's records the guideline codings 1.3.0 corrected.

The real 1.2.0 somatic clinical impact example fails the 1.3.0 SCV profile as published and passes it once recoded;
the other cases are built by hand. The release gate applies the same script to the final 1.2 monthly and compares
it with the 1.3 checkpoint monthly built from the same release.
"""

import copy
import gzip
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from test_validate_bundle_rs import VERSION, assembled, failing_keys, rs, validate, write  # noqa: E402,F401

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "docs/assets/scripts/recode-1-3-0.py"
spec = importlib.util.spec_from_file_location("recode", SCRIPT)
recode_mod = importlib.util.module_from_spec(spec)
sys.dont_write_bytecode = True  # no __pycache__ in docs/assets/scripts, which the docs site publishes
spec.loader.exec_module(recode_mod)
sys.dont_write_bytecode = False
recode = recode_mod.recode

SCI_EXAMPLE = ROOT / "examples/scv/SCV004565358.1-S-SCI-T1-TR.json"
SCV_KEY = "scv/clinvar.submission:SCV004565358.1"
AMP = "AMP/ASCO/CAP Guidelines, 2017"
SVCV4 = "ACMG/AMP/CAP/ClinGen SVCv4.0"
OLD_VALUES = (b'"tier 1"', b'"tier 2"', b'"tier 3"', b'"tier 4"', b"(AAC)", b'"SVC v4"', b"pathogenic/Likely pathogenic")


def statement(code, system, **extra):
    return {"classification": {"conceptType": "Classification", "name": code, "type": "MappableConcept",
                               "primaryCoding": {"code": code, "system": system}}, **extra}


def test_a_tier_scv_gets_the_tier_code_system_and_name():
    scv = statement("tier 2", "AMP/ASCO/CAP (AAC) Guidelines, 2017",
                    strength={"name": "Potential", "primaryCoding": {"code": "potential",
                                                                     "system": "AMP/ASCO/CAP (AAC) Guidelines, 2017"}})
    out = recode("scv", scv)
    assert out["classification"]["primaryCoding"] == {"code": "tier ii", "name": "Tier II", "system": AMP}
    assert out["strength"]["primaryCoding"] == {"code": "potential", "system": AMP}


def test_aggregates_get_the_code_and_system_but_no_name():
    vcv = statement("tier 1", "AMP/ASCO/CAP (AAC) Guidelines, 2017",
                    layers=[statement("tier 3", "AMP/ASCO/CAP (AAC) Guidelines, 2017")])
    out = recode("vcv", vcv)
    assert out["classification"]["primaryCoding"] == {"code": "tier i", "system": AMP}
    assert out["layers"][0]["classification"]["primaryCoding"] == {"code": "tier iii", "system": AMP}


def test_vus_sub_tiers_move_to_svcv4_and_gain_a_strength():
    scv = recode("scv", statement("vus-high", "SVC v4", direction="neutral"))
    assert scv["classification"]["primaryCoding"] == {"code": "vus-high", "system": SVCV4}
    assert scv["strength"] == {"conceptType": "Strength", "name": "High", "type": "MappableConcept",
                               "primaryCoding": {"code": "high", "system": SVCV4}}
    rcv = recode("rcv", {"layers": [statement("vus-low", "SVC v4")]})
    assert rcv["layers"][0]["strength"] == {"conceptType": "Strength", "name": "Low", "type": "MappableConcept"}


def test_the_combined_label_is_lower_cased():
    out = recode("scv", statement("pathogenic/Likely pathogenic", "ClinVar"))
    assert out["classification"]["primaryCoding"] == {"code": "pathogenic/likely pathogenic", "system": "ClinVar"}


def test_other_records_are_unchanged_and_recoding_is_idempotent():
    for record in (statement("pathogenic", "ACMG Guidelines, 2015"), statement("tier i", AMP),
                   statement("uncertain significance", "ACMG Guidelines, 2015")):
        assert recode("vcv", copy.deepcopy(record)) == record
    once = recode("scv", statement("tier 4", "AMP/ASCO/CAP (AAC) Guidelines, 2017"))
    assert recode("scv", copy.deepcopy(once)) == once


def run_script(src, dst):
    return subprocess.run([sys.executable, str(SCRIPT), str(src), str(dst)], capture_output=True, text=True)


def example_bundle():
    bundle = json.loads(SCI_EXAMPLE.read_text())
    bundle["schema_version"] = VERSION
    return bundle


def test_the_recoded_1_2_example_passes_the_1_3_profile(tmp_path, rs):
    src = write(tmp_path, assembled(example_bundle()))
    code, out = validate(src)
    assert code != 0 and SCV_KEY in failing_keys(out), out  # the 1.2.0 codes fail the 1.3.0 profile
    dst = tmp_path / "recoded.json.gz"
    result = run_script(src, dst)
    assert result.returncode == 0, result.stderr
    code, out = validate(dst)
    assert code == 0, out


def test_the_script_copies_unaffected_lines_byte_for_byte(tmp_path):
    src = write(tmp_path, assembled(example_bundle()))
    dst = tmp_path / "recoded.json.gz"
    result = run_script(src, dst)
    assert result.returncode == 0, result.stderr
    before = gzip.open(src, "rb").read().splitlines()
    after = gzip.open(dst, "rb").read().splitlines()
    assert len(before) == len(after)
    changed = [(b, a) for b, a in zip(before, after) if b != a]
    assert changed and all(any(old in b for old in recode_mod.OLD) for b, _ in changed)
    assert f"{len(changed)} records recoded" in result.stderr
    assert not any(any(old in a for old in OLD_VALUES) for a in after)
