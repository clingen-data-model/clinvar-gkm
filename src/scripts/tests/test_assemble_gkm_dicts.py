"""assemble-gkm-dicts.py sets the published text of every bundle record (full and delta), so the same record must
serialize to the same bytes in every release, whatever order BigQuery hands its fields in."""

import gzip
import importlib.util
import json
from pathlib import Path

import pytest

orjson = pytest.importorskip("orjson")

SCRIPTS = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("assemble_gkm_dicts", SCRIPTS / "assemble-gkm-dicts.py")
assemble_gkm_dicts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assemble_gkm_dicts)


def write_ndjson(path, rows):
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def assemble(tmp_path, files):
    src = tmp_path / "src"
    src.mkdir(parents=True)
    for name, rows in files.items():
        write_ndjson(src / name, rows)
    out = tmp_path / "bundle.json.gz"
    assemble_gkm_dicts.assemble(str(src), str(out), is_gcs=False)
    return gzip.decompress(out.read_bytes()).decode("utf-8")


def test_record_keys_are_sorted_at_every_depth():
    rec = {"type": "X", "id": "a", "b": {"z": 1, "y": [{"q": 2, "p": 1}]}}
    assert assemble_gkm_dicts.json_dumps_record(rec) == '{"b":{"y":[{"p":1,"q":2}],"z":1},"id":"a","type":"X"}'


def test_record_text_is_compact_raw_utf8():
    assert assemble_gkm_dicts.json_dumps_record({"name": "Sjögren", "n": 1}) == '{"n":1,"name":"Sjögren"}'


def test_same_record_in_any_field_order_gives_the_same_bytes(tmp_path):
    ext = [{"name": "e", "value_string": "s"}]
    one = {"id": "clinvar:1", "type": "CategoricalVariant", "name": "v", "extensions": ext}
    two = {"extensions": [{"value_string": "s", "name": "e"}], "name": "v", "type": "CategoricalVariant",
           "id": "clinvar:1"}
    a = assemble(tmp_path / "a", {"variation-0.ndjson.gz": [one]})
    b = assemble(tmp_path / "b", {"variation-0.ndjson.gz": [two]})
    assert a == b
    assert '{"extensions":[{"name":"e","value":"s"}],"id":"clinvar:1","name":"v","type":"CategoricalVariant"}' in a


def test_layout_is_unchanged_apart_from_key_order(tmp_path):
    text = assemble(tmp_path, {
        "submitter-0.ndjson.gz": [
            {"key": "clinvar.submitter:1", "value": json.dumps({"type": "Agent", "id": "clinvar.submitter:1"})}
        ],
        "gene-0.ndjson.gz": [{"key": "ncbigene:1", "value": {"type": "Gene", "id": "ncbigene:1", "extensions": []}}],
    })
    assert text == (
        "{\n"
        f'  "schema_version": "{assemble_gkm_dicts.SCHEMA_VERSION}",\n'
        '  "gene": {\n'
        '    "ncbigene:1": {"id":"ncbigene:1","type":"Gene"}\n'
        "  },\n"
        '  "submitter": {\n'
        '    "clinvar.submitter:1": {"id":"clinvar.submitter:1","type":"Agent"}\n'
        "  }\n"
        "}\n"
    )
    assert list(json.loads(text)) == ["schema_version", "gene", "submitter"]
