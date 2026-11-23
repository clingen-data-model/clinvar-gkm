#!/usr/bin/env python3
"""Rebuild the full ClinVar-GKM bundle of one weekly release from a monthly and the weekly deltas after it.

Weekly full bundles are kept only for the current month. For any other week W, this script:

1. picks the newest official monthly whose source_release <= W (never the 00-latest copy), and every delta whose
   release is later than that source_release and <= W, in release order, from the line's index.json;
2. checks the chain: the first delta's baseline_release is the monthly's source_release, and each later delta's
   baseline_release is the previous delta's release (a broken chain stops the run);
3. downloads each bundle and manifest (with retries), or reuses a local copy in --dir, and checks every bundle's
   sha256 against index.json;
4. reads the deltas into an overlay, section by section: for each delta in order, the keys its manifest lists under
   sections.<s>.deleted are removed, then its records are upserted. Records are kept as their published text, never
   parsed, so a month of deltas (a few million records) fits in a few GB;
5. streams the monthly once, line by line: a record the overlay holds is written from the overlay, a deleted one is
   dropped, any other is copied unchanged; after each section come the section's new keys. The result is written,
   gzipped, in the published layout with a .sha256 sidecar.

It reads and writes only the layout assemble-gkm-dicts.py writes: `{`, a `  "schema_version": "..."` line, then each
section opened by `  "<section>": {`, one `    "<key>": {...}` record per line, and closed by `  }`. Any other line
stops the run. It uses only the Python standard library (3.9 or later).

Usage:
  python3 replay-bundle.py --release 2026-11-15                 # current line
  python3 replay-bundle.py --line v1/1.1 --release 2026-10-11    # a frozen line
  python3 replay-bundle.py --release 2026-11-15 --plan          # list what it would download, and stop
"""
import argparse
import gzip
import hashlib
import http.client
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

BASE_URL = "https://data.clinvar-gkm.org"
USER_AGENT = "clinvar-gkm-replay-bundle/1"
CHUNK = 1 << 20
WRITE_BUFFER = 8 << 20

# The order assemble-gkm-dicts.py writes the sections in. Used only to place a section the monthly lacks but a delta
# adds; a section not listed here goes last.
SECTION_ORDER = [
    "sequenceReference", "location", "allele", "copyNumberCount", "copyNumberChange", "gene", "variation",
    "condition", "conditionSet", "therapy", "therapyGroup", "submitter", "propositionPathogenicity",
    "propositionOncogenicity", "propositionSomaticClinicalImpact", "propositionClinvarCustom", "evidenceLine", "scv",
    "vcv", "rcv",
]

SECTION = re.compile(rb'^  "([A-Za-z0-9_]+)": \{\n$')
SCHEMA_VERSION = re.compile(rb'^  "schema_version": ("(?:[^"\\]|\\.)*"),?\n$')


class ReplayError(Exception):
    pass


def log(msg):
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# The bundle layout
# ---------------------------------------------------------------------------
def record_key(body):
    """The decoded key of a record line's body (`"<key>": {...}`)."""
    end = body.find(b'"', 1)
    if end > 0 and b"\\" not in body[1:end]:
        key = body[1:end].decode("utf-8")
    else:  # an escape in the key: let the JSON decoder find where it ends
        key, end = json.JSONDecoder().raw_decode(body.decode("utf-8"))
        if not isinstance(key, str):
            raise ReplayError(f"a record key is not a string: {body[:120]!r}")
        end -= 1
    if body[end + 1:end + 3] != b": ":
        raise ReplayError(f"not a record line: {body[:120]!r}")
    return key


def read_bundle(path):
    """Yield ("schema_version", value), ("section", name), ("record", key, body) and ("end", name) from a bundle.

    `body` is the record line without its indent, trailing comma or newline: `"<key>": {...}`."""
    section, line_no, closed, seen_sv = None, 0, False, False
    with gzip.open(path, "rb") as f:
        for line in f:
            line_no += 1
            if closed:
                raise ReplayError(f"{path}: line {line_no}: text after the closing brace: {line[:120]!r}")
            if line.startswith(b'    "'):
                if section is None:
                    raise ReplayError(f"{path}: line {line_no}: a record outside any section: {line[:120]!r}")
                body = line[4:].rstrip(b"\n")
                if body.endswith(b","):
                    body = body[:-1]
                yield "record", record_key(body), body
                continue
            if line_no == 1:
                if line != b"{\n":
                    raise ReplayError(f"{path}: line 1 is not a lone opening brace: {line[:120]!r}")
                continue
            if section is not None and line in (b"  }\n", b"  },\n"):
                yield "end", section
                section = None
                continue
            m = SECTION.match(line)
            if m and section is None:
                section = m.group(1).decode()
                yield "section", section
                continue
            m = SCHEMA_VERSION.match(line)
            if m and section is None and not seen_sv:
                seen_sv = True
                yield "schema_version", json.loads(m.group(1))
                continue
            if line.rstrip(b"\n") == b"}" and section is None:
                closed = True
                continue
            raise ReplayError(f"{path}: line {line_no}: unexpected line (not the published bundle layout): "
                              f"{line[:200]!r}")
    if section is not None or not closed:
        raise ReplayError(f"{path}: the bundle ends before its closing brace")


class HashingWriter:
    """A binary file that also computes the sha256 of what is written to it."""

    def __init__(self, f):
        self.f, self.sha = f, hashlib.sha256()

    def write(self, b):
        self.sha.update(b)
        return self.f.write(b)

    def flush(self):
        self.f.flush()


class BundleWriter:
    """Write the published layout: sections opened lazily, so a section with no records is omitted."""

    def __init__(self, path, schema_version):
        self.raw = open(path, "wb")
        self.hashed = HashingWriter(self.raw)
        # mtime=0 and no file name in the gzip header: the same records give the same bytes.
        self.gz = gzip.GzipFile(filename="", mode="wb", fileobj=self.hashed, compresslevel=3, mtime=0)
        self.buf = bytearray(b"{\n" + b'  "schema_version": ' + json.dumps(schema_version).encode())
        self.section, self.first, self.counts = None, True, {}

    def start(self, section):
        self.section, self.first = section, True

    def record(self, body):
        if self.first:
            self.buf += b',\n  "' + self.section.encode() + b'": {\n'
            self.counts[self.section] = 0
            self.first = False
        else:
            self.buf += b",\n"
        self.buf += b"    " + body
        self.counts[self.section] += 1
        if len(self.buf) >= WRITE_BUFFER:
            self.gz.write(self.buf)
            self.buf = bytearray()

    def end(self):
        if not self.first:
            self.buf += b"\n  }"
        self.section = None

    def close(self):
        self.buf += b"\n}\n"
        self.gz.write(self.buf)
        self.gz.close()
        self.raw.close()
        return self.hashed.sha.hexdigest()


# ---------------------------------------------------------------------------
# The replay
# ---------------------------------------------------------------------------
def build_overlay(deltas):
    """Apply each (manifest, bundle path) in order to an overlay {section: {key: body or None}}; None = deleted.

    Returns (overlay, schema_versions, stats) where stats counts the records and deletes read."""
    overlay, versions, stats = {}, set(), {"records": 0, "deletes": 0}
    for manifest, path in deltas:
        for section, info in (manifest.get("sections") or {}).items():
            target = overlay.setdefault(section, {})
            for key in info.get("deleted") or []:
                target[key] = None
                stats["deletes"] += 1
        target = None
        for event in read_bundle(path):
            if event[0] == "record":
                target[event[1]] = event[2]
                stats["records"] += 1
            elif event[0] == "section":
                target = overlay.setdefault(event[1], {})
            elif event[0] == "schema_version":
                versions.add(event[1])
        log(f"  read {os.path.basename(path)}")
    return overlay, versions, stats


def section_rank(section):
    return SECTION_ORDER.index(section) if section in SECTION_ORDER else len(SECTION_ORDER)


def replay(monthly, deltas, out):
    """Write the monthly with the deltas applied to `out`; return (sha256, report).

    monthly: path of the monthly bundle; deltas: [(manifest dict, delta bundle path), ...] in release order."""
    overlay, versions, stats = build_overlay(deltas)
    log(f"overlay: {stats['records']:,} records and {stats['deletes']:,} deletes from {len(deltas)} delta(s)")
    report = {}
    writer = None
    pending = sorted((s for s in overlay if any(v is not None for v in overlay[s].values())), key=section_rank)
    done = set()

    def emit_new(section):
        """Write the overlay's records for `section` that the monthly didn't hold."""
        seen = matched.get(section, set())
        n = 0
        for key, body in overlay.get(section, {}).items():
            if body is not None and key not in seen:
                writer.record(body)
                n += 1
        return n

    def emit_overlay_only(section):
        writer.start(section)
        n = emit_new(section)
        writer.end()
        report[section] = {"monthly": 0, "replaced": 0, "deleted": 0, "added": n, "written": n}
        done.add(section)

    matched = {}
    current, row, ov, seen = None, None, {}, set()
    tmp = out + ".part"
    try:
        for event in read_bundle(monthly):
            kind = event[0]
            if kind == "record":
                row["monthly"] += 1
                if ov:
                    key = event[1]
                    if key in ov:
                        seen.add(key)
                        body = ov[key]
                        if body is None:
                            row["deleted"] += 1
                            continue
                        row["replaced"] += 1
                        writer.record(body)
                        continue
                writer.record(event[2])
            elif kind == "section":
                current = event[1]
                if current in done:
                    raise ReplayError(f"{monthly}: section {current} appears twice")
                for s in [s for s in pending if s not in done and section_rank(s) < section_rank(current)]:
                    emit_overlay_only(s)
                ov = overlay.get(current) or {}
                seen = matched.setdefault(current, set())
                row = report[current] = {"monthly": 0, "replaced": 0, "deleted": 0, "added": 0, "written": 0}
                writer.start(current)
            elif kind == "end":
                row["added"] = emit_new(current)
                writer.end()
                done.add(current)
                log(f"  {current:34s} {row['monthly']:>11,d} in the monthly, {row['replaced']:,} replaced, "
                    f"{row['deleted']:,} deleted, {row['added']:,} added")
            else:  # schema_version, always before the first section
                versions.add(event[1])
                if len(versions) != 1:
                    raise ReplayError(f"the bundles hold different schema_version values: {sorted(versions)}; "
                                      "replay only bundles of one line")
                writer = BundleWriter(tmp, event[1])
        if writer is None:
            raise ReplayError(f"{monthly}: no schema_version line")
        for s in pending:
            if s not in done:
                emit_overlay_only(s)
        sha = writer.close()
    except BaseException:
        if writer is not None:
            writer.raw.close()
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    for section, row in report.items():
        row["written"] = row["monthly"] - row["deleted"] + row["added"]
    os.replace(tmp, out)
    with open(out + ".sha256", "w") as f:
        f.write(f"{sha}  {os.path.basename(out)}\n")
    return sha, report


# ---------------------------------------------------------------------------
# The line's index and downloads
# ---------------------------------------------------------------------------
def retrying(what, attempts, fn):
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except urllib.error.HTTPError as e:
            if e.code < 500 and e.code not in (408, 429):
                raise ReplayError(f"{what}: HTTP {e.code}") from None
            err = f"HTTP {e.code}"
        except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
            err = str(e) or type(e).__name__
        if attempt == attempts:
            raise ReplayError(f"{what}: failed after {attempts} attempts: {err}")
        wait = min(60, 2 ** attempt)
        log(f"  {what}: {err}; retrying in {wait} s")
        time.sleep(wait)


def fetch_json(url, attempts):
    def get():
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    return retrying(url, attempts, get)


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url, dest, sha256, attempts):
    """Download url to dest, resuming a partial download, and check its sha256. A local dest that matches is kept."""
    name = os.path.basename(dest)
    if os.path.exists(dest):
        if file_sha256(dest) == sha256:
            log(f"  {name}: local copy, sha256 matches")
            return dest
        raise ReplayError(f"{dest} exists but its sha256 is not {sha256}; move it away and run again")
    part = dest + ".part"

    def get():
        have = os.path.getsize(part) if os.path.exists(part) else 0
        headers = {"User-Agent": USER_AGENT}
        if have:
            headers["Range"] = f"bytes={have}-"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as r:
            mode = "ab" if have and r.status == 206 else "wb"
            with open(part, mode) as f:
                for chunk in iter(lambda: r.read(CHUNK), b""):
                    f.write(chunk)

    log(f"  {name}: downloading")
    retrying(url, attempts, get)
    got = file_sha256(part)
    if got != sha256:
        os.remove(part)
        raise ReplayError(f"{url}: sha256 {got}, index.json says {sha256}; run again to download it afresh")
    os.replace(part, dest)
    log(f"  {name}: sha256 matches")
    return dest


def line_index(base_url, line, attempts):
    root = fetch_json(f"{base_url}/index.json", attempts)
    want = None if line is None else (line if line.startswith("v") else f"v1/{line}")
    for entry in root["versions"].values():
        if (want is None and entry.get("status") == "current") or entry.get("line") == want:
            return entry["line"], fetch_json(f"{base_url}/{entry['index'].lstrip('/')}", attempts)
    lines = ", ".join(v.get("line", "?") for v in root["versions"].values())
    raise ReplayError(f"no line {line} in {base_url}/index.json (lines: {lines})")


def plan(index, release):
    """(monthly entry, [delta entries]) to rebuild `release`, by the rule in weekly-deltas.md."""
    monthlies = list(index["datasets"]["monthly"])
    deltas = list(index["deltas"])
    for year in (index.get("archives") or {}).values():
        monthlies += year.get("monthly", [])
        deltas += year.get("deltas", [])
    official = [m for m in monthlies if not m.get("latest") and m.get("source_release")
                and m["source_release"] <= release]
    if not official:
        raise ReplayError(f"no monthly of this line has a source_release on or before {release}")
    base = max(official, key=lambda m: m["source_release"])
    chain = sorted((d for d in deltas if base["source_release"] < d["release"] <= release),
                   key=lambda d: d["release"])
    if release != base["source_release"] and (not chain or chain[-1]["release"] != release):
        raise ReplayError(f"{release} is not a release of this line; its releases are in index.json")
    return base, chain


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--release", help="the weekly release to rebuild, YYYY-MM-DD (default: the line's newest)")
    ap.add_argument("--line", help="the release line, e.g. v1/1.1 (default: the current line)")
    ap.add_argument("--dir", default=".", help="where bundles are downloaded, or already are (default: .)")
    ap.add_argument("--out", help="the bundle to write (default: <dir>/clinvar-gkm_<YYYY-MMDD>.replayed.json.gz)")
    ap.add_argument("--plan", action="store_true", help="list the monthly and deltas it would use, and stop")
    ap.add_argument("--base-url", default=BASE_URL, help=argparse.SUPPRESS)
    ap.add_argument("--retries", type=int, default=5, help="download attempts per file (default: 5)")
    a = ap.parse_args(argv)

    try:
        line, index = line_index(a.base_url.rstrip("/"), a.line, a.retries)
        release = a.release or index["latest_release"]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", release):
            raise ReplayError(f"--release {release}: give a date, YYYY-MM-DD")
        base, chain = plan(index, release)
        log(f"line {line}, release {release}")
        log(f"  monthly {base['name']} (source_release {base['source_release']}, {base['size']:,} bytes)")
        for d in chain:
            log(f"  delta   {os.path.basename(d['bundle']['path'])} ({d['bundle']['size']:,} bytes)")
        if release == base["source_release"]:
            log(f"{base['name']} is already the full bundle of {release}: use it as it is")
            return 0
        if a.plan:
            return 0

        os.makedirs(a.dir, exist_ok=True)
        url = a.base_url.rstrip("/")
        prev, deltas = base["source_release"], []
        for d in chain:
            manifest = fetch_json(f"{url}/{d['manifest']}", a.retries)
            if manifest.get("baseline_release") != prev:
                raise ReplayError(f"broken chain at {d['release']}: its baseline_release is "
                                  f"{manifest.get('baseline_release')}, expected {prev}; stopping")
            if manifest.get("release") != d["release"] or manifest.get("sha256", d["bundle"]["sha256"]) \
                    != d["bundle"]["sha256"]:
                raise ReplayError(f"the manifest of {d['release']} doesn't match index.json")
            path = os.path.join(a.dir, os.path.basename(d["bundle"]["path"]))
            deltas.append((manifest, download(f"{url}/{d['bundle']['path']}", path, d["bundle"]["sha256"],
                                              a.retries)))
            prev = d["release"]
        monthly = download(f"{url}/{base['path']}", os.path.join(a.dir, os.path.basename(base["path"])),
                           base["sha256"], a.retries)

        out = a.out or os.path.join(a.dir, f"clinvar-gkm_{release[:7]}{release[8:]}.replayed.json.gz")
        t0 = time.time()
        sha, report = replay(monthly, deltas, out)
        total = sum(r["written"] for r in report.values())
        log(f"wrote {out}: {len(report)} sections, {total:,} records, sha256 {sha} ({time.time() - t0:,.0f} s)")
        print(out)
        return 0
    except ReplayError as e:
        log(f"error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
