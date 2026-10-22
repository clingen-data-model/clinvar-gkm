SELECT
  key AS id,
  JSON_VALUE(value, '$.type') AS type,
  JSON_VALUE(value, '$.refgetAccession') AS refget_accession,
  JSON_VALUE(value, '$.name') AS name,
  JSON_VALUE(value, '$.moleculeType') AS molecule_type,
  JSON_VALUE(value, '$.residueAlphabet') AS residue_alphabet,
  bundle_cleanup(TO_JSON_STRING(value)) AS data  -- = the bundle record (assembler strip_empty + value_* collapse)
FROM {DATASET}.gkm_dict_sequence_reference
