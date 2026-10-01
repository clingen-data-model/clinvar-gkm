SELECT * EXCEPT(hasEvidenceItems),
  ARRAY(SELECT REGEXP_REPLACE(el, r'^#/[^/]+/', '') FROM UNNEST(hasEvidenceItems) AS el) AS evidence_items,
  TO_JSON_STRING((SELECT AS STRUCT t.*)) AS data
FROM {DATASET}.gkm_dict_vcv_evidence_line t
