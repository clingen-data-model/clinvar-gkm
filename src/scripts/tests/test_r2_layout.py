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
    root = R.build_root("1.2.0", "t")
    assert root["current"] == "v1/1.2"
    cur = [v for v in root["versions"].values() if v["status"] == "current"]
    assert cur == [root["versions"]["1.2"]] and cur[0]["index"] == "v1/1.2/index.json" and cur[0]["schema"] == "1.2.0"
    v11, v10 = root["versions"]["1.1"], root["versions"]["1.0"]
    assert (v11["status"], v11["schema"], v11["superseded_by"]) == ("frozen", "1.1.0", "v1/1.2")
    assert (v10["status"], v10["schema"], v10["superseded_by"]) == ("frozen", "1.0.1", "v1/1.1")
    assert all(v["status"] in ("current", "frozen") and "eol" not in v for v in root["versions"].values())


def test_every_frozen_line_is_superseded_by_a_published_line():
    assert [k for k, c in R.LINES.items() if c["status"] == "current"] == [R.CURRENT_LINE]
    for line, cfg in R.LINES.items():
        if cfg["status"] == "frozen":
            assert cfg["schema"] and cfg["superseded_by"] in R.LINES, line


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


def test_parquet_manifest_carries_clinvar_attribution(tmp_path, monkeypatch):
    d = tmp_path / "pq"; d.mkdir()
    (d / "gene.parquet").write_bytes(b"PAR1x")
    out = tmp_path / "manifest.json"
    monkeypatch.setattr(sys, "argv", ["r2_layout.py", "parquet-manifest", "--dir", str(d), "--release", "2026-10-18",
                                      "--dataset", "clinvar_2026_10_18_v2_6_0", "--schema-version", "1.1.0",
                                      "--out", str(out)])
    R.main()
    import json
    m = json.loads(out.read_text())
    assert m["source"]["name"] == "ClinVar" and "ncbi.nlm.nih.gov/clinvar" in m["source"]["url"]
    assert "genetics professional" in m["disclaimer"] and m["license"]["id"] == "CC0-1.0"
    assert m["files"][0]["name"] == "gene.parquet" and m["source_release"] == "2026-10-18"


# --- new line: line state, first-delta chain ---------------------------------------------------------------------

N = "v1/1.2/"


def test_line_state():
    assert R.line_state({}, N) == "empty"
    assert R.line_state(objs(f"{N}index.json", f"{N}README.txt", f"{L}clinvar-gkm_2026-10.json.gz"), N) == "empty"
    assert R.line_state(objs(f"{N}clinvar-gkm_2026-11.json.gz", f"{N}clinvar-gkm_00-latest.json.gz"), N) == "started"
    assert R.line_state(objs(f"{N}deltas/clinvar-gkm-delta_2026-1108.json.gz"), N) == "broken"
    assert R.line_state(objs(f"{N}weekly/clinvar-gkm_2026-1108.json.gz"), N) == "broken"


def _checkpoint_index(label="2026-11", source="2026-10-31"):
    state = objs(f"{N}clinvar-gkm_{label}.json.gz", f"{N}clinvar-gkm_00-latest.json.gz")
    return R.build_index(state, N, shas={}, sources={label: source}, prev_index=None, schema_version="1.2.0",
                         status="current", superseded_by=None, parquet_manifest=None, now="t")


def _refused(fn, *args, text):
    try:
        fn(*args)
    except SystemExit as e:
        assert text in str(e), str(e)
    else:
        raise AssertionError("expected SystemExit")


def test_first_delta_of_a_new_line_must_start_at_its_checkpoint_monthly():
    idx = _checkpoint_index()
    cp = R.checkpoint_for(idx, "2026-10-31")
    assert cp["month"] == "2026-11" and cp["release"] == "2026-10-31"
    R.check_chain("2026-11-08", "2026-10-31", None, cp)               # the line's first delta: OK
    # a delta whose baseline is older than the checkpoint has no monthly in this line
    _refused(R.check_chain, "2026-10-31", "2026-10-24", None, R.checkpoint_for(idx, "2026-10-24"),
             text="first delta of the line")
    # a first delta that skips releases after the checkpoint leaves a gap
    _refused(R.check_chain, "2026-11-15", "2026-11-08", None, R.checkpoint_for(idx, "2026-11-08"),
             text="first delta of the line")
    _refused(R.check_chain, "2026-11-08", "2026-10-31", None, None, text="the line has no monthly")
    R.check_chain("2026-11-15", "2026-11-08", None, R.checkpoint_for(idx, "2026-11-08"), True)   # --allow-gap


def test_later_delta_chain_unchanged():
    R.check_chain("2026-11-15", "2026-11-08", "2026-11-08", None)
    _refused(R.check_chain, "2026-11-22", "2026-11-08", "2026-11-15", None, text="the chain would have a gap")


def test_patch_manifest_refuses_first_delta_without_checkpoint(tmp_path):
    import gzip
    import json
    bundle = tmp_path / "d.json.gz"
    with gzip.open(bundle, "wt") as fh:
        fh.write('{"schema_version":"1.2.0"}')
    man = tmp_path / "m.json"
    man.write_text(json.dumps({"release": "2026-11-08", "baseline_release": "2026-10-31", "compare_release": "x"}))
    empty = tmp_path / "empty.json"
    empty.write_text("")
    args = ["patch-manifest", "--manifest", str(man), "--bundle", str(bundle), "--dir", f"{N}deltas/"]
    _refused(R.main, args + ["--index", str(empty)], text="first delta of the line")
    idx = tmp_path / "index.json"
    idx.write_text(json.dumps(_checkpoint_index()))
    assert R.main(args + ["--index", str(idx)]) == 0
    out = json.loads(man.read_text())
    assert out["checkpoint_full"]["month"] == "2026-11" and out["schema_version"] == "1.2.0"


# --- freezing a superseded line ----------------------------------------------------------------------------------

def _line_11_at_freeze():
    """v1/1.1/ as live on 2026-11-18 (trimmed): monthlies, October deltas at the top, weeklies, Parquet."""
    keys = (monthly("2026-09") + monthly("2026-10")
            + [f"{L}clinvar-gkm_00-latest.json.gz", f"{L}clinvar-gkm_00-latest.json.gz.sha256"]
            + delta("2026-09-28", "2026-09/") + delta("2026-10-04") + delta("2026-10-31")
            + weekly("2026-10-04") + weekly("2026-10-31")
            + [f"{L}weekly/clinvar-gkm_00-latest_weekly.json.gz", f"{L}weekly/clinvar-gkm_00-latest_weekly.json.gz.sha256",
               f"{L}parquet/scv.parquet", f"{L}parquet/manifest.json",
               f"{L}index.json", f"{L}feed.xml", f"{L}README.txt"])
    state = objs(*keys)
    shas = {k: "a" * 64 for k in keys if k.endswith(".json.gz") or k.endswith(".manifest.json")}
    index = {"datasets": {"monthly": [{"release": "2026-09", "source_release": "2026-08-29"},
                                      {"release": "2026-10", "source_release": "2026-09-28"}]}}
    return state, shas, index


def test_freeze_refuses_the_current_line():
    state, shas, index = _line_11_at_freeze()
    try:
        R.plan_freeze(state, N, shas=shas, index=index, now="t")
    except SystemExit as e:
        assert "not a frozen line" in str(e)
    else:
        raise AssertionError("expected SystemExit")


def test_freeze_plan_deletes_weekly_and_parquet_only():
    state, shas, index = _line_11_at_freeze()
    deletes, man, notes, problems = R.plan_freeze(state, L, shas=shas, index=index, now="2026-11-20T00:00:00Z")
    deleted = {k for _, k in deletes}
    assert deleted == {k for k in state if k.startswith((f"{L}weekly/", f"{L}parquet/"))}
    assert problems == []
    kept = {f["key"] for f in man["files"]}
    assert f"{L}clinvar-gkm_00-latest.json.gz" in kept and f"{L}deltas/clinvar-gkm-delta_2026-1031.manifest.json" in kept
    assert f"{L}deltas/2026-09/clinvar-gkm-delta_2026-0928.json.gz" in kept
    assert not any(k.endswith(".sha256") or "/weekly/" in k or "/parquet/" in k for k in kept)
    assert (man["status"], man["superseded_by"], man["schema_version"]) == ("frozen", "v1/1.2", "1.1.0")
    assert (man["first_delta"], man["last_delta"]) == ("2026-09-28", "2026-10-31")
    assert man["file_count"] == len(kept) and all(f["sha256"] == "a" * 64 for f in man["files"])
    # the newest weekly full is newer than the newest monthly's source: say so (an unposted monthly would be lost)
    assert any("2026-10-31" in n and "BEFORE freezing" in n for n in notes)


def test_freeze_keep_parquet_and_problems():
    state, shas, index = _line_11_at_freeze()
    deletes, _, notes, _ = R.plan_freeze(state, L, shas=shas, index=index, now="t", keep_parquet=True)
    assert not any("/parquet/" in k for _, k in deletes) and any("--keep-parquet" in n for n in notes)
    state[f"{L}stray.txt"] = (1, None)
    shas.pop(f"{L}clinvar-gkm_2026-10.json.gz")
    _, _, _, problems = R.plan_freeze(state, L, shas=shas, index={}, now="t")
    assert any("stray.txt" in p for p in problems)
    assert any("no sha256 for v1/1.1/clinvar-gkm_2026-10.json.gz" in p for p in problems)
    assert any("source_release unknown" in p for p in problems)


def test_freeze_is_idempotent_and_verifies():
    state, shas, index = _line_11_at_freeze()
    deletes, man, _, _ = R.plan_freeze(state, L, shas=shas, index=index, now="t")
    for _, k in deletes:
        state.pop(k)
    state[f"{L}MANIFEST.json"] = (1, None)
    again, man2, _, problems = R.plan_freeze(state, L, shas=shas, index=index, now="t")
    assert again == [] and problems == [] and man2["files"] == man["files"]
    idx = {"status": "frozen", "superseded_by": "v1/1.2"}
    root = R.build_root("1.2.0", "t")
    assert R.verify_frozen(state, L, man, idx, root) == []
    # a weekly full left behind, a missing file, or an index that still says current all fail
    state[f"{L}weekly/clinvar-gkm_2026-1031.json.gz"] = (10, None)
    state.pop(f"{L}clinvar-gkm_2026-09.json.gz")
    fails = R.verify_frozen(state, L, man, {"status": "current"}, root)
    assert any("should have been deleted" in f for f in fails)
    assert any("clinvar-gkm_2026-09.json.gz missing" in f for f in fails)
    assert any("status must be frozen" in f for f in fails)


def test_frozen_readme_and_index_notes():
    state, shas, index = _line_11_at_freeze()
    _, man, _, _ = R.plan_freeze(state, L, shas=shas, index=index, now="2026-11-20T00:00:00Z")
    text = R.frozen_readme(man)
    assert text.startswith("ClinVar-GKM v1/1.1 (schema 1.1.0) -- FROZEN\n")
    assert "frozen on 2026-11-20, when v1/1.2 replaced it" in text
    assert "https://data.clinvar-gkm.org/v1/1.2/index.json" in text
    assert "2026-09 <- 2026-08-29, 2026-10 <- 2026-09-28" in text and "2026-09-28 .. 2026-10-31" in text
    assert "Source, attribution and disclaimer" in text and "genetics professional" in text
    assert "archive/YYYY/" not in text
    idx = R.build_index(state, L, shas={}, sources={}, prev_index=None, schema_version="1.1.0", status="frozen",
                        superseded_by="v1/1.2/", parquet_manifest=None, now="t")
    assert idx["status"] == "frozen" and idx["superseded_by"] == "v1/1.2" and "frozen" in idx["notes"]


def test_freeze_cli_writes_manifest_and_readme(tmp_path, capsys):
    import json
    state, _, _ = _line_11_at_freeze()
    listing = tmp_path / "listing.txt"
    listing.write_text("".join(f"{s} {k}\n" for k, (s, _) in state.items()))
    mirror = tmp_path / "mirror"
    for k in state:
        rel = k[len(L):]
        if k.endswith(".json.gz") and "/weekly/" not in k:
            (mirror / rel).parent.mkdir(parents=True, exist_ok=True)
            (mirror / (rel + ".sha256")).write_text("b" * 64 + "  x\n")
        elif k.endswith(".manifest.json"):
            (mirror / rel).parent.mkdir(parents=True, exist_ok=True)
            (mirror / rel).write_text("{}")
    (mirror / "index.json").write_text(json.dumps(_line_11_at_freeze()[2]))
    out = tmp_path / "out"
    assert R.main(["freeze", "--listing", str(listing), "--line", L, "--sidecars", str(mirror),
                   "--out-dir", str(out)]) == 0
    printed = capsys.readouterr().out
    assert "PROBLEM" not in printed and f"DELETE 10 {L}parquet/scv.parquet" in printed
    man = json.loads((out / L / "MANIFEST.json").read_text())
    shas = {f["key"]: f["sha256"] for f in man["files"]}
    assert shas[f"{L}clinvar-gkm_2026-10.json.gz"] == "b" * 64
    assert shas[f"{L}deltas/clinvar-gkm-delta_2026-1031.manifest.json"] == R.hashlib.sha256(b"{}").hexdigest()
    assert (out / L / "README.txt").read_text().startswith("ClinVar-GKM v1/1.1")
