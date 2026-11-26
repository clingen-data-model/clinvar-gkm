#!/usr/bin/env python3
"""Give the records of a 1.0, 1.1 or 1.2 ClinVar-GKM bundle the guideline codings that 1.3.0 corrected.

  python3 recode-1-3-0.py IN.json.gz OUT.json.gz

1.3.0 changed these codings, on every SCV, VCV and RCV statement and wherever else a coding carries them:

  code    tier 1, tier 2, tier 3, tier 4              -> tier i, tier ii, tier iii, tier iv
  system  AMP/ASCO/CAP (AAC) Guidelines, 2017         -> AMP/ASCO/CAP Guidelines, 2017
  system  SVC v4                                      -> ACMG/AMP/CAP/ClinGen SVCv4.0
  code    pathogenic/Likely pathogenic                -> pathogenic/likely pathogenic

and added, on SCVs, the tier's canonical name to the classification coding (Tier I ... Tier IV), and, on statements
classified VUS-high, VUS-mid or VUS-low, a strength (High, Mid, Low; coded under SVCv4 on SCVs). Each is a function
of the old record, so this script makes the change in place. The output keeps the input's layout and its
schema_version: it is an older line's bundle with 1.3.0's codings, not a 1.3.0 bundle. A record line with none of
the old codings is copied byte for byte. Needs Python 3.9 or later; no packages.
https://clinvar-gkm.org/reference/known-issues/#guideline-codings-before-1-3-0
"""
import gzip
import json
import re
import sys

TIERS = {"tier 1": "tier i", "tier 2": "tier ii", "tier 3": "tier iii", "tier 4": "tier iv"}
TIER_NAMES = {"tier i": "Tier I", "tier ii": "Tier II", "tier iii": "Tier III", "tier iv": "Tier IV"}
CODES = {**TIERS, "pathogenic/Likely pathogenic": "pathogenic/likely pathogenic"}
SVCV4 = "ACMG/AMP/CAP/ClinGen SVCv4.0"
SYSTEMS = {"AMP/ASCO/CAP (AAC) Guidelines, 2017": "AMP/ASCO/CAP Guidelines, 2017", "SVC v4": SVCV4}
VUS_STRENGTHS = {"vus-high": ("high", "High"), "vus-mid": ("mid", "Mid"), "vus-low": ("low", "Low")}
# A record line holding any of these may need a change; any other line is copied as it is.
OLD = (b'"tier ', b"(AAC)", b'"SVC v4"', b"/Likely pathogenic")


def recode(section, record):
    """Return the record with 1.3.0's codings. `section` is its bundle section (scv, vcv, rcv, ...)."""
    _walk(record)
    if section == "scv":
        coding = (record.get("classification") or {}).get("primaryCoding") or {}
        if coding.get("code") in TIER_NAMES:
            coding["name"] = TIER_NAMES[coding["code"]]
    _vus_strengths(record, section == "scv")
    return record


def _walk(node):
    if isinstance(node, dict):
        coding = node.get("primaryCoding")
        if isinstance(coding, dict):
            if coding.get("code") in CODES:
                coding["code"] = CODES[coding["code"]]
            if coding.get("system") in SYSTEMS:
                coding["system"] = SYSTEMS[coding["system"]]
        for value in node.values():
            _walk(value)
    elif isinstance(node, list):
        for value in node:
            _walk(value)


def _vus_strengths(node, is_scv):
    """Give each statement classified VUS-high/mid/low its strength: the record itself (an SCV when is_scv) and
    the aggregate statements nested in a VCV or RCV record."""
    if isinstance(node, dict):
        code = ((node.get("classification") or {}).get("primaryCoding") or {}).get("code")
        if code in VUS_STRENGTHS and "strength" not in node:
            strength_code, name = VUS_STRENGTHS[code]
            strength = {"conceptType": "Strength", "name": name, "type": "MappableConcept"}
            if is_scv:
                strength["primaryCoding"] = {"code": strength_code, "system": SVCV4}
            node["strength"] = strength
        for value in node.values():
            _vus_strengths(value, False)
    elif isinstance(node, list):
        for value in node:
            _vus_strengths(value, False)


SECTION = re.compile(rb'^  "([A-Za-z0-9_]+)": \{\n$')


def main(src, dst):
    """Copy the bundle src to dst, recoding each record line that holds an old coding. Prints the count."""
    section, changed = None, 0
    with gzip.open(src, "rb") as fin, gzip.open(dst, "wb") as fout:
        for line in fin:
            if section and line.startswith(b'    "') and any(old in line for old in OLD):
                body = line[4:].rstrip(b"\n")
                comma = body.endswith(b",")
                key, end = json.JSONDecoder().raw_decode(body.removesuffix(b",").decode())
                text = body.removesuffix(b",")[end + 2:].decode()
                record = recode(section, json.loads(text))
                if record != json.loads(text):
                    changed += 1
                    new = json.dumps(record, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
                    line = b"    " + json.dumps(key).encode() + b": " + new.encode() + (b"," if comma else b"") + b"\n"
            elif m := SECTION.match(line):
                section = m.group(1).decode()
            elif line in (b"  }\n", b"  },\n"):
                section = None
            fout.write(line)
    print(f"{changed} records recoded", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
