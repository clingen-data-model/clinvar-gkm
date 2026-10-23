#!/usr/bin/env python3
"""ClinVar-GKM R2 layout rules for a version line, in one place.

A version line is `v{major}/{major}.{minor}/` (e.g. `v1/1.1/`); PATCH releases extend the same line. The layout
mirrors NCBI's pub/clinvar/xml/ (monthly), xml/weekly_release/ and xml/archive/YYYY/, plus a deltas/ folder:

  <line>clinvar-gkm_YYYY-MM.json.gz            official monthly (ADR 0002: built from the newest release
                                                before ClinVar's monthly), + .sha256
  <line>clinvar-gkm_00-latest.json.gz          the same bytes as the newest monthly, + .sha256
  <line>index.json, <line>feed.xml
  <line>weekly/clinvar-gkm_YYYY-MMDD.json.gz   the CURRENT month's weekly full bundles, + .sha256
  <line>weekly/clinvar-gkm_00-latest_weekly.json.gz  + .sha256
  <line>deltas/clinvar-gkm-delta_YYYY-MMDD.json.gz   the current month's deltas, + .sha256 + .manifest.json
  <line>deltas/YYYY-MM/clinvar-gkm-delta_...         earlier months of the current year
  <line>archive/YYYY/clinvar-gkm_YYYY-MM.json.gz     prior years' monthlies (+ .sha256)
  <line>archive/YYYY/deltas/YYYY-MM/...              prior years' deltas
  <line>parquet/<section>.parquet, parquet/manifest.json   ONE Parquet set, overwritten every release

"Current month" is the month of the newest release posted to the line. When the first release of a new month is
posted (the rollover), the finished month's deltas move into deltas/YYYY-MM/ and its weekly fulls are deleted,
except the newest one, which is kept until the new month's official monthly is posted: it is the ADR 0002 source
candidate, so the monthly can be a server-side copy of it. When the first release of a new year is posted, the
prior year's monthlies and delta folders move into archive/YYYY/.

Every subcommand is pure: it reads a listing file (`aws s3 ls --recursive` output, or "SIZE KEY" lines) and local
files, and prints a plan or writes JSON. Nothing here talks to R2; the bash callers execute the plans.
"""
import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import sys
from xml.sax.saxutils import escape

BASE_URL = os.environ.get("R2_PUBLIC_URL", "https://data.clinvar-gkm.org")

# The version lines published at the bucket root, newest first. A new MINOR line adds an entry here (and the
# previous line becomes "frozen" with superseded_by set); schema None means "the pipeline's SCHEMA_VERSION".
LINES = {
    "v1/1.1/": {"status": "current", "schema": None, "superseded_by": None},
    "v1/1.0/": {"status": "frozen", "schema": "1.0.1", "superseded_by": "v1/1.1/"},
}
CURRENT_LINE = "v1/1.1/"

LATEST = "clinvar-gkm_00-latest.json.gz"
WEEKLY_LATEST = "weekly/clinvar-gkm_00-latest_weekly.json.gz"
_SUFFIX = r"(\.json\.gz|\.json\.gz\.sha256|\.manifest\.json)"
_PATTERNS = [
    ("monthly", re.compile(r"^clinvar-gkm_(?P<label>\d{4}-\d{2})(?P<sfx>\.json\.gz|\.json\.gz\.sha256)$")),
    ("latest", re.compile(r"^clinvar-gkm_00-latest(?P<sfx>\.json\.gz|\.json\.gz\.sha256)$")),
    ("weekly", re.compile(r"^weekly/clinvar-gkm_(?P<y>\d{4})-(?P<m>\d{2})(?P<d>\d{2})(?P<sfx>\.json\.gz|\.json\.gz\.sha256)$")),
    ("weekly_latest", re.compile(r"^weekly/clinvar-gkm_00-latest_weekly(?P<sfx>\.json\.gz|\.json\.gz\.sha256)$")),
    ("delta", re.compile(r"^(?P<dir>deltas/(?:\d{4}-\d{2}/)?|archive/\d{4}/deltas/\d{4}-\d{2}/)"
                         r"clinvar-gkm-delta_(?P<y>\d{4})-(?P<m>\d{2})(?P<d>\d{2})(?P<sfx>" + _SUFFIX[1:] + "$")),
    ("archive_monthly", re.compile(r"^archive/(?P<year>\d{4})/clinvar-gkm_(?P<label>\d{4}-\d{2})"
                                   r"(?P<sfx>\.json\.gz|\.json\.gz\.sha256)$")),
    ("parquet", re.compile(r"^parquet/(?P<name>[^/]+)$")),
    ("line_file", re.compile(r"^(?P<name>index\.json|feed\.xml|README\.txt|MANIFEST\.json)$")),
]


# ---------------------------------------------------------------------------------------------------------------
# Listing


# Source, attribution and disclaimer for the published data (ClinVar is the source; see the docs' Data Use and
# Citation page). Carried by parquet/manifest.json; the same text is in r2-readme.txt.
ATTRIBUTION = {
    "source": {
        "name": "ClinVar",
        "publisher": "National Center for Biotechnology Information (NCBI), U.S. National Library of Medicine",
        "url": "https://www.ncbi.nlm.nih.gov/clinvar/",
        "data_use_policy": "https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/#disclaimer",
        "citation": ("Landrum MJ, et al. ClinVar: updates to support classifications of both germline and somatic "
                     "variants. Nucleic Acids Res. 2025;53(D1):D1313-D1321. doi:10.1093/nar/gkae1090"),
    },
    "attribution": ("Derived from NCBI's ClinVar. If you use or redistribute these data, attribute ClinVar as the data "
                    "source and cite it; cite ClinVar-GKM (doi:10.5281/zenodo.18343663) if you used these files."),
    "disclaimer": ("ClinVar's disclaimer applies: the information is not intended for direct diagnostic use or "
                   "medical decision-making without review by a genetics professional. ClinVar-GKM is not an NCBI, "
                   "NLM or NIH product and is not endorsed by them."),
    "license": {
        "id": "CC0-1.0",
        "scope": ("CC0 covers ClinGen's contribution (the code and this published transformation) only. It adds no "
                  "restriction, and it cannot grant rights that NCBI or ClinVar's submitters hold."),
    },
    "data_use": "https://dataexchange.clinicalgenome.org/clinvar-gkm/data-use/",
}


def read_listing(path):
    """{key: (size, modified)} from `aws s3 ls --recursive` output ("DATE TIME SIZE KEY") or "SIZE KEY" lines."""
    objs = {}
    with open(path) as fh:
        for line in fh:
            parts = line.split()
            if len(parts) >= 4 and re.match(r"^\d{4}-\d{2}-\d{2}$", parts[0]):
                objs[parts[3]] = (int(parts[2]), parts[0])
            elif len(parts) == 2 and parts[0].isdigit():
                objs[parts[1]] = (int(parts[0]), None)
    return objs


def classify(rel):
    """(kind, info) for a key relative to its line, or (None, {}) when it is not part of the layout."""
    for kind, rx in _PATTERNS:
        m = rx.match(rel)
        if m:
            info = m.groupdict()
            if "y" in info and info.get("y"):
                info["release"] = f"{info['y']}-{info['m']}-{info['d']}"
            return kind, info
    return None, {}


def line_objects(objs, line):
    """[(rel, size, modified, kind, info)] for every key under the line."""
    out = []
    for key, (size, mod) in sorted(objs.items()):
        if key.startswith(line):
            rel = key[len(line):]
            kind, info = classify(rel)
            out.append((rel, size, mod, kind, info))
    return out


def ymd_to_compact(release):
    return f"{release[:4]}-{release[5:7]}{release[8:10]}"


# ---------------------------------------------------------------------------------------------------------------
# Path rules


def delta_dir(release, current_month):
    """Line-relative folder for a delta of `release` when `current_month` (YYYY-MM) is the line's current month."""
    month, year = release[:7], release[:4]
    if month >= current_month:
        return "deltas/"
    if year < current_month[:4]:
        return f"archive/{year}/deltas/{month}/"
    return f"deltas/{month}/"


def monthly_dir(label, current_year):
    return "" if label[:4] >= current_year else f"archive/{label[:4]}/"


def newest_release(objs, line):
    rels = [i["release"] for _, _, _, k, i in line_objects(objs, line) if k in ("weekly", "delta")]
    return max(rels) if rels else None


def current_month(objs, line, release=None):
    months = [r[:7] for r in (newest_release(objs, line), release) if r]
    return max(months) if months else None


# ---------------------------------------------------------------------------------------------------------------
# Rollover


def plan_rollover(objs, line, release):
    """Moves and deletes that bring the line to the layout for a newly posted `release` (YYYY-MM-DD).

    Returns (moves, deletes, notes): moves = [(size, src, dst)], deletes = [(size, key)] (bucket keys).
    Idempotent: re-running after the plan is applied yields no actions.
    """
    newest = newest_release(objs, line)
    if newest and newest > release:
        raise SystemExit(f"ERROR: {release} is older than the newest release in {line} ({newest}); "
                         "a rollover runs only for the newest release")
    cur_month, cur_year = release[:7], release[:4]
    items = line_objects(objs, line)
    moves, deletes, notes = [], [], []

    for rel, size, _, kind, info in items:
        if kind == "delta":
            want = delta_dir(info["release"], cur_month)
            if info["dir"] != want:
                moves.append((size, line + rel, line + want + rel[len(info["dir"]):]))
        elif kind in ("monthly", "archive_monthly"):
            want = monthly_dir(info["label"], cur_year)
            have = "" if kind == "monthly" else f"archive/{info['year']}/"
            if have != want:
                moves.append((size, line + rel, line + want + f"clinvar-gkm_{info['label']}{info['sfx']}"))

    # Weekly fulls of finished months are deleted. The newest of them is kept while the current month's
    # official monthly is not yet posted: it is that monthly's ADR 0002 source candidate.
    old = sorted({i["release"] for _, _, _, k, i in items if k == "weekly" and i["release"][:7] < cur_month})
    monthly_posted = any(k == "monthly" and i["label"] == cur_month and i["sfx"] == ".json.gz"
                         for _, _, _, k, i in items)
    keep = old[-1] if old and not monthly_posted else None
    if keep:
        notes.append(f"keep weekly/clinvar-gkm_{ymd_to_compact(keep)}.json.gz until the {cur_month} monthly is "
                     "posted (ADR 0002 source candidate)")
    for rel, size, _, kind, info in items:
        if kind == "weekly" and info["release"][:7] < cur_month and info["release"] != keep:
            deletes.append((size, line + rel))
    return moves, deletes, notes


# ---------------------------------------------------------------------------------------------------------------
# Index, feed, root


def _sha(shas, key):
    v = shas.get(key)
    return v if v and re.fullmatch(r"[0-9a-f]{64}", v) else None


def read_shas(sidecar_dir, prefix=""):
    """{bundle key: sha256} from a local mirror of the *.sha256 sidecars (first token of each file)."""
    shas = {}
    if not sidecar_dir or not os.path.isdir(sidecar_dir):
        return shas
    for root, _, files in os.walk(sidecar_dir):
        for f in files:
            if f.endswith(".sha256"):
                p = os.path.join(root, f)
                rel = os.path.relpath(p, sidecar_dir).replace(os.sep, "/")
                with open(p) as fh:
                    tok = (fh.read().split() or [""])[0]
                shas[prefix + rel[: -len(".sha256")]] = tok
    return shas


def _entry(line, rel, size, mod, shas, **extra):
    e = {"name": rel.rsplit("/", 1)[-1], "path": line + rel, "size": size, "sha256": _sha(shas, line + rel),
         "modified": mod}
    e.update(extra)
    return e


def _monthly_pool(index):
    """Every dated official monthly in a line index (top level and archives), excluding the 00-latest copy."""
    ds = (index.get("datasets") or {})
    pool = [m for m in ds.get("monthly", []) if not m.get("latest")]
    pool += [m for y in (index.get("archives") or {}).values() for m in y.get("monthly", [])]
    return pool


def build_index(objs, line, *, shas, sources, prev_index, schema_version, status, superseded_by,
                parquet_manifest, now):
    """The line's index.json. Shape (read by the docs' R2 browser, console and replay recipe):

    datasets.monthly[]  {name, path, size, sha256, release (YYYY-MM), source_release, modified, latest}; the
                        00-latest copy is an entry with latest: true and the release it equals
    datasets.weekly[]   {name, path, size, sha256, release (YYYY-MM-DD), modified, latest}; 00-latest_weekly has
                        latest: true
    deltas[]            {release, month, path (folder), manifest (full path), bundle {path, sha256, size}, modified}
    archives            {"YYYY": {monthly: [...], deltas: [...]}}
    parquet             {path, manifest, source_release, ...} or null
    """
    items = line_objects(objs, line)
    src = {m["release"]: m["source_release"] for m in _monthly_pool(prev_index or {}) if m.get("source_release")}
    src.update(sources)

    monthly, archives, deltas, weekly = [], {}, [], []
    latest = weekly_latest = None
    manifests = {line + rel for rel, _, _, k, i in items if k == "delta" and i["sfx"] == ".manifest.json"}
    for rel, size, mod, kind, info in items:
        if info.get("sfx") not in (".json.gz", None):
            continue
        if kind == "monthly":
            monthly.append(_entry(line, rel, size, mod, shas, release=info["label"],
                                  source_release=src.get(info["label"]), latest=False))
        elif kind == "archive_monthly":
            archives.setdefault(info["year"], {"monthly": [], "deltas": []})["monthly"].append(
                _entry(line, rel, size, mod, shas, release=info["label"], source_release=src.get(info["label"]),
                       latest=False))
        elif kind == "latest":
            latest = _entry(line, rel, size, mod, shas, latest=True)
        elif kind == "weekly":
            weekly.append(_entry(line, rel, size, mod, shas, release=info["release"], latest=False))
        elif kind == "weekly_latest":
            weekly_latest = _entry(line, rel, size, mod, shas, latest=True)
        elif kind == "delta":
            man = line + rel[: -len(".json.gz")] + ".manifest.json"
            e = {"release": info["release"], "month": info["release"][:7], "path": line + info["dir"],
                 "manifest": man if man in manifests else None,
                 "bundle": {"path": line + rel, "sha256": _sha(shas, line + rel), "size": size}, "modified": mod}
            if info["dir"].startswith("archive/"):
                archives.setdefault(info["release"][:4], {"monthly": [], "deltas": []})["deltas"].append(e)
            else:
                deltas.append(e)

    def same_as(ptr, pool):   # which dated file a 00-latest copy equals (sha256 first, size as a fallback)
        for e in sorted(pool, key=lambda x: x["release"], reverse=True):
            if (ptr["sha256"] and ptr["sha256"] == e["sha256"]) or (not ptr["sha256"] and ptr["size"] == e["size"]):
                return e
        return None

    monthly.sort(key=lambda e: e["release"])
    weekly.sort(key=lambda e: e["release"])
    if latest:
        m = same_as(latest, monthly)
        latest.update(release=m["release"] if m else None, source_release=m["source_release"] if m else None)
        monthly.append(latest)
    if weekly_latest:
        w = same_as(weekly_latest, weekly)
        weekly_latest.update(release=w["release"] if w else None)
        weekly.append(weekly_latest)

    all_releases = [d["release"] for d in deltas] + [d["release"] for y in archives.values() for d in y["deltas"]]
    all_releases += [w["release"] for w in weekly if not w["latest"] and w["release"]]
    cur = max(all_releases, default=None)
    parquet = None
    if parquet_manifest:
        parquet = {"path": line + "parquet/", "manifest": line + "parquet/manifest.json"}
        for k in ("source_release", "dataset", "build_date", "builder", "table_spec_version", "schema_version"):
            parquet[k] = parquet_manifest.get(k)
        files = parquet_manifest.get("files") or []
        parquet["file_count"] = len(files)
        parquet["size"] = sum(f.get("size", 0) for f in files)
    elif any(k == "parquet" and i["name"].endswith(".parquet") for _, _, _, k, i in items):
        parquet = {"path": line + "parquet/", "manifest": None, "source_release": None}

    return {
        "description": f"ClinVar-GKM release index, line {line.rstrip('/')}",
        "line": line.rstrip("/"),
        "status": status,
        "superseded_by": superseded_by.rstrip("/") if superseded_by else None,
        "schema_version": schema_version,
        "updated_at": now,
        "base_url": BASE_URL,
        "current_month": cur[:7] if cur else None,
        "latest_release": cur,
        "datasets": {"monthly": monthly, "weekly": weekly},
        "deltas": sorted(deltas, key=lambda e: e["release"]),
        "archives": {y: {"monthly": sorted(v["monthly"], key=lambda e: e["release"]),
                         "deltas": sorted(v["deltas"], key=lambda e: e["release"])}
                     for y, v in sorted(archives.items())},
        "parquet": parquet,
        "notes": ("Paths are relative to base_url. Each monthly's source_release is the weekly release it was "
                  "built from (ADR 0002). datasets.weekly holds only the current month's weekly fulls; earlier "
                  "weeks are rebuilt from a monthly plus the deltas. Parquet is one derived set, overwritten every "
                  "release (parquet/manifest.json)."),
    }


def build_feed(index, line, now, cap=25):
    entries = []
    for e in _monthly_pool(index):
        entries.append((e["release"] + "-99", "monthly", e["release"], e["path"], e))
    for e in index["deltas"] + [d for y in index["archives"].values() for d in y["deltas"]]:
        entries.append((e["release"], "delta", e["release"], e["bundle"]["path"], e))
    entries.sort(key=lambda x: x[0], reverse=True)
    self_url = f"{BASE_URL}/{line}feed.xml"
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<feed xmlns="http://www.w3.org/2005/Atom">',
           f"  <title>ClinVar-GKM {escape(line.rstrip('/'))} releases</title>",
           f"  <id>{escape(self_url)}</id>", f"  <updated>{now}</updated>",
           f'  <link rel="self" href="{escape(self_url)}"/>',
           f'  <link rel="alternate" href="{escape(BASE_URL + "/" + line + "index.json")}"/>']
    for _, kind, label, path, e in entries[:cap]:
        href = f"{BASE_URL}/{path}"
        updated = f"{e['modified']}T00:00:00Z" if e.get("modified") else now
        # A stable id: deltas move between folders at rollover, so the URL is not an identity.
        out += ["  <entry>", f"    <title>ClinVar-GKM {escape(line.rstrip('/'))} {kind} {escape(label)}</title>",
                f"    <id>tag:clinvar-gkm.org,2026:{escape(line)}{kind}/{escape(label)}</id>",
                f"    <updated>{updated}</updated>", f'    <link href="{escape(href)}"/>', "  </entry>"]
    out.append("</feed>")
    return "\n".join(out) + "\n"


def build_root(schema_version, now):
    """Root index.json: `versions` keyed by line ("1.1"); consumers pick the entry with status == "current"."""
    versions = {}
    for line, cfg in LINES.items():
        name = line.split("/")[1]
        major, minor = name.split(".")
        versions[name] = {
            "line": line.rstrip("/"), "major": int(major), "minor": int(minor), "status": cfg["status"],
            "schema": cfg["schema"] or schema_version,
            "superseded_by": cfg["superseded_by"].rstrip("/") if cfg["superseded_by"] else None,
            "index": line + "index.json", "feed": line + "feed.xml"}
    return {"manifest_version": 2, "updated_at": now, "base_url": BASE_URL,
            "current": CURRENT_LINE.rstrip("/"), "versions": versions}


# ---------------------------------------------------------------------------------------------------------------
# Delta manifest: checkpoint_full + sha256 + schema version


def checkpoint_for(index, baseline):
    """The newest official monthly whose source_release <= baseline (a delta replays onto it).

    Shape {path, release, month, sha256}: `release` is the monthly's SOURCE release (the weekly release whose state
    it holds, comparable with baseline_release); `month` is its YYYY-MM label.
    """
    pool = _monthly_pool(index)
    unknown = [m["release"] for m in pool if not m.get("source_release")]
    if unknown:
        raise SystemExit(f"ERROR: monthly source_release unknown for {unknown}; pass --source YYYY-MM=YYYY-MM-DD "
                         "to the index generator first")
    ok = [m for m in pool if baseline and m["source_release"] <= baseline]
    if not ok:
        return None
    m = max(ok, key=lambda x: (x["source_release"], x["release"]))
    return {"path": m["path"], "release": m["source_release"], "month": m["release"], "sha256": m.get("sha256")}


def bundle_schema_version(path):
    with gzip.open(path, "rb") as fh:
        head = fh.read(4096).decode("utf-8", "replace")
    m = re.search(r'"schema_version"\s*:\s*"([^"]+)"', head)
    return m.group(1) if m else None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------------------------------------------
# Migration helpers: cleanup list, 1.0.1 archive -> frozen v1/1.0/


def plan_cleanup(objs, keep_lines=tuple(LINES)):
    """Every key outside the planned layout: not under a published line and not the root index.json."""
    return [(size, key) for key, (size, _) in sorted(objs.items())
            if key != "index.json" and not any(key.startswith(p) for p in keep_lines)]


def unexpected_in_lines(objs, keep_lines=tuple(LINES)):
    return [key for key in sorted(objs) for p in keep_lines
            if key.startswith(p) and classify(key[len(p):])[0] is None]


_V1_MONTHLY = re.compile(r"^v1/datasets/(clinvar-gkm_(?:\d{4}-\d{2}|00-latest)\.json\.gz)$")
_V1_DELTA = re.compile(r"^v1/deltas/(\d{4})-(\d{2})(\d{2})/(clinvar-gkm-delta_\d{4}-\d{4}\.json\.gz|manifest\.json)$")


def plan_move_10(manifest, archive_prefix, dest_line, now):
    """Copies that lay the archived 1.0.1 generation out as the frozen line, plus the new MANIFEST and sidecars.

    Returns (copies [(size, src, dst)], dropped [original_key], sidecars {dst_key: text}, new_manifest).
    """
    copies, dropped, sidecars, files = [], [], {}, []
    for f in manifest["files"]:
        ok = f["original_key"]
        m, d = _V1_MONTHLY.match(ok), _V1_DELTA.match(ok)
        if m:
            dst = dest_line + m.group(1)
        elif d:
            y, mo, dd, name = d.groups()
            fname = name if name != "manifest.json" else f"clinvar-gkm-delta_{y}-{mo}{dd}.manifest.json"
            dst = f"{dest_line}deltas/{y}-{mo}/{fname}"
        else:
            dropped.append(ok)
            continue
        copies.append((f["size"], f["archive_key"], dst))
        if dst.endswith(".json.gz"):
            sidecars[dst + ".sha256"] = f"{f['sha256']}  {dst.rsplit('/', 1)[-1]}\n"
        files.append({"key": dst, "size": f["size"], "sha256": f["sha256"], "original_key": ok,
                      "original_last_modified": f.get("original_last_modified"),
                      "schema_version": f.get("schema_version")})
    new_manifest = {
        "line": dest_line.rstrip("/"), "status": "frozen", "superseded_by": CURRENT_LINE.rstrip("/"),
        "schema_version": manifest.get("schema_version"), "frozen_at": now, "moved_from": archive_prefix,
        "base_url": manifest.get("base_url", BASE_URL),
        "notes": ("The 1.0.1 generation, frozen. Nothing under this line changes. Files keep their 1.0.1 bytes "
                  "(sha256 below); original_key is where each was first published. Paths inside the delta "
                  "manifests still name the original v1/datasets/ and v1/deltas/ keys, and their checkpoint_full "
                  "always says 2026-10; use index.json (each monthly's source_release) instead."),
        "file_count": len(files), "total_size": sum(f["size"] for f in files), "files": files}
    return copies, dropped, sidecars, new_manifest


# ---------------------------------------------------------------------------------------------------------------
# CLI


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gb(n):
    return f"{n / 1e9:.2f} GB"


def _sources(pairs):
    out = {}
    for p in pairs or []:
        label, _, date = p.partition("=")
        if not (re.fullmatch(r"\d{4}-\d{2}", label) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", date)):
            raise SystemExit(f"ERROR: --source wants YYYY-MM=YYYY-MM-DD, got {p!r}")
        out[label] = date
    return out


def _load_json(path):
    if path and os.path.isfile(path) and os.path.getsize(path) > 0:
        with open(path) as fh:
            return json.load(fh)
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("rollover", help="move/delete plan for a newly posted release")
    p.add_argument("--listing", required=True)
    p.add_argument("--line", default=CURRENT_LINE)
    p.add_argument("--release", required=True)

    p = sub.add_parser("delta-dir", help="bucket folder for a delta")
    p.add_argument("--listing", required=True)
    p.add_argument("--line", default=CURRENT_LINE)
    p.add_argument("--release", required=True)
    p.add_argument("--current-month")

    p = sub.add_parser("current-month")
    p.add_argument("--listing", required=True)
    p.add_argument("--line", default=CURRENT_LINE)
    p.add_argument("--release")

    p = sub.add_parser("index", help="line index.json + feed.xml")
    p.add_argument("--listing", required=True)
    p.add_argument("--line", default=CURRENT_LINE)
    p.add_argument("--sidecars", help="local mirror of the line (sidecars, parquet/manifest.json, index.json)")
    p.add_argument("--source", action="append", help="monthly source release, YYYY-MM=YYYY-MM-DD (repeatable)")
    p.add_argument("--schema-version", required=True)
    p.add_argument("--out-index", required=True)
    p.add_argument("--out-feed", required=True)

    p = sub.add_parser("root", help="bucket-root index.json")
    p.add_argument("--schema-version", required=True)
    p.add_argument("--out", required=True)

    p = sub.add_parser("checkpoint", help="checkpoint_full for a baseline release")
    p.add_argument("--index", required=True)
    p.add_argument("--baseline")

    p = sub.add_parser("patch-manifest", help="add checkpoint_full, sha256 and schema_version to a delta manifest")
    p.add_argument("--manifest", required=True)
    p.add_argument("--bundle", required=True)
    p.add_argument("--index", help="the line's current index.json (for checkpoint_full)")
    p.add_argument("--previous-release", help="the newest delta already in the line")
    p.add_argument("--allow-gap", action="store_true")
    p.add_argument("--dir", required=True, help="bucket folder the delta is published in")

    p = sub.add_parser("parquet-manifest")
    p.add_argument("--dir", required=True)
    p.add_argument("--release", required=True)
    p.add_argument("--dataset", required=True)
    p.add_argument("--schema-version", required=True)
    p.add_argument("--builder", default="BigQuery export")
    p.add_argument("--table-spec-version")
    p.add_argument("--out", required=True)

    p = sub.add_parser("cleanup", help="keys outside the planned layout")
    p.add_argument("--listing", required=True)

    p = sub.add_parser("move-1.0", help="lay archive/1.0.1/ out as the frozen line v1/1.0/")
    p.add_argument("--manifest", required=True)
    p.add_argument("--archive", default="archive/1.0.1/")
    p.add_argument("--dest", default="v1/1.0/")
    p.add_argument("--out-dir", required=True, help="writes MANIFEST.json and the sidecars here (by key)")

    a = ap.parse_args(argv)
    now = _now()

    if a.cmd == "rollover":
        moves, deletes, notes = plan_rollover(read_listing(a.listing), a.line, a.release)
        for n in notes:
            print(f"# {n}")
        for size, src, dst in moves:
            print(f"MOVE {size} {src} {dst}")
        for size, key in deletes:
            print(f"DELETE {size} {key}")
    elif a.cmd == "delta-dir":
        objs = read_listing(a.listing)
        cur = a.current_month or current_month(objs, a.line, a.release)
        print(a.line + delta_dir(a.release, cur))
    elif a.cmd == "current-month":
        print(current_month(read_listing(a.listing), a.line, a.release) or "")
    elif a.cmd == "index":
        objs = read_listing(a.listing)
        cfg = LINES.get(a.line, {"status": "current", "schema": None, "superseded_by": None})
        shas = read_shas(a.sidecars, a.line) if a.sidecars else {}
        prev = _load_json(os.path.join(a.sidecars, "index.json")) if a.sidecars else None
        pq = _load_json(os.path.join(a.sidecars, "parquet", "manifest.json")) if a.sidecars else None
        idx = build_index(objs, a.line, shas=shas, sources=_sources(a.source), prev_index=prev,
                          schema_version=cfg["schema"] or a.schema_version, status=cfg["status"],
                          superseded_by=cfg["superseded_by"], parquet_manifest=pq, now=now)
        with open(a.out_index, "w") as fh:
            json.dump(idx, fh, indent=1)
        with open(a.out_feed, "w") as fh:
            fh.write(build_feed(idx, a.line, now))
        ds = idx["datasets"]
        dated = [m for m in ds["monthly"] if not m["latest"]]
        missing = [m["release"] for m in dated if not m["source_release"]]
        lat = [m["release"] for m in ds["monthly"] if m["latest"]]
        print(f"  {a.line}: {len(dated)} monthly, 00-latest={lat[0] if lat else None}, "
              f"{len([w for w in ds['weekly'] if not w['latest']])} weekly, {len(idx['deltas'])} deltas, "
              f"{len(idx['archives'])} archive years, parquet={'yes' if idx['parquet'] else 'no'}"
              + (f"; WARNING source_release unknown for {missing}" if missing else ""))
    elif a.cmd == "root":
        with open(a.out, "w") as fh:
            json.dump(build_root(a.schema_version, now), fh, indent=1)
    elif a.cmd == "checkpoint":
        print(json.dumps(checkpoint_for(_load_json(a.index) or {}, a.baseline)))
    elif a.cmd == "patch-manifest":
        with open(a.manifest) as fh:
            man = json.load(fh)
        baseline = man.get("baseline_release")
        if a.previous_release and baseline != a.previous_release and not a.allow_gap:
            raise SystemExit(f"ERROR: delta {man.get('release')} has baseline_release {baseline}, but the newest "
                             f"delta in the line is {a.previous_release}: the chain would have a gap")
        idx = _load_json(a.index) or {}
        name = f"clinvar-gkm-delta_{ymd_to_compact(man['release'])}.json.gz"
        man["schema_version"] = bundle_schema_version(a.bundle)
        man["bundle"] = {"name": name, "path": a.dir + name, "size": os.path.getsize(a.bundle),
                         "sha256": sha256_file(a.bundle)}
        man["sha256"] = man["bundle"]["sha256"]
        man["checkpoint_full"] = checkpoint_for(idx, baseline) if idx else None
        with open(a.manifest, "w") as fh:
            json.dump(man, fh, indent=2)
        print(json.dumps({k: man[k] for k in ("release", "baseline_release", "compare_release", "schema_version",
                                               "sha256", "checkpoint_full")}))
    elif a.cmd == "parquet-manifest":
        files = []
        for f in sorted(os.listdir(a.dir)):
            if f.endswith(".parquet"):
                p = os.path.join(a.dir, f)
                files.append({"name": f, "size": os.path.getsize(p), "sha256": sha256_file(p)})
        man = {"derived": True, "build_date": now, "source_release": a.release, "dataset": a.dataset,
               "builder": a.builder, "table_spec_version": a.table_spec_version, "schema_version": a.schema_version,
               "note": ("One Parquet set, rebuilt from the newest release and overwritten every release. It is "
                        "derived from the JSON bundle; past states are rebuilt from the monthly bundles."),
               **ATTRIBUTION, "files": files}
        with open(a.out, "w") as fh:
            json.dump(man, fh, indent=1)
        print(f"  parquet/manifest.json: {len(files)} files, {_gb(sum(f['size'] for f in files))}")
    elif a.cmd == "cleanup":
        objs = read_listing(a.listing)
        for size, key in plan_cleanup(objs):
            print(f"DELETE {size} {key}")
        for key in unexpected_in_lines(objs):
            print(f"# unexpected (inside a line, not deleted): {key}")
    elif a.cmd == "move-1.0":
        with open(a.manifest) as fh:
            man = json.load(fh)
        copies, dropped, sidecars, new_man = plan_move_10(man, a.archive, a.dest, now)
        for key, text in sidecars.items():
            p = os.path.join(a.out_dir, key)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as fh:
                fh.write(text)
        os.makedirs(os.path.join(a.out_dir, a.dest), exist_ok=True)
        with open(os.path.join(a.out_dir, a.dest, "MANIFEST.json"), "w") as fh:
            json.dump(new_man, fh, indent=1)
        for key in dropped:
            print(f"# not carried into {a.dest}: {key}")
        for size, src, dst in copies:
            print(f"COPY {size} {src} {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
