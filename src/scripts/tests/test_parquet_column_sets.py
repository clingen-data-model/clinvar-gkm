"""The column sets ClinVar-GKM publishes for building the Parquet of frozen lines (docs/assets/column-sets/,
docs/parquet/previous-releases.md).

Each set must pair with the bundle schema URL the guide gives: its `schema` is the root `$id` that URL serves. The
compile test runs gkm-bundle-parquet 2.0.0 through uvx and fetches the schema, so it is skipped without uvx or the
network.
"""

import re
import shutil
import subprocess
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
COLUMN_SETS = ROOT / "docs" / "assets" / "column-sets"
TOOL = "gkm-bundle-parquet@2.0.0"

# column-set file -> (bundle schema URL the guide passes, the root $id that URL serves, projection name)
PAIRINGS = {
    "clinvar-gkm-1.1.0.columns.yaml": (
        "https://w3id.org/clingen/schema/clinvar-gkm/1.1.0/clinvar-gkm-bundle.schema.json",
        "https://w3id.org/clingen/schema/clinvar-gkm/1.1.0/json/ClinvarGkmBundle",
        "clinvar-gkm-1.1.0-producer",
    ),
}


def _top_level(path: Path) -> dict:
    """The column set's top-level scalar keys (schema, version_property, projection), read without a YAML parser."""
    out = {}
    for line in path.read_text().splitlines():
        m = re.match(r"^([a-z_]+):\s*(\S.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def test_every_published_column_set_is_listed():
    assert sorted(p.name for p in COLUMN_SETS.glob("*.columns.yaml")) == sorted(PAIRINGS)


@pytest.mark.parametrize("name", sorted(PAIRINGS))
def test_column_set_names_the_served_schema_id_and_a_projection(name):
    _, served_id, projection = PAIRINGS[name]
    top = _top_level(COLUMN_SETS / name)
    assert top["schema"] == served_id
    assert top["projection"] == projection
    assert top["version_property"] == "schema_version"


def _online(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.status == 200
    except OSError:
        return False


@pytest.mark.parametrize("name", sorted(PAIRINGS))
def test_column_set_compiles_against_its_schema_url(name):
    url, _, projection = PAIRINGS[name]
    if shutil.which("uvx") is None:
        pytest.skip("uvx not installed")
    if not _online(url):
        pytest.skip(f"offline: {url} not reachable")
    r = subprocess.run(
        ["uvx", TOOL, "compile-spec", "--bundle-schema", url, "--column-set", str(COLUMN_SETS / name)],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert r.returncode == 0, r.stderr
    assert f"the projection {projection}" in r.stdout
