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
"""


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
