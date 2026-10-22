# Release Validation

Every release is gated before any file is published. The gates check the BigQuery tables the bundles are
exported from, the real staged bundles themselves, and the Parquet dataset derived from them. A release is
published only when every gate passes. This page lists the gates and the results for 1.1.0.

The step-by-step procedure, with the exact commands and the expected output of each gate, is the
[1.1.0 rebuild runbook](https://github.com/clingen-data-model/clinvar-gkm/blob/main/docs/superpowers/plans/2026-10-20-1.1.0-rebuild-runbook.md).
The changes these gates verified are listed in the [1.1.0 changelog](changelog.md#110).

---

## Gates

| Gate | What it checks | Scope |
| --- | --- | --- |
| **Proposition structure and reference integrity** | `validate-proposition-conformance.sh`: every proposition has the structure its type requires, and every statement and evidence-line pointer names the section its proposition is in — no old-section, unparsed, dangling, misrouted or bare reference | Every dataset |
| **Expected difference** | Every row that differs from a snapshot taken before the rebuild is joined on its primary key and classified; each class of change must be attributed to a fix shipped in the release | Every dataset that existed before the rebuild |
| **Delta reconstruction** | `oracle-delta-reconstruction.sh`: the baseline release minus the delta's deletes plus the delta's records equals the next release, compared on all 21 bundle tables | Every consecutive pair of releases |
| **Strict GA4GH validation** | The official GA4GH gkm-toolkit (`ga4gh.gkm` 0.4.0), in strict mode, validates every record of the real staged bundle, verbatim, against the `schema/` tree | The first full bundle and every delta (see below) |
| **Structural check** | `schema_version`, section order, one well-formed record per line, and per-section record counts equal to the BigQuery tables | Every other full bundle |
| **No null or empty values** | No field anywhere carries `null`, `""`, `[]` or `{}`, except the null bound of a VRS `Range`, which VRS uses for an open-ended coordinate | Every staged bundle |
| **Bundle ↔ Parquet** | Per-section record counts, ids in both directions, and a sampled comparison of each row's `data` with the bundle record | The Parquet dataset against the full bundle of the release it was built from |

**Why the strict scope covers every record.** Each later full bundle equals the first full plus the deltas
after it, which the delta-reconstruction gate proves. The 2026-06-27 full and the 16 deltas therefore
together contain every distinct record of every 1.1.0 bundle, so strict validation of those 17 files
validates every record that 1.1.0 publishes. The other fulls get the structural check.

---

## 1.1.0 Results

1.1.0 rebuilt 17 BigQuery datasets, 2026-06-27 through 2026-10-18, and staged 4 monthly full bundles, 3 weekly
full bundles, 16 deltas and one Parquet dataset built from 2026-10-18.

| Gate | Result |
| --- | --- |
| Proposition structure and reference integrity | **PASS** on 17/17 datasets |
| Expected difference | **PASS** on 16/16 datasets: every difference attributed to a shipped fix |
| Delta reconstruction | **PASS** on 16/16 pairs, `0,0,0` (no missing, extra or differing rows) on all 21 tables, including the cross-version pair 2026-08-22 → 2026-08-29 |
| No null or empty values | **PASS** on the 4 monthly full bundles and the 16 deltas |

<!-- pending: Strict GA4GH validation of the 2026-06-27 full, the 16 deltas and the 2026-10-18 weekly full — add the results at publication -->
<!-- pending: No null or empty values on the 3 weekly fulls — add at publication -->
<!-- pending: Structural check of the other fulls — add the result at publication -->
<!-- pending: Bundle ↔ Parquet (2026-10-18) — add the result at publication -->

!!! note "Pending at publication"
    These results are added when 1.1.0 is published:

    - Strict GA4GH validation of the 2026-06-27 full, the 16 deltas and the 2026-10-18 weekly full
    - No null or empty values on the 3 weekly full bundles
    - Structural check of the other full bundles
    - Bundle ↔ Parquet for the Parquet dataset built from 2026-10-18
