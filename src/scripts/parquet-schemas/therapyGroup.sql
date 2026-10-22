-- gkm_dict_therapygroup is a key/value JSON dict (key:STRING, value:JSON). Parquet cannot
-- export a JSON-typed column, so stringify value to deliver two STRING columns (key,value);
-- consumers parse `value` as JSON. Typed columns are appended after key/value (additive:
-- key/value keep their names and order): `membership_operator` (value.membershipOperator)
-- and `members` (ARRAY<STRING> of bare therapy ids, in value.concepts order, with the
-- '#/therapy/' pointer prefix stripped). The {DATASET}.gkm_dict_ reference is rewritten to
-- .delta_gkm_dict_ for delta exports by extract_parquet_typed, so it must appear only once.
SELECT key, bundle_cleanup(TO_JSON_STRING(value)) AS value,  -- = the bundle record (assembler cleanup)
  JSON_VALUE(value, '$.membershipOperator') AS membership_operator,
  ARRAY(
    SELECT REGEXP_REPLACE(c, r'^#/[^/]+/', '')
    FROM UNNEST(JSON_VALUE_ARRAY(value, '$.concepts')) AS c WITH OFFSET AS o
    ORDER BY o
  ) AS members
FROM {DATASET}.gkm_dict_therapygroup
