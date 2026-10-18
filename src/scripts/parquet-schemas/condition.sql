-- condition was exported untyped (bq extract), so it alone lacked the `data` column. Keep the
-- original columns, names and order (camelCase: renaming them would break consumers) and add `data`.
SELECT t.*,
  collapse_ext_values(TO_JSON_STRING(JSON_STRIP_NULLS(TO_JSON((SELECT AS STRUCT t.*)), remove_empty => TRUE))) AS data
FROM {DATASET}.gkm_dict_condition t
