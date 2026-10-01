#!/usr/bin/env python3
"""sub-bundle.py — pull a list of statements (SCV / VCV / RCV) into ONE bundled JSON.

Given statement ids, transitively resolves every `#/section/key` reference across the
`gkm_dict_*` tables of a built release dataset and assembles a SINGLE self-contained
bundle — a JSON object of named sections `{ "<section>": { "<key>": <object> }, ... }`
in which every `#/…` pointer resolves. References shared by multiple input statements are
fetched and emitted ONCE (deduplicated): the output is one clean bundle that supports all
the requested statements, not one document per statement.

Accepts SCV, VCV, and RCV identifiers (mixed). Each id may be a full statement key
(e.g. `SCV004101425.2`, `VCV000012582.63-G-PATH-CP`, `RCV000012345.8-G-PATH-CP`) or a
bare accession (e.g. `VCV000012582.63`) to include every statement under it. VCV/RCV
statements pull in their contributing SCVs (via evidence-line `hasEvidenceItems`), so a
VCV/RCV bundle is self-contained down to the VRS sequence references.

Objects get the same transform as the release export: extension `value_<type>` collapsed
to a single `value`, and null/empty fields stripped (JSON_STRIP_NULLS).

Usage:
  # mixed statement ids as args
  python3 src/scripts/sub-bundle.py --dataset clinvar_2026_08_16_v2_5_0 \
      SCV004101425.2 VCV000012582.63-G-PATH-CP RCV000012345.8-G-PATH-CP -o bundle.json

  # ids from a file (one per line) or stdin
  python3 src/scripts/sub-bundle.py --dataset clinvar_2026_08_16_v2_5_0 --ids-file ids.txt -o bundle.json
  cat ids.txt | python3 src/scripts/sub-bundle.py --dataset clinvar_2026_08_16_v2_5_0 -

Requires the dataset to have the gkm_dict_* tables built (a completed release / Stage 4).
"""
import argparse
import json
import re
import subprocess
import sys

KV, ST = "kv", "struct"  # table mode: (key,value JSON) vs typed table keyed by `id`

# sections resolvable from a single fixed table
SIMPLE = {
    "scv": ("gkm_dict_scv", ST),
    "vcv": ("gkm_dict_vcv", ST),
    "rcv": ("gkm_dict_rcv", ST),
    "variation": ("gkm_dict_variation", ST),
    "condition": ("gkm_dict_condition", ST),
    "conditionSet": ("gkm_dict_condition_set", ST),
    "submitter": ("gkm_dict_submitter", KV),
    "allele": ("gkm_dict_allele", KV),
    "location": ("gkm_dict_location", KV),
    "sequenceReference": ("gkm_dict_sequence_reference", KV),
    "gene": ("gkm_dict_gene", KV),
    "copyNumberCount": ("gkm_dict_copy_number_count", KV),
    "copyNumberChange": ("gkm_dict_copy_number_change", KV),
}
# proposition + evidenceLine live in SCV/VCV/RCV-specific tables; route by key prefix
PROP_BY_PREFIX = {"SCV": ("gkm_dict_proposition", KV),
                  "VCV": ("gkm_dict_vcv_proposition", KV),
                  "RCV": ("gkm_dict_rcv_proposition", KV)}
EL_BY_PREFIX = {"SCV": ("gkm_dict_evidence_line", ST),
                "VCV": ("gkm_dict_vcv_evidence_line", ST),
                "RCV": ("gkm_dict_rcv_evidence_line", ST)}

# stable bundle section order (mirrors the release bundle assembly order)
SECTION_ORDER = [
    "sequenceReference", "location", "allele", "copyNumberCount", "copyNumberChange",
    "gene", "variation", "condition", "conditionSet", "submitter",
    "varcond-proposition", "vartumor-proposition", "vartherapy-proposition",
    "varcustom-proposition", "evidenceLine", "scv", "vcv", "rcv",
]
REF_RE = re.compile(r'"#/([A-Za-z0-9_-]+)/([^"]+)"')

COLLAPSE_UDF = r'''CREATE TEMP FUNCTION collapse_ext_values(j STRING)
RETURNS STRING LANGUAGE js AS r"""
  if (j == null) return null;
  function walk(o){
    if (Array.isArray(o)){ for (const x of o) walk(x); return; }
    if (o && typeof o === "object"){
      if ("name" in o){ for (const k of Object.keys(o)){ if (k.indexOf("value_")===0){ o["value"]=o[k]; delete o[k]; } } }
      for (const k of Object.keys(o)) walk(o[k]);
    }
  }
  const p = JSON.parse(j); walk(p); return JSON.stringify(p);
""";'''


def bq_query(sql, project, max_rows=1000000):
    proc = subprocess.run(
        ["bq", "--project_id=" + project, "query", "--use_legacy_sql=false",
         "--format=json", "--quiet", "--max_rows=" + str(max_rows)],
        input=sql, capture_output=True, text=True, timeout=600,
    )
    if proc.returncode != 0:
        sys.stderr.write("  bq error: " + proc.stderr.strip()[-400:] + "\n")
        return None
    return json.loads(proc.stdout or "[]")


def _side(key):
    """Which statement side a proposition/evidence-line key belongs to.

    Proposition keys are `SCV…`/`VCV…`/`RCV…`; SCV evidence-line keys are
    `clinvar.submission:SCV…` while VCV/RCV evidence-line keys are `VCV…`/`RCV…`.
    Anything not VCV/RCV (bare SCV or clinvar.submission:) is the SCV side.
    """
    u = key.upper()
    if u.startswith("VCV"):
        return "VCV"
    if u.startswith("RCV"):
        return "RCV"
    return "SCV"


def table_for(section, key):
    """Resolve (section, key) -> (table, mode), or None if the section is unknown."""
    if section in SIMPLE:
        return SIMPLE[section]
    if section.endswith("-proposition"):
        return PROP_BY_PREFIX.get(_side(key))
    if section == "evidenceLine":
        return EL_BY_PREFIX.get(_side(key))
    return None


def fetch(dataset, project, table, mode, keys):
    """Fetch objects for `keys` from one table. Returns {key: parsed-object}."""
    keylist = ", ".join("'" + k + "'" for k in sorted(keys))
    if mode == KV:
        body = (f"SELECT key AS k, collapse_ext_values(TO_JSON_STRING("
                f"JSON_STRIP_NULLS(value, remove_empty => TRUE))) AS v "
                f"FROM `{dataset}.{table}` WHERE key IN ({keylist})")
    else:
        body = (f"SELECT id AS k, collapse_ext_values(TO_JSON_STRING("
                f"JSON_STRIP_NULLS(TO_JSON(t), remove_empty => TRUE))) AS v "
                f"FROM `{dataset}.{table}` t WHERE id IN ({keylist})")
    rows = bq_query(COLLAPSE_UDF + "\n" + body, project)
    return {r["k"]: json.loads(r["v"]) for r in (rows or []) if r.get("v")}


def refs_in(obj):
    for m in REF_RE.finditer(json.dumps(obj)):
        yield (m.group(1), m.group(2))


def resolve_seeds(dataset, project, kind, raws):
    """Expand raw statement ids (exact keys or bare accessions) -> [(section, key)]."""
    table = {"scv": "gkm_dict_scv", "vcv": "gkm_dict_vcv", "rcv": "gkm_dict_rcv"}[kind]
    preds = []
    for r in raws:
        r = r.replace("'", "")  # keys never contain quotes; strip defensively
        preds += [f"id = '{r}'", f"STARTS_WITH(id, '{r}-')", f"STARTS_WITH(id, '{r}.')"]
    rows = bq_query(f"SELECT id AS k FROM `{dataset}.{table}` WHERE {' OR '.join(preds)}", project)
    return [(kind, row["k"]) for row in (rows or [])]


def build_store(dataset, project, seeds):
    """Batched BFS from the seed statements; fetch every reachable object once."""
    store = {}
    pending = set(seeds)
    seen = set(pending)
    while pending:
        by_table = {}   # (table, mode) -> {key: [(section,key), ...]}
        for section, key in pending:
            tm = table_for(section, key)
            if tm is None:
                sys.stderr.write(f"  warning: unknown section '{section}' (key {key})\n")
                store[(section, key)] = None
                continue
            by_table.setdefault(tm, {}).setdefault(key, []).append((section, key))
        new_pending = set()
        for (table, mode), keymap in by_table.items():
            found = fetch(dataset, project, table, mode, set(keymap))
            for key, refs in keymap.items():
                obj = found.get(key)
                for ref in refs:
                    store[ref] = obj
                if obj is None:
                    sys.stderr.write(f"  warning: {table}/{key} not found\n")
                    continue
                for r in refs_in(obj):
                    if r not in seen:
                        seen.add(r)
                        new_pending.add(r)
        pending = new_pending
    return store


def to_bundle(store):
    """Assemble the store into an ordered {section: {key: obj}} bundle (drops misses)."""
    bundle = {}
    for (section, key), obj in store.items():
        if obj is not None:
            bundle.setdefault(section, {})[key] = obj
    ordered = {}
    for s in SECTION_ORDER:
        if s in bundle:
            ordered[s] = {k: bundle[s][k] for k in sorted(bundle[s])}
    for s in bundle:  # any section outside the known order, appended deterministically
        if s not in ordered:
            ordered[s] = {k: bundle[s][k] for k in sorted(bundle[s])}
    return ordered


def dump_bundle(bundle, out):
    """Write the bundle as valid JSON with one compact line per record.

    Sections are keyed on their own lines; each object *value* is emitted on a
    single line (compact separators), so the file has ~one line per record rather
    than one per field. Stays a single valid JSON document — just far fewer lines
    than a fully pretty-printed bundle, which matters for large (thousands of
    records) sub-bundles.
    """
    out.write("{\n")
    sections = list(bundle.items())
    for si, (section, items) in enumerate(sections):
        entries = list(items.items())
        out.write(f"  {json.dumps(section)}: {{")
        if entries:
            out.write("\n")
            for ki, (key, obj) in enumerate(entries):
                comma = "," if ki < len(entries) - 1 else ""
                out.write(f"    {json.dumps(key)}: "
                          f"{json.dumps(obj, separators=(',', ':'))}{comma}\n")
            out.write("  }")
        else:
            out.write("}")
        out.write(",\n" if si < len(sections) - 1 else "\n")
    out.write("}\n")


def classify(raw):
    """Map a raw id to (kind, seed_id): SCV -> scv (clinvar.submission: key), VCV/RCV as-is."""
    raw = raw.strip()
    if not raw or raw == "-":
        return None
    up = raw.upper()
    if up.startswith("CLINVAR.SUBMISSION:") or up.startswith("SCV"):
        return ("scv", raw if raw.lower().startswith("clinvar.submission:")
                else "clinvar.submission:" + raw)
    if up.startswith("VCV"):
        return ("vcv", raw)
    if up.startswith("RCV"):
        return ("rcv", raw)
    sys.stderr.write(f"  warning: cannot classify id '{raw}' (expected SCV/VCV/RCV)\n")
    return None


def resolve_submitter_scvs(dataset, project, submitter_ids):
    """Resolve submitter ids -> [(scv, key)] for every SCV whose contributions cite them."""
    refs = []
    for s in submitter_ids:
        s = s.strip().replace("'", "")
        key = s if s.startswith("clinvar.submitter:") else "clinvar.submitter:" + s
        refs.append("#/submitter/" + key)
    reflist = ", ".join("'" + r + "'" for r in refs)
    rows = bq_query(
        f"SELECT id AS k FROM `{dataset}.gkm_dict_scv` "
        f"WHERE EXISTS (SELECT 1 FROM UNNEST(contributions) c WHERE c.contributor IN ({reflist}))",
        project)
    return [("scv", row["k"]) for row in (rows or [])]


def read_ids(args):
    raw = [x for x in args.ids if x.strip() != "-"]
    want_stdin = args.stdin or any(x.strip() == "-" for x in args.ids)
    if args.ids_file:
        with open(args.ids_file) as fh:
            raw += [x for x in fh]
    if (want_stdin or (not raw and not args.ids_file)) and not sys.stdin.isatty():
        raw += [x for x in sys.stdin]
    seen, out = set(), []
    for r in raw:
        c = classify(r)
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", help="SCV/VCV/RCV ids (full statement key or bare accession)")
    ap.add_argument("--dataset", required=True, help="built release dataset, e.g. clinvar_2026_08_16_v2_5_0")
    ap.add_argument("--project", default="clingen-dev")
    ap.add_argument("--ids-file", help="file with one id per line")
    ap.add_argument("--stdin", action="store_true", help="also read ids from stdin")
    ap.add_argument("--submitter", action="append", default=[], metavar="ID",
                    help="include every SCV contributed by this submitter "
                         "(clinvar.submitter:{id} or bare {id}); repeatable")
    ap.add_argument("-o", "--out", help="output file (default: stdout)")
    args = ap.parse_args()

    wanted = read_ids(args)
    if not wanted and not args.submitter:
        ap.error("no ids given (pass SCV/VCV/RCV ids, --ids-file, --submitter, or stdin)")

    by_kind = {}
    for kind, seed_id in wanted:
        by_kind.setdefault(kind, []).append(seed_id)
    sys.stderr.write(f"Resolving {len(wanted)} id(s)"
                     + (f" + {len(args.submitter)} submitter(s)" if args.submitter else "")
                     + f" from {args.project}:{args.dataset} ...\n")

    seeds = []
    for kind, raws in by_kind.items():
        seeds += resolve_seeds(args.dataset, args.project, kind, raws)
    if args.submitter:
        seeds += resolve_submitter_scvs(args.dataset, args.project, args.submitter)
    seeds = list(dict.fromkeys(seeds))  # dedup (a submitter's SCV may also be named explicitly)
    if not seeds:
        sys.stderr.write("no matching statements found.\n")
        sys.exit(1)
    sys.stderr.write(f"  {len(seeds)} statement(s) matched; walking references ...\n")

    store = build_store(args.dataset, args.project, seeds)
    bundle = to_bundle(store)

    out = open(args.out, "w") if args.out else sys.stdout
    try:
        dump_bundle(bundle, out)
    finally:
        if args.out:
            out.close()
    counts = ", ".join(f"{s}={len(v)}" for s, v in bundle.items())
    sys.stderr.write(f"done. sections: {counts}\n")


if __name__ == "__main__":
    main()
