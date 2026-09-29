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
  collapse_ext_values(TO_JSON_STRING(value)) AS data
FROM (
  SELECT key, value FROM `{DATASET}.gkm_dict_proposition`
  UNION ALL SELECT key, value FROM `{DATASET}.gkm_dict_rcv_proposition`
  UNION ALL SELECT key, value FROM `{DATASET}.gkm_dict_vcv_proposition`
)
WHERE JSON_VALUE(value, '$.type') LIKE 'Clinvar%'
