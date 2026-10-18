SELECT
  key AS id,
  JSON_VALUE(value, '$.type') AS type,
  JSON_VALUE(value, '$.digest') AS digest,
  CAST(JSON_VALUE(value, '$.start') AS INT64) AS loc_start,
  CAST(JSON_VALUE(value, '$.end') AS INT64) AS loc_end,
  REGEXP_REPLACE(JSON_VALUE(value, '$.sequenceReference'), r'^#/[^/]+/', '') AS sequence_reference_id,
  bundle_cleanup(TO_JSON_STRING(value)) AS data,  -- = the bundle record (assembler strip_empty + value_* collapse)
  COALESCE(CAST(JSON_VALUE(value, '$.start') AS INT64), CAST(JSON_VALUE(value, '$.start[0]') AS INT64)) AS loc_start_min,
  COALESCE(CAST(JSON_VALUE(value, '$.start') AS INT64), CAST(JSON_VALUE(value, '$.start[1]') AS INT64)) AS loc_start_max,
  COALESCE(CAST(JSON_VALUE(value, '$.end') AS INT64), CAST(JSON_VALUE(value, '$.end[0]') AS INT64)) AS loc_end_min,
  COALESCE(CAST(JSON_VALUE(value, '$.end') AS INT64), CAST(JSON_VALUE(value, '$.end[1]') AS INT64)) AS loc_end_max
FROM {DATASET}.gkm_dict_location
