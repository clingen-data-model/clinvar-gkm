"""extract-example.py builds the examples/ fragments from a published bundle: the top record plus everything it
references, except statements and variations, which stay pointers."""

import gzip
import importlib.util
import json
import re
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("extract_example", SCRIPTS / "extract-example.py")
ex = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ex)

# A tiny bundle in the assembler's layout. Referenced records come before the records that reference them.
BUNDLE = {
    "sequenceReference": {"SQ.1": {"type": "SequenceReference"}},
    "location": {"ga4gh:SL.1": {"sequenceReference": "#/sequenceReference/SQ.1", "type": "SequenceLocation"}},
    "allele": {"ga4gh:VA.1": {"location": "#/location/ga4gh:SL.1", "type": "Allele"}},
    "gene": {"ncbigene:1": {"name": "G1"}},
    "variation": {"clinvar:1": {"constraints": [{"allele": "#/allele/ga4gh:VA.1"}],
                                "extensions": [{"name": "genes", "value": [{"gene": "#/gene/ncbigene:1"}]}]}},
    "condition": {"clinvar.trait:1": {"name": "C1"}, "clinvar.trait:2": {"name": "C2"},
                  "clinvar.trait:9": {"name": "unused"}},
    "conditionSet": {"clinvar.traitset:1": {"concepts": ["#/condition/clinvar.trait:1", "#/condition/clinvar.trait:2"]}},
    "submitter": {"clinvar.submitter:1": {"name": "Lab"}},
    "propositionPathogenicity": {
        "SCV000000001-PATH": {"object": "#/condition/clinvar.trait:1", "subject": "#/variation/clinvar:1"},
        "VCV000000001-PATH": {"object": "#/conditionSet/clinvar.traitset:1", "subject": "#/variation/clinvar:1"},
    },
    "evidenceLine": {
        "VCV000000001.2-G-PATH.contributing": {"hasEvidenceItems": ["#/vcv/VCV000000001.2-G-PATH-CP"]},
        "VCV000000001.2-G-PATH-CP.contributing": {"hasEvidenceItems": ["#/scv/clinvar.submission:SCV000000001.3"]},
    },
    "scv": {"clinvar.submission:SCV000000001.3": {
        "contributions": [{"contributor": "#/submitter/clinvar.submitter:1"}],
        "proposition": "#/propositionPathogenicity/SCV000000001-PATH"}},
    "vcv": {
        "VCV000000001.2-G-PATH": {"hasEvidenceLines": ["#/evidenceLine/VCV000000001.2-G-PATH.contributing"],
                                  "proposition": "#/propositionPathogenicity/VCV000000001-PATH"},
        "VCV000000001.2-G-PATH-CP": {"hasEvidenceLines": ["#/evidenceLine/VCV000000001.2-G-PATH-CP.contributing"],
                                     "proposition": "#/propositionPathogenicity/VCV000000001-PATH"},
    },
}


def write_bundle(path, bundle, schema_version="1.1.0"):
    lines = ["{\n", f'  "schema_version": "{schema_version}",\n']
    for i, (section, records) in enumerate(bundle.items()):
        lines.append(f'  "{section}": {{\n')
        items = list(records.items())
        for j, (k, v) in enumerate(items):
            lines.append(f"    {json.dumps(k)}: {json.dumps(v, separators=(',', ':'))}"
                         + ("," if j < len(items) - 1 else "") + "\n")
        lines.append("  },\n" if i < len(bundle) - 1 else "  }\n")
    lines.append("}\n")
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.writelines(lines)
    return path


@pytest.fixture
def bundle(tmp_path):
    return write_bundle(tmp_path / "bundle.json.gz", BUNDLE)


def test_pointers_finds_nested_refs_only():
    rec = {"a": "#/gene/ncbigene:1", "b": [{"c": "#/condition/clinvar.trait:1"}], "d": "clinvar.trait:2", "e": 3}
    assert sorted(ex.pointers(rec)) == [("condition", "clinvar.trait:1"), ("gene", "ncbigene:1")]


def test_closure_keeps_statement_and_variation_pointers():
    have = {("vcv", "V"): {"x": "#/evidenceLine/E", "p": "#/propositionPathogenicity/P"},
            ("evidenceLine", "E"): {"items": ["#/vcv/V-CP", "#/scv/S"]},
            ("propositionPathogenicity", "P"): {"subject": "#/variation/clinvar:1", "object": "#/condition/C"}}
    records, missing, kept = ex.closure(("vcv", "V"), have.get)
    assert set(records) == set(have)
    assert missing == {("condition", "C")}
    assert kept == {("vcv", "V-CP"), ("scv", "S"), ("variation", "clinvar:1")}


def test_key_patterns_and_file_names():
    p = ex.key_pattern("vcv", "VCV000007105", "G-PATH")
    assert p.match("VCV000007105.214-G-PATH") and not p.match("VCV000007105.214-G-PATH-CP")
    assert ex.file_name("vcv", "VCV000007105", "G-PATH", ".jsonc", "VCV000007105.214-G-PATH") == \
        "VCV000007105.214-G-PATH.jsonc"
    p = ex.key_pattern("scv", "SCV004565358", "S-SCI-T1-TR")
    assert p.match("clinvar.submission:SCV004565358.1").group(1) == "1"
    assert ex.file_name("scv", "SCV004565358", "S-SCI-T1-TR", ".json", "clinvar.submission:SCV004565358.1") == \
        "SCV004565358.1-S-SCI-T1-TR.json"
    assert ex.key_pattern("variation", "clinvar:12582", "").match("clinvar:12582")
    assert not ex.key_pattern("variation", "clinvar:12582", "").match("clinvar:125820")
    assert ex.file_name("variation", "clinvar:12582", "", ".jsonc", "clinvar:12582") == "clinvar:12582.jsonc"


def test_superseded_finds_only_the_same_accession_and_suffix(tmp_path):
    for n in ("VCV000007105.213-G-PATH.jsonc", "VCV000007105.214-G-PATH.jsonc", "VCV000007105.213-G-NP.jsonc",
              "VCV000007105.213-G-PATH-CP.jsonc"):
        (tmp_path / n).write_text("{}")
    assert [p.name for p in ex.superseded(tmp_path, "VCV000007105", "G-PATH", "VCV000007105.214-G-PATH.jsonc")] == \
        ["VCV000007105.213-G-PATH.jsonc"]


def test_extract_builds_bounded_fragments_over_several_passes(bundle):
    tops = {"vcv": ("vcv", ex.key_pattern("vcv", "VCV000000001", "G-PATH")),
            "scv": ("scv", ex.key_pattern("scv", "SCV000000001", "G-PATH")),
            "var": ("variation", ex.key_pattern("variation", "clinvar:1", ""))}
    passes = []
    results, order, sv = ex.extract(bundle, tops, ["VCV000000001", "SCV000000001"], log=passes.append)
    assert sv == "1.1.0" and order == list(BUNDLE)
    # The statements close on the first pass; the variation needs the allele, then the allele's location.
    assert len(passes) == 3

    top, records, kept = results["vcv"]
    assert top == "VCV000000001.2-G-PATH"
    assert set(records) == {("vcv", top), ("evidenceLine", "VCV000000001.2-G-PATH.contributing"),
                            ("propositionPathogenicity", "VCV000000001-PATH"),
                            ("conditionSet", "clinvar.traitset:1"),
                            ("condition", "clinvar.trait:1"), ("condition", "clinvar.trait:2")}
    assert kept == {("vcv", "VCV000000001.2-G-PATH-CP"), ("variation", "clinvar:1")}
    assert records[("vcv", top)] == BUNDLE["vcv"][top]  # verbatim

    _, records, kept = results["scv"]
    assert ("submitter", "clinvar.submitter:1") in records and kept == {("variation", "clinvar:1")}

    _, records, kept = results["var"]
    assert set(records) == {("variation", "clinvar:1"), ("allele", "ga4gh:VA.1"), ("location", "ga4gh:SL.1"),
                            ("sequenceReference", "SQ.1"), ("gene", "ncbigene:1")}
    assert kept == set()

    doc = ex.fragment("1.2.0", results["vcv"][1], order)
    assert list(doc) == ["schema_version", "condition", "conditionSet", "propositionPathogenicity", "evidenceLine",
                         "vcv"]
    assert doc["schema_version"] == "1.2.0"
    assert list(doc["condition"]) == ["clinvar.trait:1", "clinvar.trait:2"]


def test_extract_needs_exactly_one_top_record(bundle):
    tops = {"x": ("vcv", re.compile(r"^VCV000000001\.\d+-G-PATH"))}  # also matches -G-PATH-CP
    with pytest.raises(SystemExit, match="expected one"):
        ex.extract(bundle, tops, [], log=lambda m: None)


def test_extract_stops_on_a_missing_reference(tmp_path):
    broken = {"vcv": {"VCV000000002.1-G-PATH": {"proposition": "#/propositionPathogenicity/nope"}}}
    path = write_bundle(tmp_path / "b.json.gz", broken)
    tops = {"x": ("vcv", ex.key_pattern("vcv", "VCV000000002", "G-PATH"))}
    with pytest.raises(SystemExit, match="not in the bundle"):
        ex.extract(path, tops, [], log=lambda m: None)


def test_scan_rejects_other_layouts(tmp_path):
    path = tmp_path / "pretty.json.gz"
    with gzip.open(path, "wt") as f:
        f.write(json.dumps({"schema_version": "1.1.0", "gene": {"ncbigene:1": {"name": "G"}}}, indent=2))
    with pytest.raises(SystemExit, match="layout"):
        ex.scan(path, lambda s, k: True, {})
