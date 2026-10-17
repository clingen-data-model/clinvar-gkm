SELECT * EXCEPT(constraints, members) REPLACE (
    -- typed FK columns carry bare ids: strip the #/gene/ pointer from each gene-list entry,
    -- keeping extension and entry order, and leaving non-gene-list extensions untouched
    ARRAY(
      SELECT AS STRUCT e.* REPLACE (
        IF(e.value_gene_array IS NULL, NULL, ARRAY(
          SELECT AS STRUCT g.* REPLACE (REGEXP_REPLACE(g.gene, r'^#/[^/]+/', '') AS gene)
          FROM UNNEST(e.value_gene_array) AS g WITH OFFSET go ORDER BY go
        )) AS value_gene_array)
      FROM UNNEST(extensions) AS e WITH OFFSET eo ORDER BY eo
    ) AS extensions
  ),
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
