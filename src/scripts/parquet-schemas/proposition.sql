-- One shared column schema for all four proposition sections (1.1.0): propositionPathogenicity,
-- propositionOncogenicity, propositionSomaticClinicalImpact, propositionClinvarCustom. export-gkm-dicts.sh
-- substitutes {SECTION} once per section, so read_parquet('proposition*.parquet') unions the four with no
-- renaming. Unions the SCV/RCV/VCV proposition dicts. Every column derives from the bundle record; a column
-- that does not apply to a row is NULL (submitted_gene_symbols: an empty array).
-- The WHERE calls the canonical section function, which raises on an unmapped type: an unknown type fails
-- the export (as in the NDJSON export) instead of being dropped from every table.
SELECT
  key AS id,
  JSON_VALUE(value, '$.type') AS type,
  JSON_VALUE(value, '$.predicate') AS predicate,
  REGEXP_REPLACE(JSON_VALUE(value, '$.subject'), r'^#/[^/]+/', '') AS subject_variant_id,
  REGEXP_REPLACE(JSON_VALUE(value, '$.object'), r'^#/[^/]+/', '') AS object_id,
  -- The section the object pointer names: condition | conditionSet | therapy | therapyGroup. Every object is
  -- a '#/' pointer (uniform references, #160), so anything else (a bare id, an inline object) fails loudly.
  CASE
    WHEN JSON_QUERY(value, '$.object') IS NULL THEN NULL
    WHEN STARTS_WITH(JSON_VALUE(value, '$.object'), '#/')
      THEN REGEXP_EXTRACT(JSON_VALUE(value, '$.object'), r'^#/([^/]+)/')
    ELSE ERROR(FORMAT('proposition %t: object is not a #/ pointer: %t', key, TO_JSON_STRING(JSON_QUERY(value, '$.object'))))
  END AS object_type,
  -- TherapeuticResponse only (the tumor type the response is for).
  REGEXP_REPLACE(JSON_VALUE(value, '$.conditionQualifier'), r'^#/[^/]+/', '') AS condition_qualifier_id,
  -- Gene context (SCV only; NULL on RCV/VCV rows). gene_context_id is the qualifier's own
  -- primaryCoding.code as a bare `ncbigene:` id (joins gene.parquet `id`); NULL when there is no coding
  -- (incl. the not-normalized placeholder, whose name is the submitter's symbol). Never derived from a symbol.
  IF(JSON_VALUE(value, '$.geneContextQualifier.primaryCoding.code') IS NULL, NULL,
     CONCAT('ncbigene:', JSON_VALUE(value, '$.geneContextQualifier.primaryCoding.code'))) AS gene_context_id,
  JSON_VALUE(value, '$.geneContextQualifier.name') AS gene_context_name,
  -- The submitter's own gene symbols, verbatim and in order, from the qualifier extension picked by name.
  ARRAY(
    SELECT JSON_VALUE(sym)
    FROM UNNEST(JSON_QUERY_ARRAY(value, '$.geneContextQualifier.extensions')) AS ext,
         UNNEST(JSON_QUERY_ARRAY(ext, '$.value_string')) AS sym WITH OFFSET so
    WHERE JSON_VALUE(ext, '$.name') = 'submittedGeneSymbols'
    ORDER BY so
  ) AS submitted_gene_symbols,
  -- Where the qualifier's gene came from, from the `geneContextSource` extension picked by name:
  -- submittedSymbolMatches | submittedSymbolDiffers | inferredFromVariant | submittedNotNormalized.
  (
    SELECT JSON_VALUE(ext, '$.value_enum')
    FROM UNNEST(JSON_QUERY_ARRAY(value, '$.geneContextQualifier.extensions')) AS ext
    WHERE JSON_VALUE(ext, '$.name') = 'geneContextSource'
  ) AS gene_context_source,
  -- Germline SCV qualifiers.
  JSON_VALUE(value, '$.modeOfInheritanceQualifier.name') AS mode_of_inheritance,
  JSON_VALUE(value, '$.penetranceQualifier.name') AS penetrance,
  bundle_cleanup(TO_JSON_STRING(value)) AS data  -- = the bundle record (assembler strip_empty + value_* collapse)
FROM (
  SELECT key, value FROM `{DATASET}.gkm_dict_proposition`
  UNION ALL SELECT key, value FROM `{DATASET}.gkm_dict_rcv_proposition`
  UNION ALL SELECT key, value FROM `{DATASET}.gkm_dict_vcv_proposition`
)
WHERE `clinvar_ingest.gkm_proposition_section`(JSON_VALUE(value, '$.type')) = '{SECTION}'
