SELECT * EXCEPT(hasEvidenceItems),
  ARRAY(SELECT REGEXP_REPLACE(el, r'^#/[^/]+/', '') FROM UNNEST(hasEvidenceItems) AS el) AS evidence_items,
  collapse_ext_values(TO_JSON_STRING(JSON_STRIP_NULLS(TO_JSON((SELECT AS STRUCT t.*)), remove_empty => TRUE))) AS data
FROM {DATASET}.gkm_dict_rcv_evidence_line t
