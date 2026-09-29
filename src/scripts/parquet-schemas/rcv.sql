SELECT * EXCEPT(proposition, hasEvidenceLines),
  REGEXP_REPLACE(proposition, r'^#/[^/]+/', '') AS proposition_id,
  ARRAY(SELECT REGEXP_REPLACE(el, r'^#/[^/]+/', '') FROM UNNEST(hasEvidenceLines) AS el) AS has_evidence_lines,
  TO_JSON_STRING(JSON_STRIP_NULLS(TO_JSON((SELECT AS STRUCT t.*)), remove_empty => TRUE)) AS data
FROM {DATASET}.gkm_dict_rcv t
