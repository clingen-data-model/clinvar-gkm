"""replay-bundle.py rebuilds a week's full bundle from a monthly and its deltas, streaming the monthly. These tests
replay a tiny synthetic monthly with two deltas (a delete, an update, a new key, a new section, a key deleted and then
re-added) and check the result record by record, its layout, its sidecar, and the chain rules. The docs publish the
script as an asset; the published copy must be the same file."""

import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
ROOT = SCRIPTS.parents[1]
spec = importlib.util.spec_from_file_location("replay_bundle", SCRIPTS / "replay-bundle.py")
replay_bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay_bundle)


def assembled(bundle):
    """The bundle as assemble-gkm-dicts.py writes it: one compact record per line."""
    lines = ["{\n", f'  "schema_version": {json.dumps(bundle["schema_version"])}']
    for section, records in bundle.items():
        if section == "schema_version":
            continue
        body = ",\n".join(
            f"    {json.dumps(k, ensure_ascii=False)}: {json.dumps(r, separators=(',', ':'), sort_keys=True)}"
            for k, r in records.items()
        )
        lines.append(f',\n  "{section}": {{\n' + body + "\n  }")
    return "".join(lines) + "\n}\n"


def write(path, bundle):
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write(assembled(bundle))
    return str(path)


def manifest(release, baseline, deleted):
    return {"release": release, "baseline_release": baseline,
            "sections": {s: {"added": 0, "updated": 0, "deleted": keys} for s, keys in deleted.items()}}


MONTHLY = {
    "schema_version": "1.2.0",
    "gene": {"g1": {"name": "A"}, "g2": {"name": "B"}, "g3": {"name": "C"}},
    "submitter": {"s1": {"name": "Lab 1"}, "s2": {"name": "Lab 2"}},
    "scv": {"scv1": {"v": 1}, "scv2": {"v": 1}, "k\"quoted\\key": {"v": 1}},
}
DELTA1 = {  # update g2, add g4, delete g3 and scv1, add a whole section the monthly lacks
    "schema_version": "1.2.0",
    "gene": {"g2": {"name": "B2"}, "g4": {"name": "D"}},
    "therapy": {"t1": {"name": "drug"}},
}
DELTA2 = {  # re-add the deleted scv1, delete s2 (the last record of its section), update the escaped key
    "schema_version": "1.2.0",
    "scv": {"scv1": {"v": 2}, "k\"quoted\\key": {"v": 2}},
}
EXPECTED = {
    "schema_version": "1.2.0",
    "gene": {"g1": {"name": "A"}, "g2": {"name": "B2"}, "g4": {"name": "D"}},
    "therapy": {"t1": {"name": "drug"}},
    "submitter": {"s1": {"name": "Lab 1"}},
    "scv": {"scv1": {"v": 2}, "scv2": {"v": 1}, "k\"quoted\\key": {"v": 2}},
}


@pytest.fixture
def replayed(tmp_path):
    monthly = write(tmp_path / "monthly.json.gz", MONTHLY)
    d1 = write(tmp_path / "d1.json.gz", DELTA1)
    d2 = write(tmp_path / "d2.json.gz", DELTA2)
    deltas = [
        (manifest("2026-11-08", "2026-10-31", {"gene": ["g3"], "scv": ["scv1"]}), d1),
        (manifest("2026-11-15", "2026-11-08", {"submitter": ["s2"], "scv": []}), d2),
    ]
    out = str(tmp_path / "out.json.gz")
    sha, report = replay_bundle.replay(monthly, deltas, out)
    return out, sha, report


def test_records(replayed):
    out, _, _ = replayed
    with gzip.open(out, "rt", encoding="utf-8") as f:
        assert json.load(f) == EXPECTED


def test_layout_and_order(replayed):
    """The published layout, sections in the assembler's order (the new section in its place), monthly records in
    the monthly's order with new keys after them, readable again by the script's own strict reader."""
    out, _, _ = replayed
    with gzip.open(out, "rt", encoding="utf-8") as f:
        text = f.read()
    assert text == assembled(EXPECTED)
    events = list(replay_bundle.read_bundle(out))
    assert [e[1] for e in events if e[0] == "section"] == ["gene", "therapy", "submitter", "scv"]
    assert [e[1] for e in events if e[0] == "record"][:3] == ["g1", "g2", "g4"]


def test_report_and_sidecar(replayed):
    out, sha, report = replayed
    assert report["gene"] == {"monthly": 3, "replaced": 1, "deleted": 1, "added": 1, "written": 3}
    assert report["therapy"]["added"] == 1
    assert report["submitter"] == {"monthly": 2, "replaced": 0, "deleted": 1, "added": 0, "written": 1}
    assert report["scv"] == {"monthly": 3, "replaced": 2, "deleted": 0, "added": 0, "written": 3}
    assert hashlib.sha256(Path(out).read_bytes()).hexdigest() == sha
    assert Path(out + ".sha256").read_text() == f"{sha}  out.json.gz\n"


def test_deterministic(tmp_path, replayed):
    """The same inputs give the same bytes (no time or file name in the gzip header)."""
    out, sha, _ = replayed
    again = tmp_path / "again"
    again.mkdir()
    monthly = write(again / "monthly.json.gz", MONTHLY)
    deltas = [
        (manifest("2026-11-08", "2026-10-31", {"gene": ["g3"], "scv": ["scv1"]}),
         write(again / "d1.json.gz", DELTA1)),
        (manifest("2026-11-15", "2026-11-08", {"submitter": ["s2"]}), write(again / "d2.json.gz", DELTA2)),
    ]
    assert replay_bundle.replay(monthly, deltas, str(again / "out.json.gz"))[0] == sha


def test_section_emptied_by_deletes_is_omitted(tmp_path):
    monthly = write(tmp_path / "m.json.gz", {"schema_version": "1.2.0", "gene": {"g1": {}}, "scv": {"a": {}}})
    d = write(tmp_path / "d.json.gz", {"schema_version": "1.2.0", "scv": {"b": {}}})
    out = str(tmp_path / "o.json.gz")
    replay_bundle.replay(monthly, [(manifest("2", "1", {"gene": ["g1"]}), d)], out)
    with gzip.open(out, "rt") as f:
        assert json.load(f) == {"schema_version": "1.2.0", "scv": {"a": {}, "b": {}}}


def test_mixed_schema_versions_refused(tmp_path):
    monthly = write(tmp_path / "m.json.gz", {"schema_version": "1.1.0", "gene": {"g1": {}}})
    d = write(tmp_path / "d.json.gz", {"schema_version": "1.2.0", "gene": {"g2": {}}})
    with pytest.raises(replay_bundle.ReplayError, match="schema_version"):
        replay_bundle.replay(monthly, [(manifest("2", "1", {}), d)], str(tmp_path / "o.json.gz"))
    assert not (tmp_path / "o.json.gz").exists() and not (tmp_path / "o.json.gz.part").exists()


def test_other_layout_refused(tmp_path):
    path = tmp_path / "pretty.json.gz"
    with gzip.open(path, "wt") as f:
        json.dump(MONTHLY, f, indent=2)
    with pytest.raises(replay_bundle.ReplayError, match="layout"):
        list(replay_bundle.read_bundle(str(path)))


INDEX = {
    "datasets": {"monthly": [
        {"name": "m10", "release": "2026-10", "source_release": "2026-09-28", "latest": False},
        {"name": "m11", "release": "2026-11", "source_release": "2026-10-31", "latest": False},
        {"name": "latest", "release": "2026-11", "source_release": "2026-10-31", "latest": True},
    ]},
    "deltas": [{"release": r} for r in ("2026-10-04", "2026-10-11", "2026-10-31", "2026-11-08", "2026-11-15")],
}


def test_plan_picks_monthly_and_chain():
    base, chain = replay_bundle.plan(INDEX, "2026-10-11")
    assert base["name"] == "m10" and [d["release"] for d in chain] == ["2026-10-04", "2026-10-11"]
    base, chain = replay_bundle.plan(INDEX, "2026-11-15")
    assert base["name"] == "m11" and [d["release"] for d in chain] == ["2026-11-08", "2026-11-15"]
    base, chain = replay_bundle.plan(INDEX, "2026-10-31")
    assert base["name"] == "m11" and chain == []


def test_plan_refuses_unknown_release():
    with pytest.raises(replay_bundle.ReplayError, match="not a release"):
        replay_bundle.plan(INDEX, "2026-11-10")
    with pytest.raises(replay_bundle.ReplayError, match="no monthly"):
        replay_bundle.plan(INDEX, "2026-09-01")


def test_docs_asset_is_the_script():
    """The docs publish the script at assets/scripts/replay-bundle.py; it must be this file, byte for byte."""
    asset = ROOT / "docs" / "assets" / "scripts" / "replay-bundle.py"
    assert asset.read_bytes() == (SCRIPTS / "replay-bundle.py").read_bytes(), (
        "docs/assets/scripts/replay-bundle.py differs from src/scripts/replay-bundle.py; copy it again")
