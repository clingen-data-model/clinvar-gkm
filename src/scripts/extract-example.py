#!/usr/bin/env python3
"""Extract example fragments from a published ClinVar-GKM bundle (.json.gz).

Each example is a small bundle fragment, ``{"schema_version": ..., "<section>": {"<key>": record}, ...}``. It holds
one top record exactly as the bundle has it (pointer form), plus every record that the top record references,
followed transitively, EXCEPT records in the statement sections (``scv``, ``vcv``, ``rcv``) and in ``variation``. A
pointer into one of those sections stays a ``#/…`` pointer that does not resolve inside the fragment:

- a statement's nested statements (``#/vcv/…-CP``, ``#/rcv/…``) and the SCVs it aggregates (``#/scv/…``), which are
  examples of their own;
- a proposition's ``subject`` (``#/variation/…``), which the two cat-vrs examples cover.

So a fragment validates against the bundle schema, but it is not a closed bundle. ``sub-bundle.py`` builds closed
bundles from BigQuery instead.

The bundle must be in the one-record-per-line layout that assemble-gkm-dicts.py writes. Records are copied with no
cleanup (only indented for reading), so an example holds what the bundle ships. Referenced records come earlier in the bundle than the
records that reference them, so a pass can only find what an earlier pass asked for. The first pass keeps the small
sections whole, the top records, and the evidence lines and propositions keyed by an example's accession, which
closes every statement example; the cat-vrs examples take two more passes (allele, then the allele's location).

Usage:
    extract-example.py --bundle <full.json.gz> --all [--examples-dir examples] [--schema-version 1.2.0]
    extract-example.py --bundle <full.json.gz> <section> <key> [--schema-version 1.2.0]   # print one to stdout

``--all`` regenerates every example in EXAMPLES. When an accession has a new version in the bundle, the file named
for the old version is removed and the rename is printed, so links to it can be fixed.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Pointers into these sections are kept as pointers; the records are not pulled into the fragment.
KEEP_POINTER = {"scv", "vcv", "rcv", "variation"}
# Sections small enough to keep whole on the first pass (their records are referenced from later sections).
SMALL = {"sequenceReference", "gene", "condition", "conditionSet", "therapy", "therapyGroup", "submitter"}
# Sections whose keys carry the statement's accession, kept on the first pass when they match an example accession.
BY_ACCESSION = {"evidenceLine", "propositionPathogenicity", "propositionOncogenicity",
                "propositionSomaticClinicalImpact", "propositionClinvarCustom"}

# (directory, section, accession, suffix, extension). The bundle key and file name follow from the section:
#   variation: key = accession, file = <accession><ext>
#   scv:       key = clinvar.submission:<accession>.<version>, file = <accession>.<version>-<suffix><ext>
#   vcv / rcv: key = <accession>.<version>-<suffix>,            file = <key><ext>
EXAMPLES = [
    ("cat-vrs", "variation", "clinvar:12582", "", ".jsonc"),
    ("cat-vrs", "variation", "clinvar:208366", "", ".jsonc"),
    ("scv", "scv", "SCV001571657", "G-PATH", ".jsonc"),
    ("scv", "scv", "SCV002099547", "G-NP", ".jsonc"),
    ("scv", "scv", "SCV004035006", "G-ASSOC", ".jsonc"),
    ("scv", "scv", "SCV004565358", "S-SCI-T1-TR", ".json"),
    ("scv", "scv", "SCV004565361", "S-SCI-T2-DIAG", ".json"),
    ("scv", "scv", "SCV005061369", "S-SCI-T4-BLB", ".json"),
    ("scv", "scv", "SCV005093950", "S-ONCO", ".json"),
    ("scv", "scv", "SCV005387955", "S-SCI-T3-VUS", ".json"),
    ("vcv", "vcv", "VCV000007105", "G-DR", ".jsonc"),
    ("vcv", "vcv", "VCV000007105", "G-NP", ".jsonc"),
    ("vcv", "vcv", "VCV000007105", "G-PATH", ".jsonc"),
    ("vcv", "vcv", "VCV000007105", "G-RF", ".jsonc"),
    ("vcv", "vcv", "VCV000012582", "G-ASSOC", ".jsonc"),
    ("vcv", "vcv", "VCV000012582", "G-NP", ".jsonc"),
    ("vcv", "vcv", "VCV000012582", "G-PATH", ".jsonc"),
    ("vcv", "vcv", "VCV000012582", "S-ONCO", ".jsonc"),
    ("vcv", "vcv", "VCV000012582", "S-SCI", ".jsonc"),
    ("rcv", "rcv", "RCV000007523", "G-NP", ".jsonc"),
    ("rcv", "rcv", "RCV000007523", "G-PATH", ".jsonc"),
    ("rcv", "rcv", "RCV000029215", "G-PATH", ".jsonc"),
    ("rcv", "rcv", "RCV000272938", "G-PATH", ".jsonc"),
    ("rcv", "rcv", "RCV000548006", "G-PATH", ".jsonc"),
    ("rcv", "rcv", "RCV000585796", "G-PATH", ".jsonc"),
    ("rcv", "rcv", "RCV001781420", "G-PATH", ".jsonc"),
    ("rcv", "rcv", "RCV001787370", "G-DR", ".jsonc"),
    ("rcv", "rcv", "RCV001787371", "G-DR", ".jsonc"),
    ("rcv", "rcv", "RCV001839445", "G-NP", ".jsonc"),
    ("rcv", "rcv", "RCV003327361", "G-ASSOC", ".jsonc"),
    ("rcv", "rcv", "RCV004018620", "G-PATH", ".jsonc"),
    ("rcv", "rcv", "RCV004554600", "G-PATH", ".jsonc"),
    ("rcv", "rcv", "RCV004668724", "S-ONCO", ".jsonc"),
    ("rcv", "rcv", "RCV005007840", "G-PATH", ".jsonc"),
    ("rcv", "rcv", "RCV006253518", "S-SCI", ".jsonc"),
    ("rcv", "rcv", "RCV006253519", "S-SCI", ".jsonc"),
    ("rcv", "rcv", "RCV006253521", "S-SCI", ".jsonc"),
    ("rcv", "rcv", "RCV006253522", "S-SCI", ".jsonc"),
    ("rcv", "rcv", "RCV006253523", "S-SCI", ".jsonc"),
    ("rcv", "rcv", "RCV006253525", "S-SCI", ".jsonc"),
    ("rcv", "rcv", "RCV006253527", "S-SCI", ".jsonc"),
    ("rcv", "rcv", "RCV006254391", "S-SCI", ".jsonc"),
]

POINTER = re.compile(r"^#/([A-Za-z]+)/(.+)$")
SECTION_LINE = re.compile(rb'^  "([A-Za-z]+)": \{\n$')
SCHEMA_VERSION_LINE = re.compile(rb'^  "schema_version": ("(?:[^"\\]|\\.)*"),?\n$')


def key_pattern(section: str, accession: str, suffix: str) -> re.Pattern:
    """The bundle keys an example entry matches; group 1 is the version (absent for variation)."""
    acc = re.escape(accession)
    if section == "variation":
        return re.compile(rf"^{acc}$")
    if section == "scv":
        return re.compile(rf"^clinvar\.submission:{acc}\.(\d+)$")
    return re.compile(rf"^{acc}\.(\d+)-{re.escape(suffix)}$")


def file_name(section: str, accession: str, suffix: str, ext: str, key: str) -> str:
    """The example's file name for the bundle key it matched."""
    if section == "variation":
        return f"{accession}{ext}"
    if section == "scv":
        return f"{key.split(':', 1)[1]}-{suffix}{ext}"
    return f"{key}{ext}"


def superseded(directory: Path, accession: str, suffix: str, keep: str) -> list[Path]:
    """Files in `directory` for the same accession and suffix under another version (or extension) than `keep`."""
    if not suffix:
        return []
    pat = re.compile(rf"^{re.escape(accession)}\.\d+-{re.escape(suffix)}\.jsonc?$")
    return sorted(p for p in directory.glob(f"{accession}.*") if pat.match(p.name) and p.name != keep)


def pointers(value):
    """Every (section, key) that a `#/section/key` string anywhere in `value` points to."""
    if isinstance(value, str):
        m = POINTER.match(value)
        if m:
            yield m.group(1), m.group(2)
    elif isinstance(value, dict):
        for v in value.values():
            yield from pointers(v)
    elif isinstance(value, list):
        for v in value:
            yield from pointers(v)


def closure(top: tuple[str, str], lookup) -> tuple[dict, set, set]:
    """The fragment for `top`: (records {(section, key): record}, missing refs, kept pointers).

    `lookup((section, key))` returns the record or None. Pointers into KEEP_POINTER sections are kept, every other
    pointer is followed. `missing` lists the followed pointers `lookup` could not find (yet)."""
    records, missing, kept = {}, set(), set()
    todo = [top]
    while todo:
        ref = todo.pop()
        if ref in records or ref in missing:
            continue
        rec = lookup(ref)
        if rec is None:
            missing.add(ref)
            continue
        records[ref] = rec
        for p in pointers(rec):
            if p[0] in KEEP_POINTER:
                if p != top:
                    kept.add(p)
            else:
                todo.append(p)
    return records, missing, kept


def fragment(schema_version: str, records: dict, section_order: list[str]) -> dict:
    """The example document: schema_version, then the sections in bundle order, keys sorted within each."""
    doc = {"schema_version": schema_version}
    for section in section_order:
        keys = sorted(k for s, k in records if s == section)
        if keys:
            doc[section] = {k: records[(section, k)] for k in keys}
    return doc


def scan(bundle: Path, keep, state: dict):
    """Stream the bundle once; return {(section, key): record line} for every record `keep(section, key)` accepts.

    Records `state["schema_version"]` and `state["sections"]` (in bundle order). Stops on any line outside the
    assembler's layout."""
    dec = subprocess.Popen([shutil.which("pigz") or "gzip", "-dc", str(bundle)], stdout=subprocess.PIPE,
                           bufsize=1 << 24)
    found, section, sections = {}, None, []
    try:
        for line in dec.stdout:
            if line.startswith(b'    "'):
                end = line.index(b'": ', 5)
                raw = line[5:end]
                key = json.loads(b'"' + raw + b'"') if b"\\" in raw else raw.decode()
                if keep(section, key):
                    found[(section, key)] = line[end + 3:]
                continue
            m = SECTION_LINE.match(line)
            if m:
                section = m.group(1).decode()
                sections.append(section)
                continue
            m = SCHEMA_VERSION_LINE.match(line)
            if m:
                state["schema_version"] = json.loads(m.group(1))
                continue
            if line.rstrip(b"\n") in (b"{", b"}", b"  }", b"  },"):
                continue
            raise SystemExit(f"ERROR: {bundle}: not the assembler's one-record-per-line layout: {line[:120]!r}")
    finally:
        dec.stdout.close()
        if dec.wait() != 0:
            raise SystemExit(f"ERROR: {bundle} could not be decompressed")
    state["sections"] = sections
    return found


def extract(bundle: Path, tops: dict, accessions: list[str], log=print) -> tuple[dict, list[str], str]:
    """Build one fragment per entry of `tops` {name: (section, key pattern)}, in as few passes as the references need.

    `accessions` are the statement accessions whose evidence lines and propositions the first pass keeps. Returns
    ({name: (top key, records, kept pointers)}, section order, schema_version)."""
    by_section: dict[str, list] = {}
    for section, pattern in tops.values():
        by_section.setdefault(section, []).append(pattern)
    acc_rx = re.compile("|".join(re.escape(a) for a in accessions)) if accessions else None
    state: dict = {}
    lines: dict = {}
    parsed: dict = {}

    def lookup(ref):
        if ref not in parsed:
            line = lines.get(ref)
            parsed[ref] = None if line is None else json.loads(line.rstrip().rstrip(b","))
        return parsed[ref]

    def first_pass(section, key):
        if section in SMALL:
            return True
        if section in BY_ACCESSION:
            return acc_rx is not None and acc_rx.search(key) is not None
        return any(p.match(key) for p in by_section.get(section, ()))

    log(f"pass 1: {bundle}")
    lines.update(scan(bundle, first_pass, state))
    top_keys = {}
    for name, (section, pattern) in tops.items():
        keys = sorted(k for s, k in lines if s == section and pattern.match(k))
        if len(keys) != 1:
            raise SystemExit(f"ERROR: {name}: expected one {section} record matching {pattern.pattern}, found {keys}")
        top_keys[name] = (section, keys[0])
    passes = 1
    while True:
        results = {name: closure(top, lookup) for name, top in top_keys.items()}
        missing = set().union(set(), *(m for _, m, _ in results.values()))
        if not missing:
            break
        passes += 1
        log(f"pass {passes}: {len(missing)} referenced records")
        found = scan(bundle, lambda s, k: (s, k) in missing, state)
        if not found:
            raise SystemExit(f"ERROR: references not in the bundle: {sorted(missing)[:20]}")
        for ref in found:
            parsed.pop(ref, None)
        lines.update(found)
    return ({name: (top_keys[name][1], results[name][0], results[name][2]) for name in tops}, state["sections"],
            state["schema_version"])


def dumps(doc: dict) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract example fragments from a published ClinVar-GKM bundle.")
    ap.add_argument("--bundle", required=True, type=Path, help="full bundle .json.gz (assembler layout)")
    ap.add_argument("--all", action="store_true", help="regenerate every example in EXAMPLES")
    ap.add_argument("--examples-dir", type=Path, default=REPO_ROOT / "examples")
    ap.add_argument("--schema-version", help="schema_version to write (default: the bundle's)")
    ap.add_argument("section", nargs="?", help="with a key instead of --all: print that one fragment")
    ap.add_argument("key", nargs="?")
    args = ap.parse_args()
    if args.all == bool(args.section and args.key) or bool(args.section) != bool(args.key):
        ap.error("pass either --all or a section and a key")

    if not args.all:
        acc = re.findall(r"[SVR]CV\d+", args.key)
        results, order, sv = extract(args.bundle, {"one": (args.section, re.compile(rf"^{re.escape(args.key)}$"))},
                                     acc, log=lambda m: print(m, file=sys.stderr))
        sys.stdout.write(dumps(fragment(args.schema_version or sv, results["one"][1], order)))
        return

    tops = {(d, sec, acc, suf): (sec, key_pattern(sec, acc, suf)) for d, sec, acc, suf, _ in EXAMPLES}
    accessions = sorted({acc for _, sec, acc, _, _ in EXAMPLES if sec != "variation"})
    results, order, sv = extract(args.bundle, tops, accessions)
    sv = args.schema_version or sv
    for directory, sec, acc, suf, ext in EXAMPLES:
        top, records, kept = results[(directory, sec, acc, suf)]
        out_dir = args.examples_dir / directory
        name = file_name(sec, acc, suf, ext, top)
        for old in superseded(out_dir, acc, suf, name):
            old.unlink()
            print(f"renamed: {directory}/{old.name} -> {directory}/{name}")
        (out_dir / name).write_text(dumps(fragment(sv, records, order)), encoding="utf-8")
        kinds: dict[str, int] = {}
        for s, _ in kept:
            kinds[s] = kinds.get(s, 0) + 1
        print(f"{directory}/{name}: {len(records)} records; pointers kept: "
              + (", ".join(f"#/{s}/ {n}" for s, n in sorted(kinds.items())) or "none"))


if __name__ == "__main__":
    main()
