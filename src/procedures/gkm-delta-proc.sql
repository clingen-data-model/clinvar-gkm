-- ============================================================================
-- gkm_delta_build — materialize per-table delta payloads from gkm_change_log
-- ============================================================================
-- For each tracked table, writes {S}.delta_<table> = the FULL current rows whose pk
-- is A or U in {S}.gkm_change_log (same schema as the target table — a consumer
-- upserts it by pk directly). D tombstones are NOT payload rows; they live in the
-- manifest (gkm_change_log) only. Requires gkm_change_log to have been built first.
--
-- `tables` mirrors the catvar+scv+rcv/vcv-output subset of gkm_change_log's `tracked`
-- array (name + pk expression). Keep in sync. The rcv/vcv `_agg` intermediates are
-- intentionally excluded (same as gkm_change_log): only the published dict/proposition/
-- evidence_line outputs get delta payloads.
-- ============================================================================
CREATE OR REPLACE PROCEDURE `clinvar_ingest.gkm_delta_build`(on_date DATE)
BEGIN
  DECLARE tables ARRAY<STRUCT<name STRING, pk STRING>> DEFAULT [
    STRUCT('gkm_dict_variation'          AS name, 'id' AS pk),
    STRUCT('gkm_dict_sequence_reference',     'key'),
    STRUCT('gkm_dict_location',               'key'),
    STRUCT('gkm_dict_allele',                 'key'),
    STRUCT('gkm_dict_copy_number_count',      'key'),
    STRUCT('gkm_dict_copy_number_change',     'key'),
    STRUCT('gkm_dict_gene',                   'key'),
    -- scv condition/statement outputs (Plan 2)
    STRUCT('gkm_dict_condition',              'id'),
    STRUCT('gkm_dict_condition_set',          'id'),
    STRUCT('gkm_scv_condition_sets',          'scv_id'),
    STRUCT('gkm_dict_submitter',              'key'),
    STRUCT('gkm_dict_proposition',            'key'),
    STRUCT('gkm_dict_evidence_line',          'id'),
    STRUCT('gkm_dict_scv',                    'id'),
    -- rcv/vcv statement outputs (Plan 3)
    STRUCT('gkm_dict_rcv',                    'id'),
    STRUCT('gkm_dict_rcv_proposition',        'key'),
    STRUCT('gkm_dict_rcv_evidence_line',      'id'),
    STRUCT('gkm_dict_vcv',                    'id'),
    STRUCT('gkm_dict_vcv_proposition',        'key'),
    STRUCT('gkm_dict_vcv_evidence_line',      'id')
  ];
  DECLARE i INT64 DEFAULT 0;
  DECLARE t STRUCT<name STRING, pk STRING>;
  DECLARE q STRING;

  FOR rec IN (SELECT s.schema_name FROM `clinvar_ingest.schema_on`(on_date) AS s)
  DO
    SET i = 0;
    WHILE i < ARRAY_LENGTH(tables) DO
      SET t = tables[OFFSET(i)];
      SET i = i + 1;
      SET q = """
        CREATE OR REPLACE TABLE `{S}.delta_{T}` AS
        SELECT src.*
        FROM `{S}.{T}` src
        WHERE CAST({PK} AS STRING) IN (
          SELECT pk FROM `{S}.gkm_change_log`
          WHERE table_name = '{T}' AND change_type IN ('A','U')
        )
      """;
      SET q = REPLACE(q, '{PK}', t.pk);
      SET q = REPLACE(q, '{T}', t.name);
      SET q = REPLACE(q, '{S}', rec.schema_name);
      EXECUTE IMMEDIATE q;
    END WHILE;
  END FOR;
END;
