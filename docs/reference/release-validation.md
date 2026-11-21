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
| **Strict schema validation** | `validate-bundle.sh`, with [jsonschema-rs](https://pypi.org/project/jsonschema-rs/) and a registry holding the repo's `schema/` tree (the ClinVar-GKM schemas and the GA4GH schemas they reference), validates every record of the real staged bundle, verbatim, against the bundle schema (Draft 2020-12). A failure stops the release before upload | Every full bundle and every delta (from 1.2.0; see below) |
| **Official toolkit cross-check** | The official GA4GH gkm-toolkit's `validate_bundle_schema` (`ga4gh.gkm` 0.4.0, python-jsonschema) validates a stratified 1% sample of the line's first full bundle (`sample-bundle.py`: at least 3,000 records of every section, spread over the section, copied verbatim). The tests also require both engines to name the same failing records in bundles with planted violations, including inside the layered `variation`, `vcv` and `scv` profiles | Each version release |
| **Structural check** | `schema_version`, section order, one well-formed record per line, and per-section record counts equal to the BigQuery tables | Every other full bundle |
| **No null or empty values** | No field anywhere carries `null`, `""`, `[]` or `{}`, except the null bound of a VRS `Range`, which VRS uses for an open-ended coordinate | Every staged bundle |
| **Bundle ↔ Parquet** | Per-section record counts, ids in both directions, and a sampled comparison of each row's `data` with the bundle record | The Parquet dataset against the full bundle of the release it was built from |

**1.1.0: the official toolkit on every record.** In 1.1.0 the gkm-toolkit validated the 2026-06-27 full and
the 16 deltas. Each later full bundle equals the first full plus the deltas after it, which the
delta-reconstruction gate proves, so those 17 files contain every distinct record that 1.1.0 publishes. The other
fulls got the structural check.

**From 1.2.0: jsonschema-rs on every record of every bundle.** `run-release.sh` builds each release's delta and
weekly full and validates every record of both with `validate-bundle.sh` before anything is uploaded; a failure
stops the release. The engine is jsonschema-rs: the same bundle schema, registry and per-record documents as the
toolkit, and the same Draft 2020-12 check (the toolkit's `validate_bundle_schema` adds no checks of its own). It
takes about 15 minutes on a full bundle. The toolkit takes about 17 hours on 64 cores for a 1.2.0 full, about
3.6 times as long as for 1.1.0: the 1.2.0 profiles close each ClinVar record type with `unevaluatedProperties`
over layered `allOf`/`$ref` schemas (71 uses, against 27 in 1.1.0), and python-jsonschema re-evaluates every
layer to apply it, where jsonschema-rs does not. So the toolkit now cross-checks a sample at each version release
(see the table), and the engine tests require both engines to fail the same records.

---

## 1.1.0 Results

1.1.0 rebuilt 17 BigQuery datasets, 2026-06-27 through 2026-10-18, and staged 4 monthly full bundles, 3 weekly
full bundles, 16 deltas and one Parquet dataset built from 2026-10-18.

| Gate | Result |
| --- | --- |
| Proposition structure and reference integrity | **PASS** on 17/17 datasets |
| Expected difference | **PASS** on 16/16 datasets: every difference attributed to a shipped fix |
| Delta reconstruction | **PASS** on 16/16 pairs, `0,0,0` (no missing, extra or differing rows) on all 21 tables, including the cross-version pair 2026-08-22 → 2026-08-29 |
| Strict GA4GH validation | **PASS**, `failing: 0`: the 2026-06-27 full (86,810,319 records), all 16 deltas and the 2026-10-18 weekly full (91,491,982 records), every section |
| Structural check | **PASS** on the other 5 full bundles (2026-08-04, 2026-08-29, 2026-09-28, 2026-10-04, 2026-10-11): `schema_version` 1.1.0, section order, well-formed records, and per-section counts equal to BigQuery |
| No null or empty values | **PASS** on all 4 monthly and 3 weekly full bundles and the 16 deltas |
| Bundle ↔ Parquet | **PASS** for 2026-10-18: all 20 sections have equal counts and ids (0 in the bundle only, 0 in Parquet only); 183,368 sampled records' `data` equal |


### Verification reports

The strict GA4GH validation of the published files produces a stamped report for each file. Each report records:

- the UTC run time;
- the tool and schema versions;
- the file's published URL and the sha256 of the bytes validated, checked against the published `.sha256`;
- per section, the records and failures and the schema those records are validated against;
- every check, and any warnings.

The 1.1.0 reports are attached to the [1.1.0 GitHub Release](https://github.com/clingen-data-model/clinvar-gkm/releases/tag/1.1.0):

| File | Result | Report |
| --- | --- | --- |
| `weekly/clinvar-gkm_2026-1018.json.gz` (the newest full bundle) | **PASS**: 91,491,982 records in 20 sections, 0 failing | [Markdown](https://github.com/clingen-data-model/clinvar-gkm/releases/download/1.1.0/clinvar-gkm_2026-1018.validation.md) · [JSON](https://github.com/clingen-data-model/clinvar-gkm/releases/download/1.1.0/clinvar-gkm_2026-1018.validation.json) |
| `deltas/clinvar-gkm-delta_2026-1018.json.gz` | **PASS**: 215,170 records in 15 sections, 0 failing | [Markdown](https://github.com/clingen-data-model/clinvar-gkm/releases/download/1.1.0/clinvar-gkm-delta_2026-1018.validation.md) · [JSON](https://github.com/clingen-data-model/clinvar-gkm/releases/download/1.1.0/clinvar-gkm-delta_2026-1018.validation.json) |

Reports for the other full bundles and deltas will be added as they are produced. The report option is being
contributed to the GA4GH GKM Toolkit ([ga4gh/gkm-starter-kit#128](https://github.com/ga4gh/gkm-starter-kit/pull/128)).
