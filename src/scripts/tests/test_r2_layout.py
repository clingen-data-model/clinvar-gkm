import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import r2_layout as R  # noqa: E402

L = "v1/1.1/"


def objs(*keys, size=10):
    return {k: (size, "2026-10-20") for k in keys}


def delta(d, folder=""):
    c = f"{d[:4]}-{d[5:7]}{d[8:10]}"
    base = f"{L}deltas/{folder}clinvar-gkm-delta_{c}"
    return [base + ".json.gz", base + ".json.gz.sha256", base + ".manifest.json"]


def weekly(d):
    c = f"{d[:4]}-{d[5:7]}{d[8:10]}"
    return [f"{L}weekly/clinvar-gkm_{c}.json.gz", f"{L}weekly/clinvar-gkm_{c}.json.gz.sha256"]


def monthly(label, folder=""):
    return [f"{L}{folder}clinvar-gkm_{label}.json.gz", f"{L}{folder}clinvar-gkm_{label}.json.gz.sha256"]


OCTOBER = (monthly("2026-09") + monthly("2026-10") + delta("2026-09-28", "2026-09/") + delta("2026-10-04")
           + delta("2026-10-11") + delta("2026-10-25") + weekly("2026-10-04") + weekly("2026-10-11")
           + weekly("2026-10-25"))


def test_delta_dir_rule():
    assert R.delta_dir("2026-10-04", "2026-10") == "deltas/"
    assert R.delta_dir("2026-09-28", "2026-10") == "deltas/2026-09/"
    assert R.delta_dir("2026-12-28", "2027-01") == "archive/2026/deltas/2026-12/"


def test_no_rollover_within_month():
    moves, deletes, _ = R.plan_rollover(objs(*OCTOBER), L, "2026-10-25")
    assert moves == [] and deletes == []


def test_month_rollover_keeps_source_candidate_until_monthly_posted():
    moves, deletes, notes = R.plan_rollover(objs(*OCTOBER), L, "2026-11-01")
    moved = {src.rsplit("/", 1)[1]: dst for _, src, dst in moves}
    assert moved["clinvar-gkm-delta_2026-1004.json.gz"] == f"{L}deltas/2026-10/clinvar-gkm-delta_2026-1004.json.gz"
    assert moved["clinvar-gkm-delta_2026-1025.manifest.json"].startswith(f"{L}deltas/2026-10/")
    assert len(moves) == 9   # three October deltas x three files; September is already in its folder
    deleted = {k for _, k in deletes}
    assert deleted == set(weekly("2026-10-04") + weekly("2026-10-11"))   # 10-25 kept: 2026-11 source candidate
    assert any("2026-1025" in n for n in notes)


def test_candidate_deleted_once_monthly_posted():
    state = objs(*(OCTOBER + monthly("2026-11") + weekly("2026-11-01") + delta("2026-11-01")))
    moves, deletes, _ = R.plan_rollover(state, L, "2026-11-01")
    assert {k for _, k in deletes} == set(weekly("2026-10-04") + weekly("2026-10-11") + weekly("2026-10-25"))


def test_rollover_is_idempotent_after_apply():
    state = objs(*OCTOBER)
    moves, deletes, _ = R.plan_rollover(state, L, "2026-11-01")
    for size, src, dst in moves:
        state[dst] = state.pop(src)
    for _, k in deletes:
        state.pop(k)
    assert R.plan_rollover(state, L, "2026-11-01")[:2] == ([], [])


def test_year_rollover():
    dec = (monthly("2026-11") + monthly("2026-12") + delta("2026-11-30", "2026-11/") + delta("2026-12-06")
           + delta("2026-12-27") + weekly("2026-12-06") + weekly("2026-12-27"))
    moves, deletes, _ = R.plan_rollover(objs(*dec), L, "2027-01-03")
    dst = {src.rsplit("/", 1)[1]: d for _, src, d in moves}
    assert dst["clinvar-gkm_2026-12.json.gz"] == f"{L}archive/2026/clinvar-gkm_2026-12.json.gz"
    assert dst["clinvar-gkm_2026-11.json.gz.sha256"] == f"{L}archive/2026/clinvar-gkm_2026-11.json.gz.sha256"
    assert dst["clinvar-gkm-delta_2026-1130.json.gz"] == f"{L}archive/2026/deltas/2026-11/clinvar-gkm-delta_2026-1130.json.gz"
    assert dst["clinvar-gkm-delta_2026-1227.manifest.json"] == f"{L}archive/2026/deltas/2026-12/clinvar-gkm-delta_2026-1227.manifest.json"
    assert {k for _, k in deletes} == set(weekly("2026-12-06"))   # 12-27 kept for the 2027-01 monthly


def test_refuses_older_release():
    try:
        R.plan_rollover(objs(*OCTOBER), L, "2026-10-12")
    except SystemExit as e:
        assert "older than the newest release" in str(e)
    else:
        raise AssertionError("expected SystemExit")


def test_index_shape_and_checkpoint():
    keys = OCTOBER + [f"{L}clinvar-gkm_00-latest.json.gz", f"{L}weekly/clinvar-gkm_00-latest_weekly.json.gz"]
    state = objs(*keys)
    state[f"{L}clinvar-gkm_2026-10.json.gz"] = (20, "2026-10-20")
    state[f"{L}clinvar-gkm_00-latest.json.gz"] = (20, "2026-10-20")
    idx = R.build_index(state, L, shas={}, sources={"2026-09": "2026-08-29", "2026-10": "2026-09-28"},
                        prev_index=None, schema_version="1.1.0", status="current", superseded_by=None,
                        parquet_manifest=None, now="t")
    ds = idx["datasets"]
    assert [m["release"] for m in ds["monthly"]] == ["2026-09", "2026-10", "2026-10"]
    assert ds["monthly"][-1]["latest"] and ds["monthly"][-1]["source_release"] == "2026-09-28"
    assert [d["release"] for d in idx["deltas"]] == ["2026-09-28", "2026-10-04", "2026-10-11", "2026-10-25"]
    d = idx["deltas"][0]
    assert d["manifest"] == f"{L}deltas/2026-09/clinvar-gkm-delta_2026-0928.manifest.json"
    assert d["bundle"]["path"] == f"{L}deltas/2026-09/clinvar-gkm-delta_2026-0928.json.gz"
    cp = R.checkpoint_for(idx, "2026-09-28")
    assert cp["path"] == f"{L}clinvar-gkm_2026-10.json.gz" and cp["release"] == "2026-09-28" and cp["month"] == "2026-10"
    assert R.checkpoint_for(idx, "2026-09-23")["month"] == "2026-09"
    # source_release carries forward from the previous index
    idx2 = R.build_index(state, L, shas={}, sources={}, prev_index=idx, schema_version="1.1.0", status="current",
                         superseded_by=None, parquet_manifest=None, now="t")
    assert [m["source_release"] for m in idx2["datasets"]["monthly"]] == ["2026-08-29", "2026-09-28", "2026-09-28"]


def test_root_versions():
    root = R.build_root("1.1.0", "t")
    cur = [v for v in root["versions"].values() if v["status"] == "current"]
    assert cur == [root["versions"]["1.1"]] and cur[0]["index"] == "v1/1.1/index.json" and cur[0]["schema"] == "1.1.0"
    assert root["versions"]["1.0"]["superseded_by"] == "v1/1.1" and root["versions"]["1.0"]["schema"] == "1.0.1"


def test_cleanup_keeps_only_lines_and_root_index():
    state = objs("index.json", "v1/index.json", "v1/datasets/x.json.gz", "archive/1.0.1/MANIFEST.json",
                 f"{L}index.json", "v1/1.0/index.json", "v1/_backup/pre-1.1.0/index.json")
    assert {k for _, k in R.plan_cleanup(state)} == {"v1/index.json", "v1/datasets/x.json.gz",
                                                     "archive/1.0.1/MANIFEST.json", "v1/_backup/pre-1.1.0/index.json"}


def test_move_10():
    man = {"schema_version": "1.0.1", "files": [
        {"original_key": "v1/datasets/clinvar-gkm_2026-07.json.gz", "archive_key": "archive/1.0.1/v1/datasets/clinvar-gkm_2026-07.json.gz", "size": 5, "sha256": "a" * 64},
        {"original_key": "v1/deltas/2026-1004/manifest.json", "archive_key": "archive/1.0.1/v1/deltas/2026-1004/manifest.json", "size": 3, "sha256": "b" * 64},
        {"original_key": "v1/deltas/00-latest/manifest.json", "archive_key": "archive/1.0.1/v1/deltas/00-latest/manifest.json", "size": 3, "sha256": "c" * 64},
        {"original_key": "v1/index.json", "archive_key": "archive/1.0.1/v1/index.json", "size": 3, "sha256": "d" * 64}]}
    copies, dropped, sidecars, new = R.plan_move_10(man, "archive/1.0.1/", "v1/1.0/", "t")
    assert [c[2] for c in copies] == ["v1/1.0/clinvar-gkm_2026-07.json.gz",
                                      "v1/1.0/deltas/2026-10/clinvar-gkm-delta_2026-1004.manifest.json"]
    assert dropped == ["v1/deltas/00-latest/manifest.json", "v1/index.json"]
    assert sidecars == {"v1/1.0/clinvar-gkm_2026-07.json.gz.sha256": "a" * 64 + "  clinvar-gkm_2026-07.json.gz\n"}
    assert new["status"] == "frozen" and new["superseded_by"] == "v1/1.1" and new["file_count"] == 2
