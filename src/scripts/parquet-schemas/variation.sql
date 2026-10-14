SELECT * EXCEPT(constraints, members),
  ARRAY(SELECT REGEXP_REPLACE(m, r'^#/[^/]+/', '') FROM UNNEST(members) AS m) AS members,
  ARRAY(
    SELECT AS STRUCT
      c.type,
      REGEXP_REPLACE(c.allele, r'^#/[^/]+/', '') AS allele,
      REGEXP_REPLACE(c.location, r'^#/[^/]+/', '') AS location,
      c.copies, c.copyChange, c.matchCharacteristic, c.relations
    FROM UNNEST(constraints) AS c
  ) AS constraints,
  collapse_ext_values(TO_JSON_STRING(JSON_STRIP_NULLS(TO_JSON((SELECT AS STRUCT t.*)), remove_empty => TRUE))) AS data
FROM {DATASET}.gkm_dict_variation t
