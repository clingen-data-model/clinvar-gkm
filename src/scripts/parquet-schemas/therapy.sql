-- gkm_dict_therapy is a key/value JSON dict (key:STRING, value:JSON). Parquet cannot
-- export a JSON-typed column, so stringify value to deliver two STRING columns (key,value);
-- consumers parse `value` as JSON. Typed columns are appended after key/value (additive:
-- key/value keep their names and order): `name` and `concept_type` (value.conceptType).
-- The {DATASET}.gkm_dict_ reference is rewritten to .delta_gkm_dict_ for delta exports by
-- extract_parquet_typed, so it must appear only once.
SELECT key, TO_JSON_STRING(value) AS value,
  JSON_VALUE(value, '$.name') AS name,
  JSON_VALUE(value, '$.conceptType') AS concept_type
FROM {DATASET}.gkm_dict_therapy
