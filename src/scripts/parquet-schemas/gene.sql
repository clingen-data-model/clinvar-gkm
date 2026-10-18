SELECT
  key AS id,
  JSON_VALUE(value, '$.conceptType') AS concept_type,
  JSON_VALUE(value, '$.name') AS name,
  bundle_cleanup(TO_JSON_STRING(value)) AS data  -- = the bundle record (assembler strip_empty + value_* collapse)
FROM {DATASET}.gkm_dict_gene
