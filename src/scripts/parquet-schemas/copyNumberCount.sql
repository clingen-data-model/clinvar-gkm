SELECT
  key AS id,
  JSON_VALUE(value, '$.type') AS type,
  JSON_VALUE(value, '$.digest') AS digest,
  CAST(JSON_VALUE(value, '$.copies') AS INT64) AS copies,
  REGEXP_REPLACE(JSON_VALUE(value, '$.location'), r'^#/[^/]+/', '') AS location_id,
  bundle_cleanup(TO_JSON_STRING(value)) AS data  -- = the bundle record (assembler strip_empty + value_* collapse)
FROM {DATASET}.gkm_dict_copy_number_count
