"""Tests for community-profile-conformance.py and the rs registry it builds on.

Needs jsonschema-rs and orjson, which exist only in the uv environment validate-bundle.sh builds:
    uv run --no-project --quiet --python 3.12 --with "jsonschema-rs==0.61.1" --with orjson --with pytest \
        python -m pytest -q src/scripts/tests/test_community_profile_conformance.py
"""
import copy
import gzip
import importlib.util
import json
from pathlib import Path

import jsonschema_rs
import pytest

SCRIPTS = Path(__file__).resolve().parents[1]


def load_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate_bundle_rs = load_script("validate_bundle_rs", "validate-bundle-rs.py")


def test_load_resources_includes_the_community_profiles():
    ids = {i for i, _ in validate_bundle_rs.load_resources(SCRIPTS.parents[1] / "schema")}
    assert any(i.endswith("/json/acmg-2015/VariantPathogenicityStatement") for i in ids)


def test_an_unknown_ref_fails_without_a_network_fetch():
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
              "$ref": "https://w3id.org/clingen/schema/clinvar-gkm/0.0.0/json/NoSuchClass"}
    with pytest.raises(jsonschema_rs.ValidationError, match="not in the local schema registry"):
        jsonschema_rs.Draft202012Validator(
            schema, registry=validate_bundle_rs.local_registry(SCRIPTS.parents[1] / "schema"))


conformance = load_script("community_profile_conformance", "community-profile-conformance.py")

COMMUNITY_SCI_OK = {  # what the aac-2017 profile wants
    "type": "Statement", "proposition": "#/propositionSomaticClinicalImpact/x", "direction": "supports",
    "specifiedBy": {"type": "Method", "name": "AMP/ASCO/CAP Guidelines, 2017"},
    "classification": {"type": "MappableConcept", "name": "Tier I",
                       "primaryCoding": {"code": "tier i", "system": "AMP/ASCO/CAP Guidelines, 2017"}},
    "strength": {"type": "MappableConcept",
                 "primaryCoding": {"code": "strong", "system": "AMP/ASCO/CAP Guidelines, 2017"}},
}
CLINVAR_SCI = copy.deepcopy(COMMUNITY_SCI_OK)  # what ClinVar-GKM emits after the 1.3.0 fixes
del CLINVAR_SCI["specifiedBy"]
CLINVAR_SCI["classification"]["name"] = "Tier I - Strong"
CLINVAR_SCI["classification"]["primaryCoding"]["name"] = "Tier I"


def test_conformant_record_has_no_reasons():
    assert conformance.reasons("aac-2017", COMMUNITY_SCI_OK) == set()


def test_clinvar_sci_record_differs_by_specifiedby_and_tier_name():
    assert conformance.reasons("aac-2017", CLINVAR_SCI) == {"no specifiedBy", "classification name"}


def write_bundle(tmp_path, records):
    body = ",\n".join(f"    {json.dumps(k)}: {json.dumps(r, separators=(',', ':'))}" for k, r in records.items())
    bundle_path = tmp_path / "bundle.json.gz"
    with gzip.open(bundle_path, "wt") as f:  # the assembler's one-record-per-line layout
        f.write('{\n  "schema_version": "x",\n  "scv": {\n' + body + "\n  }\n}\n")
    return bundle_path


def test_report_counts_per_profile(tmp_path):
    bundle_path = write_bundle(tmp_path, {"clinvar.submission:SCV000090500.1": COMMUNITY_SCI_OK,
                                          "clinvar.submission:SCV000090501.1": CLINVAR_SCI})
    report = conformance.report(bundle_path)
    assert report["aac-2017"] == {"scvs": 2, "conformant": 1,
                                  "reasons": {"no specifiedBy": 1, "classification name": 1}}


def test_write_docs_replaces_only_the_marked_block(tmp_path):
    bundle_path = write_bundle(tmp_path, {"clinvar.submission:SCV000090501.1": CLINVAR_SCI})
    page = tmp_path / "page.md"
    page.write_text("before\n<!-- community-conformance:start -->\nold\n<!-- community-conformance:end -->\nafter\n")
    conformance.write_docs(page, bundle_path, conformance.report(bundle_path))
    text = page.read_text()
    assert text.startswith("before\n<!-- community-conformance:start -->\n") and text.endswith(
        "<!-- community-conformance:end -->\nafter\n")
    assert "old" not in text and "bundle.json.gz" in text and "| AMP/ASCO/CAP 2017 |" in text


def test_write_docs_fails_without_the_markers(tmp_path):
    bundle_path = write_bundle(tmp_path, {"clinvar.submission:SCV000090501.1": CLINVAR_SCI})
    page = tmp_path / "page.md"
    page.write_text("no markers\n")
    with pytest.raises(SystemExit):
        conformance.write_docs(page, bundle_path, conformance.report(bundle_path))
