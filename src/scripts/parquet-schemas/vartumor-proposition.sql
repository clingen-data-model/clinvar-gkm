-- G2 variant×tumorType standard propositions: VariantOncogenicity. Unions the SCV/RCV/VCV proposition
-- dicts, filtered to the vartumor delivery group. subjectVariant → objectTumorType.
SELECT
  key AS id,
  JSON_VALUE(value, '$.type') AS type,
  JSON_VALUE(value, '$.predicate') AS predicate,
  REGEXP_REPLACE(JSON_VALUE(value, '$.subject'), r'^#/[^/]+/', '') AS subject_variant_id,
  REGEXP_REPLACE(JSON_VALUE(value, '$.object'), r'^#/[^/]+/', '') AS object_tumor_type_id,
  JSON_VALUE(value, '$.geneContextQualifier.name') AS gene_context_name,
  collapse_ext_values(TO_JSON_STRING(value)) AS data
FROM (
  SELECT key, value FROM `{DATASET}.gkm_dict_proposition`
  UNION ALL SELECT key, value FROM `{DATASET}.gkm_dict_rcv_proposition`
  UNION ALL SELECT key, value FROM `{DATASET}.gkm_dict_vcv_proposition`
)
WHERE JSON_VALUE(value, '$.type') = 'VariantOncogenicityProposition'
