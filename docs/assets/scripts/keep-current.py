#!/usr/bin/env python3
"""Keep a local copy of the ClinVar-GKM records current by applying the weekly deltas.

The copy is a DuckDB database with two tables:

  records(section, key, json)   one row per bundle record, its JSON text as published
  state(...)                    one row: the release the copy is at, its line and its schema_version

  python3 keep-current.py init FULL.json.gz      load a monthly or weekly full you downloaded
  python3 keep-current.py update                 apply every delta published since the copy's release
  python3 keep-current.py status                 print the state
  python3 keep-current.py verify                 at the newest release: compare with the published records sha256

The same for a directory of Parquet tables (its state is in <dir>/keep-current.json):

  python3 keep-current.py parquet-init DIR       download the published Parquet set (the newest release);
                                                 --only scv,submitter downloads only those tables
  python3 keep-current.py parquet-update DIR     build each new delta's tables with gkm-bundle-parquet and merge them
  python3 keep-current.py parquet-check DIR      at the newest release: row counts against the published manifest

Options: --db (default clinvar-gkm.duckdb), --cache (default gkm-cache/, where deltas are downloaded).
Every path comes from the root index.json and the line's index.json; every download is checked by its sha256.
Needs Python 3.9 or later and the duckdb package; parquet-update also runs gkm-bundle-parquet 2.0.0.
https://clinvar-gkm.org/data-access/keep-current/
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
from collections import deque
from concurrent.futures import ProcessPoolExecutor

import duckdb

BASE = "https://data.clinvar-gkm.org"
SECTION = re.compile(rb'^  "([A-Za-z0-9_]+)": \{\n$')
SCHEMA_VERSION = re.compile(rb'^  "schema_version": ("[^"]*"),?\n$')
BATCH = 200_000


class Refused(Exception):
    pass


# --- downloads ---------------------------------------------------------------------------------------------------

def fetch(path, dest=None):
    """GET BASE/path (retrying), returning the bytes or writing them to dest."""
    for attempt in range(5):
        try:
            req = urllib.request.Request(f"{BASE}/{path.lstrip('/')}",
                                         headers={"User-Agent": "clinvar-gkm-keep-current/1"})
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


def line_index(line):
    """The line's index.json, with the deltas and monthlies of archived years folded in."""
    index = fetch_json(f"{line}/index.json")
    for year in index.get("archives", {}).values():
        index["deltas"] += year.get("deltas", [])
        index["datasets"]["monthly"] += year.get("monthly", [])
    return index


def current_line():
    root = fetch_json("index.json")
    return root, root["current"]


# --- the bundle layout -------------------------------------------------------------------------------------------

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


def copy_rows(con, table, rows):
    """Bulk-load (section, key, json) rows through a tab-separated file (record text holds no raw tab)."""
    with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, encoding="utf-8") as f:
        for row in rows:
            f.write("\t".join(row) + "\n")
    try:
        con.execute(f"COPY {table} FROM '{f.name}' "
                    " (DELIMITER '\t', QUOTE '', ESCAPE '', HEADER false, AUTO_DETECT false, MAX_LINE_SIZE 16777216)")
    finally:
        os.unlink(f.name)


def load_bundle(con, table, path):
    """Load every record of a bundle into `table`; return the bundle's schema_version."""
    schema_version, batch = None, []
    for event in read_bundle(path):
        if event[0] == "schema_version":
            schema_version = event[1]
            continue
        batch.append(event[1:])
        if len(batch) == BATCH:
            copy_rows(con, table, batch)
            batch = []
    copy_rows(con, table, batch)
    return schema_version


# --- the copy ----------------------------------------------------------------------------------------------------

def connect(db):
    con = duckdb.connect(db)
    con.execute("CREATE TABLE IF NOT EXISTS records (section VARCHAR, key VARCHAR, json VARCHAR)")
    con.execute("CREATE TABLE IF NOT EXISTS state (last_release VARCHAR, line VARCHAR, schema_version VARCHAR,"
                " base VARCHAR, updated_at VARCHAR)")
    return con


def get_state(con):
    row = con.execute("SELECT last_release, line, schema_version, base FROM state").fetchone()
    if row is None:
        raise Refused("the copy has no state: run init first")
    return dict(zip(("last_release", "line", "schema_version", "base"), row))


def set_state(con, last_release, line, schema_version, base):
    con.execute("DELETE FROM state")
    con.execute("INSERT INTO state VALUES (?, ?, ?, ?, ?)",
                [last_release, line, schema_version, base, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())])


def cmd_init(con, args):
    """Load a full bundle. Its release comes from index.json (the bundle holds none), found by its sha256."""
    if con.execute("SELECT count(*) FROM records").fetchone()[0]:
        raise Refused(f"{args.db} already holds records: init a new database file")
    line = args.line or current_line()[1]
    index = line_index(line)
    sha = sha256_file(args.full)
    entry = next((m for m in index["datasets"]["monthly"] + index["datasets"]["weekly"] if m["sha256"] == sha), None)
    if entry is None:
        raise Refused(f"{args.full} (sha256 {sha[:12]}...) is not a monthly or weekly full listed in {line}/index.json")
    release = entry.get("source_release") or entry["release"]  # a monthly is at its source_release
    con.execute("BEGIN")
    try:
        schema_version = load_bundle(con, "records", args.full)
        if schema_version != index["schema_version"]:
            raise Refused(f"the bundle is schema {schema_version}, line {line} is {index['schema_version']}")
        set_state(con, release, line, schema_version, entry["name"])
        con.execute("COMMIT")
    except BaseException:
        con.execute("ROLLBACK")
        raise
    print(f"loaded {entry['name']}: at release {release}, line {line}, schema {schema_version}")


def plan(state):
    """The deltas to apply, oldest first, after checking the line and the chain."""
    root, current = current_line()
    if state["line"] != current:
        old = next((v for v in root["versions"].values() if v["line"] == state["line"]), {})
        raise Refused(f"the copy is on {state['line']} ({old.get('status', 'unknown')}, superseded by "
                      f"{old.get('superseded_by')}); the current line is {current}. Its deltas don't apply to this "
                      f"copy: start a new one on {current}")
    index = line_index(current)
    chain = sorted((d for d in index["deltas"] if d["release"] > state["last_release"]), key=lambda d: d["release"])
    previous = state["last_release"]
    for d in chain:
        d["manifest_json"] = manifest = fetch_json(d["manifest"])
        if manifest["baseline_release"] != previous:
            raise Refused(f"broken chain: the {manifest['release']} delta builds on {manifest['baseline_release']}, "
                          f"the copy would be at {previous}")
        if manifest.get("schema_version") != state["schema_version"]:
            raise Refused(f"the {manifest['release']} delta is schema {manifest.get('schema_version')}, the copy is "
                          f"{state['schema_version']}: start a new copy on {current}")
        if manifest["sha256"] != d["bundle"]["sha256"]:
            raise Refused(f"the {manifest['release']} manifest and index.json disagree on the bundle's sha256")
        previous = manifest["release"]
    return chain


def apply_delta(con, d, path, state):
    """One transaction: delete the manifest's deleted keys and every key the delta holds, insert its records."""
    manifest = d["manifest_json"]
    con.execute("BEGIN")
    con.execute("CREATE OR REPLACE TEMP TABLE delta (section VARCHAR, key VARCHAR, json VARCHAR)")
    con.execute("CREATE OR REPLACE TEMP TABLE gone (section VARCHAR, key VARCHAR, json VARCHAR)")
    schema_version = load_bundle(con, "delta", path)
    if schema_version != state["schema_version"]:
        raise Refused(f"the {manifest['release']} delta bundle is schema {schema_version}")
    copy_rows(con, "gone", ((s, k, "") for s, info in manifest["sections"].items() for k in info["deleted"]))
    con.execute("INSERT INTO gone SELECT section, key, '' FROM delta")
    con.execute("DELETE FROM records USING gone WHERE records.section = gone.section AND records.key = gone.key")
    con.execute("INSERT INTO records SELECT * FROM delta")
    set_state(con, manifest["release"], state["line"], state["schema_version"], state["base"])
    con.execute("COMMIT")
    state["last_release"] = manifest["release"]


def cmd_update(con, args):
    state = get_state(con)
    chain = plan(state)
    if not chain:
        print(f"up to date at {state['last_release']}")
        return
    os.makedirs(args.cache, exist_ok=True)
    for d in chain:
        path = os.path.join(args.cache, os.path.basename(d["bundle"]["path"]))
        if not (os.path.exists(path) and sha256_file(path) == d["bundle"]["sha256"]):
            fetch(d["bundle"]["path"], path)
            if sha256_file(path) != d["bundle"]["sha256"]:
                raise Refused(f"{path}: sha256 differs from index.json")
        try:
            apply_delta(con, d, path, state)
        except BaseException:
            con.execute("ROLLBACK")
            raise
        print(f"applied {d['release']}: {d['manifest_json']['counts']}")
    print(f"at release {state['last_release']}")


def cmd_status(con, args):
    state = get_state(con)
    n = con.execute("SELECT count(*) FROM records").fetchone()[0]
    print(json.dumps({**state, "records": n}, indent=2))


# --- records sha256 (the definition in gkm-bundle-parquet's docs/round-trip.md) ---------------------------------

def _number(x):
    if isinstance(x, int) and abs(x) <= 2 ** 53:
        return str(x)
    x = float(x)
    if x.is_integer() and abs(x) <= 2 ** 53:
        return str(int(x))
    if x == 0:
        return "0"
    sign, (_, digits, exp) = ("-" if x < 0 else ""), __import__("decimal").Decimal(repr(abs(x))).normalize().as_tuple()
    s = "".join(map(str, digits))
    k, n = len(s), len(s) + exp
    if k <= n <= 21:
        return sign + s + "0" * (n - k)
    if 0 < n <= 21:
        return sign + s[:n] + "." + s[n:]
    if -6 < n <= 0:
        return sign + "0." + "0" * -n + s
    e = n - 1
    return sign + s[0] + ("." + s[1:] if k > 1 else "") + "e" + ("+" if e >= 0 else "-") + str(abs(e))


def canonical(v):
    """RFC 8785 (JCS) with every array sorted."""
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, bool) or v is None:
        return json.dumps(v)
    if isinstance(v, dict):
        names = sorted(v, key=lambda k: k.encode("utf-16-be", "surrogatepass"))
        return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + canonical(v[k]) for k in names) + "}"
    if isinstance(v, list):
        return "[" + ",".join(sorted(canonical(e) for e in v)) + "]"
    return _number(v)


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _lines(rows):
    return [(json.dumps(k, ensure_ascii=False), sha(canonical(json.loads(j)))) for k, j in rows]


def records_sha256(con, schema_version):
    """The copy's records sha256: per section, the sorted lines `"<key>" TAB <record sha256>`; then the sorted
    lines `"<section>" TAB <section sha256>` and `$ TAB <root sha256>`. Records are hashed on every CPU."""
    sections = [s for (s,) in con.execute("SELECT DISTINCT section FROM records ORDER BY section").fetchall()]
    lines = []
    with ProcessPoolExecutor() as pool:
        for s in sections:
            con.execute("CREATE OR REPLACE TEMP TABLE ks (key VARCHAR, sha VARCHAR)")
            cur = con.cursor().execute("SELECT key, json FROM records WHERE section = ?", [s])
            pending, done = deque(), []
            for batch in iter(lambda: cur.fetchmany(10_000), []):
                pending.append(pool.submit(_lines, batch))
                if len(pending) > 4 * (os.cpu_count() or 1):  # bounded: a section never sits in memory whole
                    done += pending.popleft().result()
                if len(done) >= BATCH:
                    copy_rows(con, "ks", done)
                    done = []
            while pending:
                done += pending.popleft().result()
            copy_rows(con, "ks", done)
            h = hashlib.sha256()
            cur = con.execute("SELECT key || chr(9) || sha AS line FROM ks ORDER BY line")
            while rows := cur.fetchmany(BATCH):
                h.update("".join(line + "\n" for (line,) in rows).encode("utf-8"))
            lines.append(f"{json.dumps(s)}\t{h.hexdigest()}\n")
    root = sha(canonical({"schema_version": schema_version, **{s: {} for s in sections}}))
    lines.append(f"$\t{root}\n")
    return hashlib.sha256("".join(sorted(lines)).encode("utf-8")).hexdigest()


def cmd_verify(con, args):
    state = get_state(con)
    pq = fetch_json(f"{state['line']}/parquet/manifest.json")
    if pq["source_release"] != state["last_release"] or pq["schema_version"] != state["schema_version"]:
        raise Refused(f"the published Parquet is release {pq['source_release']}; the copy is at "
                      f"{state['last_release']}. Only a copy at the newest release can be checked")
    mine = records_sha256(con, state["schema_version"])
    ok = mine == pq["records_sha256"]
    print(f"{'match' if ok else 'DIFFERENT'}: copy {mine}, published Parquet {pq['records_sha256']}")
    if not ok:
        sys.exit(1)


# --- Parquet tables ----------------------------------------------------------------------------------------------

TOOL = "uvx gkm-bundle-parquet@2.0.0"
SCHEMA = "https://w3id.org/clingen/schema/clinvar-gkm/{}/clinvar-gkm-bundle.schema.json"


def parquet_state(tables):
    try:
        with open(os.path.join(tables, "keep-current.json")) as f:
            return json.load(f)
    except FileNotFoundError:
        raise Refused(f"{tables} has no keep-current.json: run parquet-init first") from None


def cmd_parquet_init(con, args):
    """Download the published Parquet set (the newest release) and record its release."""
    line = current_line()[1]
    manifest = fetch_json(f"{line}/parquet/manifest.json")
    wanted = args.only.split(",") if args.only else list(manifest["tables"])
    unknown = set(wanted) - set(manifest["tables"])
    if unknown:
        raise Refused(f"no published table {sorted(unknown)}")
    os.makedirs(args.tables)
    for name in wanted:
        t = manifest["tables"][name]
        path = os.path.join(args.tables, t["file"])
        fetch(f"{line}/parquet/{t['file']}", path)
        if sha256_file(path) != t["sha256"]:
            raise Refused(f"{path}: sha256 differs from the published manifest")
    state = {"last_release": manifest["source_release"], "line": line, "schema_version": manifest["schema_version"],
             "table_spec_sha256": manifest["table_spec"]["sha256"], "builder": manifest["builder"],
             "base": f"published Parquet {manifest['source_release']}"}
    with open(os.path.join(args.tables, "keep-current.json"), "w") as f:
        json.dump(state, f, indent=2)
    print(f"downloaded {len(wanted)} tables at release {state['last_release']}")


def merge_tables(base, built, manifest, out):
    """Each table of `base`, less the rows whose id the manifest deletes or the delta holds, plus the delta's rows."""
    db = duckdb.connect()
    os.makedirs(out)
    for file in sorted(f for f in os.listdir(base) if f.endswith(".parquet")):
        section = file.removesuffix(".parquet")
        deleted = manifest["sections"].get(section, {}).get("deleted", [])
        db.execute("CREATE OR REPLACE TEMP TABLE gone AS SELECT unnest(?::VARCHAR[]) AS id", [deleted])
        new = os.path.join(built, file)
        if os.path.exists(new):
            db.execute(f"INSERT INTO gone SELECT id FROM read_parquet('{new}')")
            delta_rows = f"UNION ALL BY NAME SELECT * FROM read_parquet('{new}')"
        else:
            delta_rows = ""
        db.execute(f"""COPY (SELECT * FROM read_parquet('{os.path.join(base, file)}')
                             WHERE id NOT IN (SELECT id FROM gone) {delta_rows})
                       TO '{os.path.join(out, file)}' (FORMAT parquet, COMPRESSION zstd)""")
    db.close()


def cmd_parquet_check(con, args):
    """At the newest release: each table's row count against the published manifest, and no id twice."""
    state = parquet_state(args.tables)
    manifest = fetch_json(f"{state['line']}/parquet/manifest.json")
    if manifest["source_release"] != state["last_release"]:
        raise Refused(f"the published Parquet is release {manifest['source_release']}; the tables are at "
                      f"{state['last_release']}")
    db, bad = duckdb.connect(), 0
    names = [n for n, t in manifest["tables"].items() if os.path.exists(os.path.join(args.tables, t["file"]))]
    for name in names:
        t = manifest["tables"][name]
        rows, ids = db.execute(f"SELECT count(*), count(DISTINCT id) FROM read_parquet("
                               f"'{os.path.join(args.tables, t['file'])}')").fetchone()
        if rows != t["rows"] or ids != rows:
            bad += 1
            print(f"{name}: {rows} rows, {ids} ids; published {t['rows']} rows")
    print(f"{len(names) - bad} of {len(names)} tables match the published row counts")
    sys.exit(1 if bad else 0)


def cmd_parquet_update(con, args):
    import shutil
    import subprocess
    tables = args.tables.rstrip("/")
    state = parquet_state(tables)
    chain = plan(state)
    if not chain:
        print(f"up to date at {state['last_release']}")
        return
    os.makedirs(args.cache, exist_ok=True)
    for d in chain:
        path = os.path.join(args.cache, os.path.basename(d["bundle"]["path"]))
        if not (os.path.exists(path) and sha256_file(path) == d["bundle"]["sha256"]):
            fetch(d["bundle"]["path"], path)
            if sha256_file(path) != d["bundle"]["sha256"]:
                raise Refused(f"{path}: sha256 differs from index.json")
        built = os.path.join(args.cache, f"parquet-{d['release']}")
        if not os.path.exists(os.path.join(built, "manifest.json")):
            shutil.rmtree(built, ignore_errors=True)
            subprocess.run([*args.tool.split(), "build", "--full", path, "--sha256", d["bundle"]["sha256"],
                            "--bundle-schema", SCHEMA.format(state["schema_version"]),
                            "--version-property", "schema_version", "--out", built], check=True)
        with open(os.path.join(built, "manifest.json")) as f:
            spec = json.load(f)["table_spec"]["sha256"]
        if spec != state["table_spec_sha256"]:
            raise Refused(f"the delta's tables have table spec {spec[:12]}..., yours "
                          f"{state['table_spec_sha256'][:12]}...: build them with {state['builder']}")
        shutil.rmtree(tables + ".next", ignore_errors=True)
        merge_tables(tables, built, d["manifest_json"], tables + ".next")
        state["last_release"] = d["release"]
        with open(os.path.join(tables + ".next", "keep-current.json"), "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tables, tables + ".prev")  # swap whole directories, so the tables and their state move together
        os.replace(tables + ".next", tables)
        shutil.rmtree(tables + ".prev")
        print(f"applied {d['release']} to {tables}/")
    print(f"at release {state['last_release']}")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--db", default="clinvar-gkm.duckdb")
    p.add_argument("--cache", default="gkm-cache")
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("full")
    i.add_argument("--line", help="a line folder such as v1/1.2 (default: the current line)")
    for name in ("update", "status", "verify"):
        sub.add_parser(name)
    for name in ("parquet-init", "parquet-update", "parquet-check"):
        t = sub.add_parser(name)
        t.add_argument("tables", help="the directory of Parquet tables")
        t.add_argument("--tool", default=TOOL, help=f"how to run gkm-bundle-parquet (default: {TOOL})")
        t.add_argument("--only", help="parquet-init: a comma-separated subset of tables (default: all 20)")
    args = p.parse_args()
    con = None if args.cmd.startswith("parquet") else connect(args.db)
    try:
        {"init": cmd_init, "update": cmd_update, "status": cmd_status, "verify": cmd_verify,
         "parquet-init": cmd_parquet_init, "parquet-update": cmd_parquet_update,
         "parquet-check": cmd_parquet_check}[args.cmd](con, args)
    except Refused as e:
        sys.exit(f"refused: {e}")


if __name__ == "__main__":
    main()
