-- ============================================================================
-- dataset_diff_required — driver: diff the ClinVar tables the incremental build
-- actually consumes, between two snapshots
-- ============================================================================
-- Loops the ClinVar tables whose diffs drive an incremental changed-set (with
-- each table's natural key) and calls clinvar_ingest.dataset_diff for each,
-- producing <compare_schema>.diff_<table> (written into the compare/newer
-- snapshot's own dataset).
--
-- Scope note: only tables consumed by the gkm_* changed-set logic are listed.
-- ClinVar's pre-aggregated classification tables (variation_archive_classification,
-- rcv_accession_classification) and other unconsumed tables (scv_summary — read
-- directly cur-vs-base by gkm_scv_changed, not via a diff; clinical_assertion_
-- observation; submission) are intentionally excluded. (This also drops
-- variation_archive_classification, which lacked a release_date column and so
-- errored under the EXCEPT(release_date) diff.)
--
-- 'release_date' is ignored for every table (it changes on every snapshot).
--
-- Special cases baked into the map:
--   * trait_mapping — no stable per-row key AND may contain duplicates, so its
--     key_columns is empty (whole non-ignored row is the key) and use_distinct
--     is TRUE. Per spec its key is "all columns except release_date".
--
-- Usage:
--   CALL `clinvar_ingest.dataset_diff_required`(
--     'clinvar_2026_07_15_v2_5_0',   -- baseline (older)
--     'clinvar_2026_07_20_v2_5_0'    -- compare (newer)
--   );
-- ============================================================================

CREATE OR REPLACE PROCEDURE `clinvar_ingest.dataset_diff_required`(
  baseline_schema STRING,
  compare_schema  STRING
)
BEGIN
  DECLARE tables ARRAY<STRUCT<name STRING, keys ARRAY<STRING>, distinct_rows BOOL>>;
  DECLARE i INT64 DEFAULT 0;
  DECLARE t STRUCT<name STRING, keys ARRAY<STRING>, distinct_rows BOOL>;

  -- Only tables whose diff_<table> is consumed by the incremental changed-set
  -- logic (gkm_scv_changed, gkm_rcvvcv_changed, gkm_catvar, variation_identity).
  SET tables = [
    STRUCT('clinical_assertion'               AS name, ['id','version']            AS keys, FALSE AS distinct_rows),
    STRUCT('clinical_assertion_trait',             ['id'],                              FALSE),
    STRUCT('clinical_assertion_trait_set',         ['id'],                              FALSE),
    STRUCT('clinical_assertion_variation',         ['id'],                              FALSE),
    STRUCT('gene',                                 ['id'],                              FALSE),
    STRUCT('gene_association',                      ['gene_id','variation_id'],          FALSE),
    STRUCT('rcv_accession',                         ['id','version'],                    FALSE),
    STRUCT('rcv_mapping',                           ['rcv_accession'],                   FALSE),
    STRUCT('submitter',                             ['id'],                              FALSE),
    STRUCT('trait',                                 ['id'],                              FALSE),
    STRUCT('trait_mapping',                         CAST([] AS ARRAY<STRING>),           TRUE),
    STRUCT('trait_set',                             ['id'],                              FALSE),
    STRUCT('variation',                             ['id'],                              FALSE),
    STRUCT('variation_archive',                     ['id','version'],                    FALSE)
  ];

  WHILE i < ARRAY_LENGTH(tables) DO
    SET t = tables[OFFSET(i)];
    -- Isolate each table so a missing table or per-table error doesn't abort
    -- the whole run; the failure is surfaced but the loop continues.
    BEGIN
      CALL `clinvar_ingest.dataset_diff`(
        baseline_schema,
        compare_schema,
        t.name,
        t.keys,
        ['release_date'],
        t.distinct_rows
      );
    EXCEPTION WHEN ERROR THEN
      SELECT FORMAT('SKIPPED %s: %s', t.name, @@error.message) AS diff_warning;
    END;
    SET i = i + 1;
  END WHILE;
END;
