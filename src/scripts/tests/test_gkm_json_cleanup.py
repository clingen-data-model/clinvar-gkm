import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gkm_json_cleanup
from gkm_json_cleanup import UNORDERED_ARRAYS, order_unordered_arrays, strip_empty

SCHEMA = Path(__file__).resolve().parents[3] / "schema"


def test_drops_empty_array_field():
    assert strip_empty({"name": "Benign", "extensions": []}) == {"name": "Benign"}


def test_drops_null_and_empty_object_fields():
    assert strip_empty({"a": None, "b": {}, "c": 1}) == {"c": 1}


def test_recurses_into_nested_objects():
    assert strip_empty({"x": {"y": [], "z": "k"}}) == {"x": {"z": "k"}}


def test_object_that_becomes_empty_is_dropped():
    assert strip_empty({"outer": {"inner": []}}) == {}


def test_preserves_falsy_scalars():
    assert strip_empty({"n": 0, "b": False, "s": ""}) == {"n": 0, "b": False, "s": ""}


def test_keeps_array_elements_but_strips_their_internals():
    assert strip_empty({"items": [{"k": "v", "e": []}, {"k": "w"}]}) == {
        "items": [{"k": "v"}, {"k": "w"}]
    }


def test_top_level_list_is_cleaned_elementwise():
    assert strip_empty([{"a": []}, {"b": 2}]) == [{}, {"b": 2}]


def test_idempotent_on_clean_input():
    clean = {"name": "x", "items": [{"k": "v"}]}
    assert strip_empty(clean) == clean
    assert strip_empty(strip_empty(clean)) == clean


def test_condition_aliases_get_one_order_whatever_the_input_order():
    one = {"id": "clinvar.trait:2113", "aliases": ["Erythrocytosis, familial, 1", "POLYCYTHEMIA, PRIMARY", "Ä"]}
    two = {"id": "clinvar.trait:2113", "aliases": ["Ä", "POLYCYTHEMIA, PRIMARY", "Erythrocytosis, familial, 1"]}
    assert order_unordered_arrays("condition", one) == order_unordered_arrays("condition", two) == {
        "id": "clinvar.trait:2113",
        "aliases": ["Erythrocytosis, familial, 1", "POLYCYTHEMIA, PRIMARY", "Ä"],
    }


def test_only_listed_arrays_are_reordered():
    rec = {"aliases": ["b", "a"], "mappings": [{"c": 2}, {"c": 1}]}
    assert order_unordered_arrays("condition", rec) == {"aliases": ["a", "b"], "mappings": [{"c": 2}, {"c": 1}]}
    vcv = {"aliases": ["b", "a"]}
    assert order_unordered_arrays("vcv", vcv) == {"aliases": ["b", "a"]}


def test_nested_paths_and_object_elements(monkeypatch):
    monkeypatch.setitem(UNORDERED_ARRAYS, "x", ("items[].tags", "meta.codes"))
    rec = {
        "items": [{"tags": [{"b": 1, "a": 2}, {"a": 1}]}, {"other": 1}],
        "meta": {"codes": [3, 1, 2]},
        "tags": ["z", "y"],
    }
    assert order_unordered_arrays("x", rec) == {
        "items": [{"tags": [{"a": 1}, {"a": 2, "b": 1}]}, {"other": 1}],
        "meta": {"codes": [1, 2, 3]},
        "tags": ["z", "y"],
    }


def test_elements_are_kept_including_duplicates():
    rec = {"aliases": ["b", "a", "b"]}
    assert order_unordered_arrays("condition", rec) == {"aliases": ["a", "b", "b"]}


def _array_order_flags():
    """{property name: {ordered flag, ...}} over every array property in the schema tree."""
    flags = {}

    def walk(node, name):
        if isinstance(node, dict):
            if node.get("type") == "array":
                flags.setdefault(name, set()).add(node.get("ordered"))
            for k, v in node.items():
                walk(v, k)
        elif isinstance(node, list):
            for v in node:
                walk(v, name)

    for path in SCHEMA.glob("*/json/**/*"):
        if path.is_file():
            walk(json.loads(path.read_text()), None)
    return flags


def test_every_reordered_array_is_unordered_in_every_schema():
    if not list(SCHEMA.glob("va-spec/json/*")):
        pytest.skip("schema/ needs the va-spec submodule (git submodule update --init --recursive)")
    flags = _array_order_flags()
    for section, paths in gkm_json_cleanup.UNORDERED_ARRAYS.items():
        for path in paths:
            name = path.split(".")[-1].rstrip("[]")
            assert flags.get(name) == {False}, f"{section} {path}: schemas mark {name} ordered {flags.get(name)}"
