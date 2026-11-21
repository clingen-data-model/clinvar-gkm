#!/usr/bin/env python3
"""Write a stratified sample of a full bundle, so the GA4GH gkm-toolkit can cross-check the rs engine at a release.

rs (jsonschema-rs) validates every record of every published bundle. The toolkit (python-jsonschema) is far too slow
for a 1.2.0 full (about 17 h on 64 vCPUs: it re-evaluates every allOf/$ref layer for each unevaluatedProperties), so a
version release runs it on this sample instead:

    ./src/scripts/sample-bundle.py <full.json.gz> <sample.json.gz> [--fraction 0.01] [--min 3000]
    ./src/scripts/validate-bundle.sh <sample.json.gz> --engine toolkit

Per section it keeps max(fraction x N, min(N, --min)) records, spread evenly over the section (systematic, not the
first ones), verbatim: the lines are copied byte for byte, so the sample can't mask an export or assembler bug. Two
passes: the first counts each section. The input must be in the assembler's one-record-per-line layout.
"""
import argparse
import json
import re
import subprocess
import gzip

SECTION = re.compile(rb'^  "([A-Za-z]+)": \{\n$')


def lines(path):
    proc = subprocess.Popen(["gzip", "-dc", path], stdout=subprocess.PIPE, bufsize=1 << 20)
    yield from proc.stdout
    if proc.wait() != 0:
        raise SystemExit(f"ERROR: gzip -dc {path} failed")


def count(path):
    counts, section = {}, None
    for line in lines(path):
        if line.startswith(b"    "):
            counts[section] += 1
        elif m := SECTION.match(line):
            section = m.group(1).decode()
            counts[section] = 0
    return counts


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("bundle")
    p.add_argument("out")
    p.add_argument("--fraction", type=float, default=0.01)
    p.add_argument("--min", type=int, default=3000, help="records kept per section at least (all, if fewer)")
    a = p.parse_args()

    counts = count(a.bundle)
    target = {s: max(round(n * a.fraction), min(n, a.min)) for s, n in counts.items()}
    kept = dict.fromkeys(counts, 0)
    section, i, pending, first = None, 0, [], True
    with gzip.open(a.out, "wb") as out:
        def flush():
            nonlocal first
            out.write((b"" if first else b",\n") + b'  "' + section.encode() + b'": {\n')
            out.write(b",\n".join(pending) + b"\n  }")
            first = False

        for line in lines(a.bundle):
            if line.startswith(b"    "):
                n, t = counts[section], target[section]
                if (i + 1) * t // n > i * t // n:
                    pending.append(line.rstrip(b"\n").rstrip(b","))
                    kept[section] += 1
                i += 1
            elif m := SECTION.match(line):
                section, i, pending = m.group(1).decode(), 0, []
            elif line.startswith(b"  }"):
                flush()
                section = None
            elif line.startswith(b'  "schema_version"'):
                out.write(b"{\n" + line.rstrip(b"\n").rstrip(b",") + b",\n")
            elif line.strip() not in (b"{", b"}"):
                raise SystemExit(f"ERROR: not the assembler's one-record-per-line layout: {line[:120]!r}")
        out.write(b"\n}\n")

    for s, n in counts.items():
        print(f"  {s:34s} {n:>11,d} -> {kept[s]:>9,d}")
    print(f"  total {sum(counts.values()):,d} -> {sum(kept.values()):,d} records in {a.out}")
    with open(a.out + ".stats.json", "w") as fh:
        json.dump({"source": a.bundle, "counts": counts, "kept": kept}, fh, indent=1)


if __name__ == "__main__":
    main()
