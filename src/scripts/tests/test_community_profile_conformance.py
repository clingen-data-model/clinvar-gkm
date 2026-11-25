"""Tests for community-profile-conformance.py and the rs registry it builds on.

Needs jsonschema-rs and orjson, which exist only in the uv environment validate-bundle.sh builds:
    uv run --no-project --quiet --python 3.12 --with "jsonschema-rs==0.61.1" --with orjson --with pytest \
        python -m pytest -q src/scripts/tests/test_community_profile_conformance.py
"""
import importlib.util
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
