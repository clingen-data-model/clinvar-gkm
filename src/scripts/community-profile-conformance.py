#!/usr/bin/env python3
"""Count how a bundle's SCV statements differ from the VA-Spec community statement profiles.

ClinVar-GKM holds its SCVs to its own profiles (ClinvarScvPathogenicityStatement, ...), each modelled on a VA-Spec
community profile minus documented differences. This report measures every SCV in the pathogenicity, oncogenicity
and somatic clinical impact sections against the unchanged community profile, and counts each reason it fails:

- no specifiedBy           the community profile requires specifiedBy; ClinVar SCVs may have no assertion method
- classification coding    the classification's code or system is not one the community profile allows
- classification name      the classification's name is not the one the community profile fixes (AMP tiers)
- strength coding          the strength's code or system is not one the community profile allows
- other                    anything else

Run it by hand on each monthly full; --write-docs refreshes the counts on the Community Profiles page. Needs
jsonschema-rs and orjson (the uv environment validate-bundle.sh builds):

    uv run --no-project --quiet --python 3.12 --with "jsonschema-rs==0.61.1" --with orjson \\
        python src/scripts/community-profile-conformance.py <bundle.json.gz> [--json out.json] \\
        [--write-docs docs/profiles/community-profiles.md]

Reads only the one-record-per-line layout assemble-gkm-dicts.py writes.
"""
import argparse
import datetime
import gzip
import importlib.util
import json
import sys
from pathlib import Path

import jsonschema_rs
import orjson

REPO = Path(__file__).resolve().parents[2]
PROFILES = {
    "propositionPathogenicity": ("acmg-2015", "VariantPathogenicityStatement"),
    "propositionOncogenicity": ("ccv-2022", "VariantOncogenicityStatement"),
    "propositionSomaticClinicalImpact": ("aac-2017", "VariantClinicalSignificanceStatement"),
}
NAMES = {"acmg-2015": "ACMG 2015", "ccv-2022": "CCV 2022", "aac-2017": "AMP/ASCO/CAP 2017"}
REASONS = ["no specifiedBy", "classification coding", "classification name", "strength coding", "other"]
START, END = "<!-- community-conformance:start -->", "<!-- community-conformance:end -->"
_validators = {}


def _validate_bundle_rs():
    path = Path(__file__).with_name("validate-bundle-rs.py")
    spec = importlib.util.spec_from_file_location("validate_bundle_rs", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validator(community):
    """The community profile's statement schema, compiled once against the local registry."""
    if not _validators:
        registry = _validate_bundle_rs().local_registry(REPO / "schema")
        for name, cls in PROFILES.values():
            schema = json.loads((REPO / "schema/va-spec/json" / name / cls).read_text())
            _validators[name] = jsonschema_rs.Draft202012Validator(schema, registry=registry, validate_formats=False)
    return _validators[community]


def reasons(community, record):
    """The set of reasons the record fails the community profile (empty when it conforms)."""
    found = set()
    for error in validator(community).iter_errors(record):
        path = "/".join(str(p) for p in error.instance_path)
        if isinstance(error.kind, jsonschema_rs.ValidationErrorKind.Required) and error.kind.property == "specifiedBy":
            found.add("no specifiedBy")
        elif path.startswith("classification/primaryCoding"):
            found.add("classification coding")
        elif path == "classification/name":
            found.add("classification name")
        elif path.startswith("strength"):
            found.add("strength coding")
        else:
            found.add("other")
    return found


def scv_records(bundle_path):
    """Yield each record of the bundle's scv section."""
    section = None
    with gzip.open(bundle_path, "rb") as f:
        for line in f:
            if line.startswith(b'  "') and line.rstrip().endswith(b"{"):
                section = line.split(b'"')[1].decode()
            elif section == "scv" and line.startswith(b'    "'):
                yield from orjson.loads(b"{" + line.rstrip().rstrip(b",") + b"}").values()


def report(bundle_path):
    """{community: {"scvs": n, "conformant": n, "reasons": {reason: n}}}, each reason counted once per record."""
    out = {name: {"scvs": 0, "conformant": 0, "reasons": {}} for name, _ in PROFILES.values()}
    for record in scv_records(bundle_path):
        section = str(record.get("proposition", "")).split("/")[1:2]
        if not section or section[0] not in PROFILES:
            continue
        community = PROFILES[section[0]][0]
        counts = out[community]
        counts["scvs"] += 1
        found = reasons(community, record)
        if not found:
            counts["conformant"] += 1
        for reason in found:
            counts["reasons"][reason] = counts["reasons"].get(reason, 0) + 1
    return out


def table(bundle_path, result):
    lines = [f"Counts from `{Path(bundle_path).name}`, generated {datetime.date.today().isoformat()}.", "",
             "| Community profile | SCVs | Conformant | " + " | ".join(r.capitalize() for r in REASONS) + " |",
             "| --- | ---: | ---: | " + " | ".join("---:" for _ in REASONS) + " |"]
    for name, _ in PROFILES.values():
        c = result[name]
        lines.append(f"| {NAMES[name]} | {c['scvs']:,} | {c['conformant']:,} | "
                     + " | ".join(f"{c['reasons'].get(r, 0):,}" for r in REASONS) + " |")
    return "\n".join(lines)


def write_docs(page, bundle_path, result):
    """Replace the text between the community-conformance markers on the page with the counts table."""
    text = Path(page).read_text()
    if text.count(START) != 1 or text.count(END) != 1 or text.index(START) > text.index(END):
        sys.exit(f"{page}: needs exactly one {START} ... {END} block")
    head, rest = text.split(START)
    _, tail = rest.split(END)
    Path(page).write_text(f"{head}{START}\n{table(bundle_path, result)}\n{END}{tail}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle", help="a bundle .json.gz in the assembler's layout")
    ap.add_argument("--json", help="also write the counts as JSON to this path")
    ap.add_argument("--write-docs", help="refresh the counts block on this Markdown page")
    args = ap.parse_args()
    result = report(args.bundle)
    print(table(args.bundle, result))
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2) + "\n")
    if args.write_docs:
        write_docs(args.write_docs, args.bundle, result)


if __name__ == "__main__":
    main()
