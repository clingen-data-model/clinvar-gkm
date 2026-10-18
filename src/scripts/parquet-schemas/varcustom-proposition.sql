-- G4 variant×condition custom propositions: the 10 Clinvar* CustomProposition types (specific type in
-- customPropositionType). Unions the SCV/RCV/VCV proposition dicts, filtered to the varcustom delivery
-- group. subject → object; generic qualifiers[] name/value array (SCV only — null for RCV/VCV rows).
SELECT
  key AS id,
  JSON_VALUE(value, '$.type') AS type,
  JSON_VALUE(value, '$.predicate') AS predicate,
  REGEXP_REPLACE(JSON_VALUE(value, '$.subject'), r'^#/[^/]+/', '') AS subject_id,
  REGEXP_REPLACE(JSON_VALUE(value, '$.object'), r'^#/[^/]+/', '') AS object_id,
  JSON_VALUE(value, '$.geneContextQualifier.name') AS gene_context_name,
  JSON_VALUE(value, '$.modeOfInheritanceQualifier.name') AS mode_of_inheritance,
  JSON_VALUE(value, '$.penetranceQualifier.name') AS penetrance,
  bundle_cleanup(TO_JSON_STRING(value)) AS data,  -- = the bundle record (assembler strip_empty + value_* collapse)
  -- Appended after `data` (additive; existing column positions unchanged). The gene-context qualifier is
  -- SCV-only and variant-derived (one representative gene per variant, chosen upstream), NOT
  -- submitter-asserted. gene_context_id is the qualifier's own primaryCoding.code as a bare `ncbigene:` id
  -- (joins gene.parquet `id`); NULL when there is no coding (incl. the "submitted genes were not
  -- normalized" placeholder). Never derived from a symbol.
  IF(JSON_VALUE(value, '$.geneContextQualifier.primaryCoding.code') IS NULL, NULL,
     CONCAT('ncbigene:', JSON_VALUE(value, '$.geneContextQualifier.primaryCoding.code'))) AS gene_context_id,
  -- The submitter's own gene symbols, verbatim and in order, from the qualifier extension picked by name.
  ARRAY(
    SELECT JSON_VALUE(sym)
    FROM UNNEST(JSON_QUERY_ARRAY(value, '$.geneContextQualifier.extensions')) AS ext,
         UNNEST(JSON_QUERY_ARRAY(ext, '$.value_string')) AS sym WITH OFFSET so
    WHERE JSON_VALUE(ext, '$.name') = 'submittedGeneSymbols'
    ORDER BY so
  ) AS submitted_gene_symbols
FROM (
  SELECT key, value FROM `{DATASET}.gkm_dict_proposition`
  UNION ALL SELECT key, value FROM `{DATASET}.gkm_dict_rcv_proposition`
  UNION ALL SELECT key, value FROM `{DATASET}.gkm_dict_vcv_proposition`
)
WHERE JSON_VALUE(value, '$.type') LIKE 'Clinvar%'
