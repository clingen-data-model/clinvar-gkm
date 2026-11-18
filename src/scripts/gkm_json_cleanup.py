"""Recursively drop null / empty-array / empty-object values from a decoded JSON
value, matching JSON_STRIP_NULLS(remove_empty => TRUE) for our data shapes.

Used by assemble-gkm-dicts.py so the published bundle (full + delta) has the same
cleanup gkm_json_proc used to apply. Publish-layer only — never touches BigQuery
tables, so it cannot affect delta/change-log/oracle correctness.

Rules:
  * dict: drop keys whose stripped value is None, {} or [].
  * list: strip each element's internals but KEEP elements (SQL arrays hold no NULL
    elements; dropping non-empty elements would change array length).
  * scalars: returned unchanged (0 / False / "" are preserved).

order_unordered_arrays writes the arrays in UNORDERED_ARRAYS in one canonical order, so a record whose list
comes back from the pipeline in a different order is still written with the same bytes.
"""
import json


def _is_empty(v):
    return v is None or (isinstance(v, (dict, list)) and len(v) == 0)


def strip_empty(value):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            sv = strip_empty(v)
            if not _is_empty(sv):
                out[k] = sv
        return out
    if isinstance(value, list):
        return [strip_empty(v) for v in value]
    return value


def collapse_ext_values(value):
    """Rename a typed extension value key (``value_<type>``) to the polymorphic
    ``value`` in every object that has a ``name`` sibling, at any depth.

    The pipeline stores extension values as value_string / value_boolean /
    value_submitted_condition / ... so gkm_json_proc can nullify-by-type and drop
    the unused variants; the va-spec Extension shape wants a single ``value``. This
    is the publish-layer parity of the BQ ``collapse_ext_values`` UDF and of
    scv.sql's Parquet ``data`` collapse — applied here so EVERY section (and every
    nested ``extensions`` array, e.g. classification.extensions) is collapsed, not
    just the handful the BQ NDJSON export reaches.

    Mutates ``value`` in place and returns it. Idempotent — a record with no
    ``value_*`` keys is unchanged — so it is safe over sections the BQ export has
    already collapsed. Run AFTER strip_empty so any null ``value_*`` is gone and a
    single populated variant remains.
    """
    if isinstance(value, dict):
        if "name" in value:
            for k in list(value.keys()):
                if k.startswith("value_"):
                    value["value"] = value.pop(k)
        for v in value.values():
            collapse_ext_values(v)
    elif isinstance(value, list):
        for v in value:
            collapse_ext_values(v)
    return value


# Arrays written in a canonical order, by section, as paths from the record's root ("a" is the record's "a" array;
# "a[].b" is the "b" array of every element of "a"). An array belongs here only when
#   * every schema that defines it marks it `ordered: false`, so its order carries no meaning
#     (tests/test_gkm_json_cleanup.py checks this against schema/), and
#   * the pipeline was seen to write it in a different order in different releases for the same record.
# Never add an array that a schema marks `ordered: true`.
UNORDERED_ARRAYS = {
    # gkm-core Entity.aliases: the trait's alternate names, taken as-is from clinvar-ingest's trait.alternate_names
    # (gkm-scv-condition-proc.sql). Between the 2026-10 monthly full and the 2026-10-18 weekly full, 1,513 conditions
    # differed only in the order of their aliases.
    "condition": ("aliases",),
}


def canonical_text(value):
    """The sort key of an array element: its compact JSON text with keys sorted."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _order(node, steps):
    if not steps or not isinstance(node, dict) or steps[0].rstrip("[]") not in node:
        return
    name = steps[0].rstrip("[]")
    if len(steps) == 1:
        if isinstance(node[name], list):
            node[name].sort(key=canonical_text)
    elif isinstance(node[name], list):
        for item in node[name]:
            _order(item, steps[1:])
    else:
        _order(node[name], steps[1:])


def order_unordered_arrays(section, value):
    """Sort the arrays UNORDERED_ARRAYS lists for ``section`` by their elements' canonical_text.

    Mutates ``value`` in place and returns it. Elements are never added, dropped or changed, only reordered; equal
    elements have the same text, so the result does not depend on the input order."""
    for path in UNORDERED_ARRAYS.get(section, ()):
        _order(value, path.split("."))
    return value
