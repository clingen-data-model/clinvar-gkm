SELECT * EXCEPT(concepts),
  ARRAY(SELECT REGEXP_REPLACE(el, r'^#/[^/]+/', '') FROM UNNEST(concepts) AS el) AS concepts,
  -- Null-stripped like the bundle record (an absent conceptSetType is omitted, not "conceptSetType": null).
  collapse_ext_values(TO_JSON_STRING(JSON_STRIP_NULLS(TO_JSON((SELECT AS STRUCT t.*)), remove_empty => TRUE))) AS data
FROM {DATASET}.gkm_dict_condition_set t
-- Drop single-member sets: a ConceptSet of one concept is just that condition — every
-- producer references the lone member directly as #/condition/, never the set — and it
-- violates the va-spec ConditionSet minItems:2. Reference-integrity verified: 0 of
-- ~2.96M proposition.object refs point to a <=1-concept set. Mirrors the NDJSON filter.
WHERE ARRAY_LENGTH(t.concepts) > 1
