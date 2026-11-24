#!/usr/bin/env python3
"""Build a history table (slowly changing dimension, type 2) of the ClinVar-GKM SCV, VCV and RCV statements.

  python3 track-history.py base FULL.json.gz [--line v1/1.1]   start from a monthly full
  python3 track-history.py base --from-release 2026-06-27      or start from nothing, deltas only
  python3 track-history.py update [--to 2026-11-15]             add every delta after the history's last release
  python3 track-history.py extract BUNDLE.json.gz OUT.parquet   one release's statements, to compare two releases

One row per statement record and the releases it was current for:

  history(section, stable_id, key, proposition, classification, review_status, submitter, valid_from, valid_to)

`key` is the bundle key (it carries ClinVar's version); `stable_id` is the key without the version, so the rows
of one SCV, VCV or RCV across versions share it. `valid_to` is the release whose delta deleted or replaced the
row, NULL while it is current. Every path comes from the root index.json and the lines' index.json, and every
download is checked by its sha256. Needs Python 3.9 or later and the duckdb package.
https://clinvar-gkm.org/build/track-change/
"""
import argparse
import gzip
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import urllib.request

import duckdb

BASE = "https://data.clinvar-gkm.org"
SECTION = re.compile(rb'^  "([A-Za-z0-9_]+)": \{\n$')
SCHEMA_VERSION = re.compile(rb'^  "schema_version": ("[^"]*"),?\n$')


class Refused(Exception):
    pass


# --- downloads ---------------------------------------------------------------------------------------------------

def fetch(path, dest=None):
    """GET BASE/path (retrying), returning the bytes or writing them to dest."""
    for attempt in range(5):
        try:
            req = urllib.request.Request(f"{BASE}/{path.lstrip('/')}",
                                         headers={"User-Agent": "clinvar-gkm-track-history/1"})
            with urllib.request.urlopen(req, timeout=120) as r:
                if dest is None:
                    return r.read()
                with open(dest + ".part", "wb") as f:
                    while chunk := r.read(1 << 20):
                        f.write(chunk)
                os.replace(dest + ".part", dest)
                return dest
        except OSError as e:
            if attempt == 4:
                raise
            print(f"retrying {path}: {e}", file=sys.stderr)
            time.sleep(2 ** attempt)


def fetch_json(path):
    return json.loads(fetch(path))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def read_bundle(path):
    """Yield ("schema_version", value) and ("record", section, key, json_text) from a published bundle.

    Reads the layout the bundles are written in: a `"schema_version"` line, each section opened by
    `  "<section>": {`, one `    "<key>": {...}` record per line, closed by `  }`. Any other line stops it."""
    section = None
    with gzip.open(path, "rb") as f:
        for n, line in enumerate(f, 1):
            if line.startswith(b'    "') and section:
                body = line[4:].rstrip(b"\n").removesuffix(b",")
                key, end = json.JSONDecoder().raw_decode(body.decode())
                if body[end:end + 2] != b": " or b"\t" in body:
                    raise ValueError(f"{path}: line {n}: not a record line")
                yield "record", section, key, body[end + 2:].decode()
            elif m := SECTION.match(line):
                section = m.group(1).decode()
            elif line in (b"  }\n", b"  },\n"):
                section = None
            elif m := SCHEMA_VERSION.match(line):
                yield "schema_version", json.loads(m.group(1))
            elif line.rstrip(b"\n") not in (b"{", b"}"):
                raise ValueError(f"{path}: line {n}: not the published bundle layout")


SECTIONS = ("scv", "vcv", "rcv")
VERSION = re.compile(r"^(clinvar\.submission:)?((?:SCV|VCV|RCV)\d+)\.\d+")


def row(section, key, text):
    r = json.loads(text)
    ext = {e["name"]: e.get("value") for e in r.get("extensions", [])}
    submitted = [c["contributor"] for c in r.get("contributions", []) if c.get("activityType") == "submitted"]
    return {
        "section": section,
        "stable_id": VERSION.sub(r"\2", key),
        "key": key,
        "proposition": (r.get("proposition") or "").rsplit("/", 1)[-1],
        "classification": (r.get("classification") or {}).get("name"),
        "review_status": ext.get("clinvarScvReviewStatus") or ext.get("clinvarReviewStatus"),
        "submitter": submitted[0].rsplit("/", 1)[-1] if submitted else None,
    }


def insert_rows(con, path, valid_from):
    """Add a row, valid from `valid_from`, for every SCV, VCV and RCV record of a bundle. Returns schema_version."""
    schema_version, batch = None, []

    def flush():
        with tempfile.NamedTemporaryFile("w", suffix=".ndjson", delete=False, encoding="utf-8") as f:
            f.writelines(json.dumps(r) + "\n" for r in batch)
        try:
            con.execute(f"""INSERT INTO history SELECT *, ?::VARCHAR, NULL::VARCHAR FROM read_json('{f.name}',
                format='newline_delimited', columns={{section:'VARCHAR', stable_id:'VARCHAR', key:'VARCHAR',
                proposition:'VARCHAR', classification:'VARCHAR', review_status:'VARCHAR', submitter:'VARCHAR'}})""",
                        [valid_from])
        finally:
            os.unlink(f.name)
        batch.clear()

    for event in read_bundle(path):
        if event[0] == "schema_version":
            schema_version = event[1]
        elif event[1] in SECTIONS:
            batch.append(row(*event[1:]))
            if len(batch) == 500_000:
                flush()
    flush()
    return schema_version


def connect(db):
    con = duckdb.connect(db)
    con.execute("""CREATE TABLE IF NOT EXISTS history (section VARCHAR, stable_id VARCHAR, key VARCHAR,
        proposition VARCHAR, classification VARCHAR, review_status VARCHAR, submitter VARCHAR,
        valid_from VARCHAR, valid_to VARCHAR)""")
    con.execute("CREATE TABLE IF NOT EXISTS history_state (last_release VARCHAR, base VARCHAR)")
    return con


def releases():
    """Every delta on the host, oldest first. A release published in more than one line comes from the newest
    line: v1/1.1 republished the 1.0.1 weeks, and each line starts where the line before it ends."""
    root, best = fetch_json("index.json"), {}
    for v in sorted(root["versions"].values(), key=lambda v: (v["major"], v["minor"])):
        index = fetch_json(v["index"])
        deltas = list(index["deltas"])
        for year in index.get("archives", {}).values():
            deltas += year.get("deltas", [])
        for d in deltas:
            best[d["release"]] = {**d, "line": v["line"]}
    return [best[r] for r in sorted(best)]


def cmd_base(con, args):
    if con.execute("SELECT count(*) FROM history_state").fetchone()[0]:
        raise Refused(f"{args.db} already has a history")
    if args.from_release:
        release, base = args.from_release, f"deltas only, from {args.from_release}"
    else:
        index = fetch_json(f"{args.line}/index.json")
        monthlies = list(index["datasets"]["monthly"])
        for year in index.get("archives", {}).values():
            monthlies += year.get("monthly", [])
        sha = sha256_file(args.full)
        entry = next((m for m in monthlies if m["sha256"] == sha), None)
        if entry is None:
            raise Refused(f"{args.full} is not a monthly listed in {args.line}/index.json")
        release, base = entry["source_release"], entry["path"]
        insert_rows(con, args.full, release)
    con.execute("INSERT INTO history_state VALUES (?, ?)", [release, base])
    print(f"history starts at {release} ({base})")


def cmd_update(con, args):
    last, base = con.execute("SELECT last_release, base FROM history_state").fetchone()
    os.makedirs(args.cache, exist_ok=True)
    for d in releases():
        if d["release"] <= last or (args.to and d["release"] > args.to):
            continue
        manifest = fetch_json(d["manifest"])
        if manifest["baseline_release"] != last:
            raise Refused(f"broken chain: the {d['release']} delta builds on {manifest['baseline_release']}, "
                          f"the history is at {last}")
        path = os.path.join(args.cache, os.path.basename(d["bundle"]["path"]))
        if not (os.path.exists(path) and sha256_file(path) == d["bundle"]["sha256"]):
            fetch(d["bundle"]["path"], path)
            if sha256_file(path) != d["bundle"]["sha256"]:
                raise Refused(f"{path}: sha256 differs from index.json")
        con.execute("BEGIN")
        con.execute("CREATE OR REPLACE TEMP TABLE gone AS SELECT unnest(?::VARCHAR[]) AS key",
                    [[k for s in SECTIONS for k in manifest["sections"].get(s, {}).get("deleted", [])]])
        before = con.execute("SELECT count(*) FROM history").fetchone()[0]
        insert_rows(con, path, d["release"])
        # Close the current row of every key the delta deletes or replaces (the new rows stay open).
        con.execute("""UPDATE history SET valid_to = ? WHERE valid_to IS NULL AND valid_from < ?
            AND key IN (SELECT key FROM gone UNION ALL SELECT key FROM history WHERE valid_from = ?)""",
                    [d["release"], d["release"], d["release"]])
        con.execute("UPDATE history_state SET last_release = ?", [d["release"]])
        con.execute("COMMIT")
        added = con.execute("SELECT count(*) FROM history").fetchone()[0] - before
        print(f"{d['release']} ({d['line']}): {added} statement rows added")
        last = d["release"]
    print(f"history at {last}")


def cmd_extract(con, args):
    """Write one release's statements (no history) to a Parquet file, to compare two releases."""
    work = args.out + ".work.duckdb"
    db = connect(work)
    try:
        schema_version = insert_rows(db, args.full, None)
        db.execute(f"COPY (SELECT * EXCLUDE (valid_from, valid_to) FROM history) TO '{args.out}' (FORMAT parquet)")
        n = db.execute("SELECT count(*) FROM history").fetchone()[0]
    finally:
        db.close()
        for f in (work, work + ".wal"):
            if os.path.exists(f):
                os.remove(f)
    print(f"{args.out}: {n} statements, schema {schema_version}")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--db", default="clinvar-gkm-history.duckdb")
    p.add_argument("--cache", default="gkm-cache")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("base")
    b.add_argument("full", nargs="?")
    b.add_argument("--line", default="v1/1.1", help="the line the monthly is from (default v1/1.1)")
    b.add_argument("--from-release", help="start from nothing at this release, and add only deltas")
    u = sub.add_parser("update")
    u.add_argument("--to", help="stop at this release (default: the newest)")
    x = sub.add_parser("extract")
    x.add_argument("full")
    x.add_argument("out")
    args = p.parse_args()
    if args.cmd == "base" and bool(args.full) == bool(args.from_release):
        p.error("base takes a monthly full or --from-release, not both")
    con = None if args.cmd == "extract" else connect(args.db)
    try:
        {"base": cmd_base, "update": cmd_update, "extract": cmd_extract}[args.cmd](con, args)
    except Refused as e:
        sys.exit(f"refused: {e}")


if __name__ == "__main__":
    main()
