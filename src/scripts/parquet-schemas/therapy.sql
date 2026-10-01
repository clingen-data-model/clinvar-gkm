-- gkm_dict_therapy is a key/value JSON dict (key:STRING, value:JSON). Parquet cannot
-- export a JSON-typed column, so stringify value to deliver two STRING columns (key,value);
-- consumers parse `value` as JSON. The {DATASET}.gkm_dict_ reference is rewritten to
-- .delta_gkm_dict_ for delta exports by extract_parquet_typed, so it must appear only once.
SELECT key, TO_JSON_STRING(value) AS value
FROM {DATASET}.gkm_dict_therapy
