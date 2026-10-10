#!/usr/bin/env python3
"""Extract a self-contained example record from a ClinVar-GKM release's BigQuery
tables, with its ``#/…`` references resolved inline.

Accuracy: the per-section object is produced by the repo's OWN object-construction
SQL (``src/scripts/parquet-schemas/<section>.sql`` — the same SQL the release
Parquet export uses, which exposes a ``data`` column holding the exact assembled
bundle object) plus the shared ``collapse_ext_values`` UDF (read from
``export-gkm-dicts.sh``). So an extracted record equals what the release ships.

Usage:
    extract-example.py <section> <key> [--dataset DS | --date YYYY-MM-DD --version V]
                                       [--project clingen-dev]

Prints a pretty-printed, self-contained JSON object (references inlined) to stdout.
Example:
    extract-example.py vcv 'VCV000012582.63-G-PATH-CP'
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMA_DIR = SCRIPT_DIR / "parquet-schemas"
EXPORT_SH = SCRIPT_DIR / "export-gkm-dicts.sh"

# Sections whose object comes from a parquet-schema (its `data` column). Any ref
# section not listed here is handled specially below (condition, evidenceLine).
_REF_RE = re.compile(r"^#/(?P<section>[^/]+)/(?P<key>.+)$")
# A ref section maps 1:1 to a parquet-schema file of the same name, except these:
_EVIDENCE_CANDIDATES = ("evidenceLine", "vcv_evidenceLine", "rcv_evidenceLine")

# Reference-resolution policy (applied only to refs ENCOUNTERED while resolving;
# the top-level record requested on the CLI is always fetched in full):
#   - variation / scv: always kept as pointers — the variant (a proposition's
#     `subject`) has its own cat-vrs example, and an SCV submission is the LEAF of
#     the aggregation tree, so evidence unwinds down to SCV pointers;
#   - vcv / rcv: UNWOUND (inlined) so the aggregation/evidence tree is visible,
#     but descending into one marks everything below it as "nested";
#   - conditionSet / condition (a proposition's `object`): inlined on the TOP
#     statement only, kept as a pointer inside nested unwound statements (which
#     reference the same condition) so examples stay compact.
# Everything else (allele -> location -> sequenceReference, gene, therapy,
# submitter, evidenceLine, proposition) is inlined.
_ALWAYS_POINTER = {"variation", "scv"}
_UNWIND_STATEMENTS = {"vcv", "rcv"}
_CONDITION_SECTIONS = {"conditionSet", "condition"}
# Content-addressed dicts whose parquet-schema emits key/value columns (every
# other schema emits id/data).
_KEYVALUE_SECTIONS = {"therapy", "therapyGroup"}


def _collapse_udf() -> str:
    """Read the shared collapse_ext_values UDF from export-gkm-dicts.sh (single
    source of truth) so proposition/scv/evidenceLine schemas resolve correctly."""
    text = EXPORT_SH.read_text()
    m = re.search(r"COLLAPSE_UDF=\$\(cat <<'SQL'\n(.*?)\nSQL\n", text, re.S)
    if not m:
        sys.exit("ERROR: could not find COLLAPSE_UDF in export-gkm-dicts.sh")
    return m.group(1)


COLLAPSE_UDF = _collapse_udf()


def _bq_json(project: str, sql: str) -> list[dict]:
    out = subprocess.run(
        ["bq", "query", f"--project_id={project}", "--use_legacy_sql=false",
         "--format=json", "--quiet", "--nouse_cache", "--max_rows=10", sql],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout or "[]")


def _object_sql(section: str, dataset: str) -> str | None:
    """Inner SELECT producing (id, data) for a section, or None if unknown.

    `data` is the fully-assembled bundle object as a JSON string.
    """
    schema = SCHEMA_DIR / f"{section}.sql"
    if schema.is_file():
        return schema.read_text().replace("{DATASET}", dataset)
    if section == "condition":
        # No parquet-schema (condition.parquet is an untyped raw extract). The
        # bundle object is the full row with null/empty stripped (assemble.py
        # stream_passthrough parity) — mirror that here.
        return (
            "SELECT id, TO_JSON_STRING(JSON_STRIP_NULLS("
            "TO_JSON((SELECT AS STRUCT c.*)), remove_empty => TRUE)) AS data "
            f"FROM `{dataset}.gkm_dict_condition` c"
        )
    return None


def _candidate_sections(section: str) -> tuple[str, ...]:
    """Parquet-schema sections to try for a ref. `evidenceLine` merges three."""
    if section == "evidenceLine":
        return _EVIDENCE_CANDIDATES
    return (section,)


class Extractor:
    def __init__(self, project: str, dataset: str) -> None:
        self.project = project
        self.dataset = dataset
        self._raw_cache: dict[tuple[str, str], dict | None] = {}

    def fetch_raw(self, section: str, key: str) -> dict | None:
        """Fetch one section/key's assembled object (not yet ref-resolved)."""
        cache_key = (section, key)
        if cache_key in self._raw_cache:
            return self._raw_cache[cache_key]
        result: dict | None = None
        esc = key.replace("'", "''")
        for cand in _candidate_sections(section):
            inner = _object_sql(cand, self.dataset)
            if inner is None:
                continue
            # Schemas emit id/data, except the content-addressed therapy dicts
            # which emit key/value.
            idcol, datacol = (
                ("key", "value") if cand in _KEYVALUE_SECTIONS else ("id", "data")
            )
            # Normalise every section's object the way the conformant bundle wants:
            # strip null/empty fields, then collapse each extension's typed
            # `value_<type>` key to the single polymorphic `value`. Some section
            # schemas (e.g. variation) expose their object WITHOUT this collapse,
            # so apply it uniformly here; idempotent where already collapsed.
            sql = (
                f"{COLLAPSE_UDF}\n"
                "SELECT collapse_ext_values(TO_JSON_STRING("
                f"JSON_STRIP_NULLS(SAFE.PARSE_JSON({datacol}), remove_empty => TRUE)"
                ")) AS data\n"
                f"FROM (\n{inner}\n) WHERE {idcol} = '{esc}' LIMIT 1"
            )
            rows = _bq_json(self.project, sql)
            if rows:
                result = json.loads(rows[0]["data"])
                break
        self._raw_cache[cache_key] = result
        return result

    def resolve(self, value, trail: tuple[str, ...] = (), nested: bool = False):
        """Return `value` with local `#/…` pointers replaced by inline objects,
        per the policy above. `nested` is True once resolution has descended into
        an unwound vcv/rcv statement (so that statement's `object` condition stays
        a pointer). A pointer that closes a cycle is kept (JSON can't be cyclic).
        """
        if isinstance(value, str):
            m = _REF_RE.match(value)
            if not m:
                return value
            section = m.group("section")
            if value in trail:
                return value  # cycle — keep the pointer
            if section in _ALWAYS_POINTER:
                return value
            if section in _CONDITION_SECTIONS and nested:
                return value  # object condition inlined on the top statement only
            target = self.fetch_raw(section, m.group("key"))
            if target is None:
                # Unresolvable (missing/renamed) — keep the pointer, warn.
                print(f"  [extract] WARNING: could not resolve {value}", file=sys.stderr)
                return value
            child_nested = nested or section in _UNWIND_STATEMENTS
            return self.resolve(target, (*trail, value), child_nested)
        if isinstance(value, dict):
            return {k: self.resolve(v, trail, nested) for k, v in value.items()}
        if isinstance(value, list):
            return [self.resolve(v, trail, nested) for v in value]
        return value

    def extract(self, section: str, key: str):
        raw = self.fetch_raw(section, key)
        if raw is None:
            sys.exit(f"ERROR: {section} '{key}' not found in {self.dataset}")
        return self.resolve(raw, (f"#/{section}/{key}",))


def _latest_dataset(project: str) -> str:
    out = subprocess.run(
        ["bq", "ls", f"--project_id={project}", "--max_results=100000"],
        capture_output=True, text=True, check=True,
    ).stdout
    dsets = sorted(
        line.split()[0] for line in out.splitlines()
        if re.match(r"clinvar_\d{4}_\d{2}_\d{2}_v", line.split()[0] if line.split() else "")
    )
    if not dsets:
        sys.exit("ERROR: no clinvar_* dataset found; pass --dataset")
    return dsets[-1]


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract a self-contained GKM example record.")
    ap.add_argument("section", help="bundle section, e.g. vcv, scv, rcv, variation")
    ap.add_argument("key", help="record id/key, e.g. VCV000012582.63-G-PATH-CP")
    ap.add_argument("--project", default="clingen-dev")
    ap.add_argument("--dataset", help="BigQuery dataset; default = latest clinvar_* release")
    ap.add_argument("--date", help="release date YYYY-MM-DD (with --version)")
    ap.add_argument("--version", help="dataset version, e.g. v2_6_0 (with --date)")
    args = ap.parse_args()

    if args.dataset:
        dataset = args.dataset
    elif args.date and args.version:
        dataset = f"clinvar_{args.date.replace('-', '_')}_{args.version}"
    else:
        dataset = _latest_dataset(args.project)

    extractor = Extractor(args.project, dataset)
    record = extractor.extract(args.section, args.key)
    print(json.dumps(record, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
