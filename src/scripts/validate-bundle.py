#!/usr/bin/env python3
"""Validate EVERY record of a real bundle (.json.gz) with the GA4GH gkm-toolkit. Run it through validate-bundle.sh.

The bundle is streamed (ijson) so it never has to fit in memory. Records are passed to ga4gh.gkm
validate_bundle_schema VERBATIM (no cleanup, no re-collapse: unlike sub-bundle.py this cannot mask an
export/assembler bug), in chunks of --chunk records per section, each chunk wrapped as
{"schema_version": <bundle's own value>, <section>: {key: record, ...}}. The registry is built by
validate-schema-conformance.py's load_registry over the whole schema/ tree (strict, as published).

Also checks: the bundle's schema_version equals the schema const; every section is non-empty
(minProperties 1). Exit 0 only when every record passes.

Usage: python validate-bundle.py <bundle.json.gz> <repo_root> [--workers N] [--chunk N] [--max-print N]
"""
import argparse
import collections
import gzip
import importlib.util
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import ijson

G = {}


def _init(repo_root):
    spec = importlib.util.spec_from_file_location(
        "vsc", Path(repo_root) / "src/scripts/validate-schema-conformance.py")
    vsc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vsc)
    from jsonschema import Draft202012Validator
    from ga4gh.gkm.bundles.schema_validation import validate_bundle_schema
    registry, _ = vsc.load_registry(Path(repo_root) / "schema", relax=False)
    schema = json.loads((Path(repo_root) / "schema/clinvar-gkm/clinvar-gkm-bundle.schema.json").read_text())
    G.update(schema=schema, validate=validate_bundle_schema,
             validator=Draft202012Validator(schema, registry=registry))


def _check(task):
    sv, section, items = task
    try:
        G["validate"]({"schema_version": sv, section: dict(items)}, G["schema"], validator=G["validator"])
        return section, len(items), []
    except Exception:  # find the failing records in this chunk
        bad = []
        for k, rec in items:
            try:
                G["validate"]({"schema_version": sv, section: {k: rec}}, G["schema"], validator=G["validator"])
            except Exception as e:  # noqa: BLE001
                bad.append(f"{section}/{k}: {str(e)[:300]}")
        if not bad:
            bad.append(f"{section}: chunk-level failure not reproducible per record")
        return section, len(items), bad


def records(path, seen):
    """Yield ('schema_version', None, value) once, then (section, key, record) for every entry, adding each
    top-level section to `seen`.

    Depth is tracked from the start/end events, NOT from dots in the ijson prefix: record keys such as
    'ga4gh:SL.x', 'clinvar.trait:1' or 'clinvar.submission:SCV1.2' contain dots (a dot-count depth
    silently dropped every such section)."""
    with gzip.open(path, "rb") as fh:
        lvl = 0; section = key = builder = None; bdepth = 0
        for _prefix, event, value in ijson.parse(fh, use_float=True):
            if builder is not None:
                builder.event(event, value)
                if event in ("start_map", "start_array"):
                    bdepth += 1
                elif event in ("end_map", "end_array"):
                    bdepth -= 1
                    if bdepth == 0:
                        yield section, key, builder.value
                        builder = None
                continue
            if event in ("start_map", "start_array"):
                if lvl == 2:                       # a record value
                    builder = ijson.ObjectBuilder(); builder.event(event, value); bdepth = 1
                else:
                    lvl += 1
            elif event in ("end_map", "end_array"):
                lvl -= 1
            elif event == "map_key":
                if lvl == 1:
                    section = value
                    if value != "schema_version":
                        seen.append(value)
                elif lvl == 2:
                    key = value
            elif lvl == 1 and section == "schema_version":
                yield "schema_version", None, value
            elif lvl == 2:                         # scalar record value
                yield section, key, value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle")
    ap.add_argument("repo_root")
    ap.add_argument("--workers", type=int, default=max(1, mp.cpu_count() - 1))
    ap.add_argument("--chunk", type=int, default=2000)
    ap.add_argument("--max-print", type=int, default=20)
    a = ap.parse_args()

    _init(a.repo_root)
    const = G["schema"]["properties"]["schema_version"].get("const")
    t0 = time.time()
    counts, failures, seen, sv, nfail = {}, [], [], None, 0

    def tasks():
        nonlocal sv
        buf, cur = [], None
        for section, key, rec in records(a.bundle, seen):
            if section == "schema_version":
                sv = rec
                continue
            if cur is not None and section != cur and buf:
                yield sv, cur, buf
                buf = []
            cur = section
            buf.append((key, rec))
            if len(buf) >= a.chunk:
                yield sv, cur, buf
                buf = []
        if buf:
            yield sv, cur, buf

    with mp.Pool(a.workers, initializer=_init, initargs=(a.repo_root,)) as pool:
        pending = collections.deque()

        def drain(limit):
            nonlocal nfail
            while len(pending) > limit:  # bounded in-flight work: the bundle is never buffered in memory
                section, n, bad = pending.popleft().get()
                counts[section] = counts.get(section, 0) + n
                nfail += len(bad)
                failures.extend(bad[: max(0, a.max_print - len(failures))])

        for task in tasks():
            pending.append(pool.apply_async(_check, (task,)))
            drain(a.workers * 3)
        drain(0)

    total = sum(counts.values())
    print(f"bundle: {a.bundle}")
    print(f"schema_version: bundle={sv!r} schema const={const!r} -> {'OK' if sv == const else 'MISMATCH'}")
    for s, n in counts.items():
        print(f"  {s:28s} {n:>10,d}")
    print(f"records: {total:,d}  failing: {nfail:,d}  ({time.time() - t0:,.0f} s, {a.workers} workers)")
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
