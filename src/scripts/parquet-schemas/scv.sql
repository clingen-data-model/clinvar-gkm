SELECT * EXCEPT(proposition, hasEvidenceLines, contributions) REPLACE(
  -- extensions: the dict table stores non-NULL structs of nulls (the unused value_<type> variants and
  -- placeholder concepts[]/xrefs[] elements). The bundle drops them (JSON_STRIP_NULLS remove_empty in the
  -- NDJSON export), so rebuild the typed column to match the bundle: an all-null struct becomes NULL and an
  -- all-null array element is dropped, at every depth. `.* REPLACE` keeps the column's fields, order and types.
  ARRAY(
    SELECT AS STRUCT e.* REPLACE(
      IF(is_blank(e.value_submitted_condition_set), NULL, (
        SELECT AS STRUCT e.value_submitted_condition_set.* REPLACE(
          ARRAY(
            SELECT AS STRUCT c.* REPLACE(
              ARRAY(SELECT x FROM UNNEST(c.xrefs) AS x WITH OFFSET xo WHERE NOT is_blank(x) ORDER BY xo) AS xrefs,
              IF(is_blank(c.original_medgen_match), NULL, c.original_medgen_match) AS original_medgen_match,
              IF(is_blank(c.mapping), NULL, c.mapping) AS mapping)
            FROM UNNEST(e.value_submitted_condition_set.concepts) AS c WITH OFFSET co
            WHERE NOT is_blank(c) ORDER BY co
          ) AS concepts))) AS value_submitted_condition_set,
      IF(is_blank(e.value_submitted_condition), NULL, (
        SELECT AS STRUCT e.value_submitted_condition.* REPLACE(
          ARRAY(SELECT x FROM UNNEST(e.value_submitted_condition.xrefs) AS x WITH OFFSET xo
                WHERE NOT is_blank(x) ORDER BY xo) AS xrefs,
          IF(is_blank(e.value_submitted_condition.original_medgen_match), NULL,
             e.value_submitted_condition.original_medgen_match) AS original_medgen_match,
          IF(is_blank(e.value_submitted_condition.mapping), NULL,
             e.value_submitted_condition.mapping) AS mapping))) AS value_submitted_condition)
    FROM UNNEST(t.extensions) AS e WITH OFFSET eo
    WHERE NOT is_blank(e) ORDER BY eo
  ) AS extensions),
  REGEXP_REPLACE(proposition, r'^#/[^/]+/', '') AS proposition_id,
  ARRAY(
    SELECT AS STRUCT c.type, REGEXP_REPLACE(c.contributor, r'^#/[^/]+/', '') AS contributor, c.date, c.activityType
    FROM UNNEST(contributions) AS c
  ) AS contributions,
  ARRAY(SELECT REGEXP_REPLACE(el, r'^#/[^/]+/', '') FROM UNNEST(hasEvidenceLines) AS el) AS has_evidence_lines,
  collapse_ext_values(TO_JSON_STRING(JSON_STRIP_NULLS(TO_JSON((SELECT AS STRUCT t.*)), remove_empty => TRUE))) AS data
FROM {DATASET}.gkm_dict_scv t
