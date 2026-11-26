#!/usr/bin/env python3
"""Validate EVERY record of a real bundle (.json.gz) with jsonschema-rs. Run it through validate-bundle.sh --engine rs.

The same check as validate-bundle.py (the GA4GH gkm-toolkit engine), about 30 times faster, so a full bundle takes
minutes instead of hours:

- the same bundle schema, clinvar-gkm-bundle.schema.json, as JSON Schema Draft 2020-12 with formats not asserted
  (python-jsonschema's default, which the toolkit uses);
- the same registry: every schema in a json/ directory (or a profile directory inside one) under schema/, by its
  $id (as validate-schema-conformance.py's load_registry; jsonschema-rs resolves the root-relative $refs against the
  $id itself);
- the same document shape: each chunk of records is validated as {"schema_version": <bundle's value>, <section>:
  {key: record, ...}}, verbatim, and a failing chunk is re-validated record by record to name the failing records
  (against the bundle schema narrowed to that section, which gives the same result: see validator_for);
- the same checks: schema_version equals the schema const, no section is empty, every record passes.

It reads only the layout assemble-gkm-dicts.py writes: `{`, a `  "schema_version": "..."` line, then each section
opened by `  "<section>": {`, one `    "<key>": {...}` record per line, and closed by `  }`. Any other line stops the
run, and a line that does not hold exactly one record fails it, so a different layout can never skip a record. Use
--engine toolkit (validate-bundle.py) for any other JSON. The main process only splits lines; workers parse (orjson)
and validate.

Usage: python validate-bundle-rs.py <bundle.json.gz> <repo_root> [--workers N] [--chunk N] [--max-print N]
"""
import argparse
import collections
import importlib.metadata
import json
import multiprocessing as mp
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import jsonschema_rs
import orjson

BUNDLE_SCHEMA = "schema/clinvar-gkm/clinvar-gkm-bundle.schema.json"
SECTION = re.compile(rb'^  "([A-Za-z]+)": \{\n$')
SCHEMA_VERSION = re.compile(rb'^  "schema_version": ("(?:[^"\\]|\\.)*"),?\n$')
G = {}


class LayoutError(Exception):
    pass


def load_resources(schema_root):
    """(id, schema) for every schema in a json/ directory, or a profile directory inside one, under schema_root,
    following links (load_registry's walk)."""
    resources, seen = {}, set()
    for dirpath, dirnames, filenames in os.walk(schema_root, followlinks=True):
        real = os.path.realpath(dirpath)
        if real in seen:  # guard against link cycles (nested submodules)
            dirnames[:] = []
            continue
        seen.add(real)
        # a module's json/ directory, or a profile directory inside it (va-spec json/acmg-2015/, ...)
        if "json" not in (os.path.basename(dirpath), os.path.basename(os.path.dirname(dirpath))):
            continue
        for fn in filenames:
            if fn.endswith(".md"):
                continue
            try:
                doc = json.loads((Path(dirpath) / fn).read_text())
            except (json.JSONDecodeError, OSError):
                continue
            if doc.get("$id"):
                resources.setdefault(doc["$id"], doc)
    return list(resources.items())


def no_retrieval(uri):
    """Refuse to fetch a $ref over the network (jsonschema-rs would): every schema comes from the local registry."""
    raise LookupError(f"{uri} is not in the local schema registry (no network retrieval)")


def local_registry(schema_root):
    """The jsonschema-rs registry of every schema load_resources finds under schema_root, with no network retrieval."""
    return jsonschema_rs.Registry(load_resources(schema_root), retriever=no_retrieval)


def _init(repo_root):
    root = Path(repo_root)
    G.update(schema=json.loads((root / BUNDLE_SCHEMA).read_text()), registry=local_registry(root / "schema"),
             validators={})


def validator_for(section):
    """The bundle schema with `properties` narrowed to schema_version and this section, compiled on first use.

    Every document validated holds only those two keys, so the narrowed schema gives the same result as the whole one
    (the root's additionalProperties: false still rejects an unknown section, and allOf is kept). It is narrowed
    because jsonschema-rs takes minutes to compile the whole bundle schema at once, but about a minute for all the
    sections one by one."""
    v = G["validators"].get(section)
    if v is None:
        schema = dict(G["schema"])
        schema["properties"] = {k: s for k, s in schema["properties"].items() if k in ("schema_version", section)}
        v = G["validators"][section] = jsonschema_rs.Draft202012Validator(schema, registry=G["registry"],
                                                                           validate_formats=False)
    return v


def _check(task):
    """Validate one chunk of record lines; return (section, records, failures)."""
    sv, section, lines = task
    try:
        records = orjson.loads(b"{" + b"".join(lines).rstrip().rstrip(b",") + b"}")
    except orjson.JSONDecodeError as e:
        return section, len(lines), [f"{section}: a chunk of {len(lines)} record lines is not valid JSON: {e}"]
    if len(records) != len(lines):  # a repeated key, or a line holding more than one record
        return section, len(lines), [f"{section}: {len(lines)} record lines hold {len(records)} distinct records"]
    validator = validator_for(section)
    if validator.is_valid({"schema_version": sv, section: records}):
        return section, len(records), []
    bad = []
    for key, record in records.items():
        doc = {"schema_version": sv, section: {key: record}}
        error = next(validator.iter_errors(doc), None)
        if error is not None:
            path = "/".join(str(p) for p in error.instance_path) or "/"
            bad.append(f"{section}/{key}: Bundle does not match its JSON Schema at {path}: {error.message[:300]}")
    if not bad:
        bad.append(f"{section}: chunk-level failure not reproducible per record")
    return section, len(records), bad


def tasks(stream, state, chunk):
    """Yield (schema_version, section, [record line, ...]) chunks, enforcing the assembler's layout."""
    section, buf, line_no, closed = None, [], 0, False
    for line in stream:
        line_no += 1
        if closed:
            raise LayoutError(f"line {line_no}: text after the closing brace: {line[:120]!r}")
        if line.startswith(b'    "'):
            if section is None:
                raise LayoutError(f"line {line_no}: a record outside any section: {line[:120]!r}")
            buf.append(line)
            if len(buf) >= chunk:
                yield state["sv"], section, buf
                buf = []
            continue
        if line_no == 1:
            if line != b"{\n":
                raise LayoutError(f"line 1 is not a lone opening brace: {line[:120]!r}")
            continue
        if section is not None and line in (b"  }\n", b"  },\n"):
            if buf:
                yield state["sv"], section, buf
                buf = []
            section = None
            continue
        m = SECTION.match(line)
        if m and section is None:
            section = m.group(1).decode()
            state["seen"].append(section)
            continue
        m = SCHEMA_VERSION.match(line)
        if m and section is None and state["sv"] is None:
            state["sv"] = json.loads(m.group(1))
            continue
        if line.rstrip(b"\n") == b"}" and section is None:
            closed = True
            continue
        raise LayoutError(f"line {line_no}: unexpected line: {line[:200]!r}")
    if section is not None or not closed:
        raise LayoutError("the bundle ends before its closing brace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle")
    ap.add_argument("repo_root")
    ap.add_argument("--workers", type=int, default=max(1, mp.cpu_count() - 1))
    ap.add_argument("--chunk", type=int, default=2000)
    ap.add_argument("--max-print", type=int, default=20)
    a = ap.parse_args()

    if not Path(a.bundle).is_file():
        sys.exit(f"ERROR: {a.bundle} is not a file")
    const = json.loads((Path(a.repo_root) / BUNDLE_SCHEMA).read_text())["properties"]["schema_version"].get("const")
    t0 = time.time()
    counts, failures, nfail = {}, [], 0
    state = {"sv": None, "seen": []}
    # Decompress in another process (pigz when present) so this one only splits lines.
    dec = subprocess.Popen([shutil.which("pigz") or "gzip", "-dc", a.bundle], stdout=subprocess.PIPE,
                           bufsize=1 << 24)
    try:
        with mp.Pool(a.workers, initializer=_init, initargs=(a.repo_root,)) as pool:
            pending = collections.deque()

            def drain(limit):
                nonlocal nfail
                while len(pending) > limit:  # bounded in-flight work: the bundle is never buffered in memory
                    section, n, bad = pending.popleft().get()
                    counts[section] = counts.get(section, 0) + n
                    nfail += len(bad)
                    failures.extend(bad[: max(0, a.max_print - len(failures))])

            for task in tasks(dec.stdout, state, a.chunk):
                pending.append(pool.apply_async(_check, (task,)))
                drain(a.workers * 4)
            drain(0)
    except LayoutError as e:
        dec.kill()
        dec.wait()
        sys.exit(f"ERROR: {a.bundle}: {e}\nThe rs engine reads only the assembler's one-record-per-line layout, so it "
                 "stopped rather than skip records. Validate other JSON with --engine toolkit.")
    if dec.wait() != 0:
        sys.exit(f"ERROR: {a.bundle} could not be decompressed")

    sv, seen = state["sv"], state["seen"]
    total = sum(counts.values())
    print(f"bundle: {a.bundle}")
    print(f"schema_version: bundle={sv!r} schema const={const!r} -> {'OK' if sv == const else 'MISMATCH'}")
    for s, n in counts.items():
        print(f"  {s:28s} {n:>10,d}")
    print(f"records: {total:,d}  failing: {nfail:,d}  ({time.time() - t0:,.0f} s, {a.workers} workers, "
          f"jsonschema-rs {importlib.metadata.version('jsonschema-rs')})")
    for f in failures:
        print("  FAIL", f)
    empty = [x for x in seen if counts.get(x, 0) == 0]
    if empty:
        print("  EMPTY sections:", ", ".join(empty))
    ok = sv == const and nfail == 0 and total > 0 and not empty
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
