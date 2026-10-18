# Final Statements (Step 7)

## Overview

Step 7 of `gkm_scv_statement_proc` performs the final assembly of complete VA-Spec Statement records into `gkm_dict_scv`. This step joins all previously built components -- SCV records, propositions, conditions, citations, and assertion methods -- into the output structure consumed by VCV procedures and the JSON export pipeline.

---

## CTEs

The step uses several CTEs to prepare intermediate data before the final SELECT.

### scv_condition_name

Derives a single human-readable condition name string from `gkm_scv_condition_sets` for use in the classification description extension:

- **Single condition** -- uses the condition's `name` field directly
- **ConditionSet with 2+ conditions** -- produces `"N conditions"` (e.g., `"3 conditions"`)
- **No condition** -- falls back to `"unspecified condition"`

### temp_scv_citation_docs

Builds one VA-Spec `Document` per ClinVar citation. The same rules apply to the submission's citations (`reportedIn`) and to the assertion method's citations (`specifiedBy.reportedIn`). A ClinVar citation can list several ids for one publication; ACMG 2015, for example, lists a DOI, a PubMed id and a PMC id. They become **one** Document:

| Document field | From the ClinVar citation |
|---|---|
| `pmid` | The `PubMed` id (`PMID` is accepted as an alias) |
| `doi` | The `DOI` id, when it matches VA-Spec's `doi` pattern and has no whitespace |
| `urls` | Every resolvable URL, in a fixed order: ClinVar's own `url`, then PubMed, PMC, DOI and Bookshelf (table below) |
| `name` | The citation's `abbrev`, e.g. `ACMG, 2015` or `GeneReviews` |
| `documentType` | The citation's `type`, verbatim: `general`, `practice guideline`, `review`, `Suggested Reading`, `file in FileTrack` |

| Source | URL format |
|---|---|
| PubMed | `https://pubmed.ncbi.nlm.nih.gov/{id}` |
| PMC | `https://europepmc.org/article/PMC/{id}` |
| DOI | `https://doi.org/{doi}`, with characters that are not URL-safe percent-encoded |
| BookShelf | `https://www.ncbi.nlm.nih.gov/books/{id}` |

`urls` only ever holds `http(s)` URLs, never a bare id or CURIE. Citations with only a URL become `{urls: [url]}`.

ClinVar's original values are never changed silently. Only invalid values are repaired, and the Document's `extensions` keep the originals:

| Extension | Value | When |
|---|---|---|
| `clinvarCitationText` | string | The citation has free text. A text-only citation becomes a Document whose only content is this extension. The text is often not a reference at all, e.g. a list of ACMG criteria. |
| `originalClinvarCitation` | string | The id was repaired; the value is the id as ClinVar has it |
| `originalClinvarCitationSource` | string | The id was moved to another source; the value is ClinVar's source |
| `citationRepaired` | `true` | Any repair was made |
| `clinvarDoi` | string | A valid DOI that VA-Spec's `doi` pattern rejects, such as SICI DOIs (`10.1002/(SICI)…`). `doi` stays empty and the DOI's `doi.org` URL is in `urls`. |
| `invalidClinvarCitation` | string | An id that cannot be used, e.g. a DOI of `https`. No `doi` or URL is derived from it. |
| `unmappedClinvarCitation` | string | `<source>:<id>` for a source the pipeline does not recognize |
| `clinvarAssertionMethodCitation` | `true` | A second or later assertion-method citation, reported on the statement (see `temp_scv_method`) |

The repairs:

- **DOI with a prefix or stray characters**: whitespace, a leading `https://doi.org/`, `http://dx.doi.org/`, `doi.org/`, `doi:`, `doi/` or `org/`, and a trailing `.` are removed. The result must match the DOI pattern, or the id is unusable (`invalidClinvarCitation`).
- **DOI source with a PubMed or PMC id**: a DOI-sourced id that is all digits becomes `pmid`; one shaped `PMC<digits>` becomes a PMC URL. Both keep `originalClinvarCitationSource`.

**Output:** `temp_scv_citation_docs` — internal temporary table consumed by `temp_scv_citations` and `temp_scv_method`.

### temp_scv_citations

Collects the submission's citation Documents into the `reportedIn` array, ordered by PubMed id and then by content. Identical Documents collapse to one.

### temp_scv_method

Builds the assertion method record for the `specifiedBy` field: the method type, the method name and, when the assertion method cites a publication, its Document. `Method.reportedIn` holds one Document. When ClinVar lists more than one citation for the method, the first, in ClinVar's order, goes on the method. The rest go on the statement's `reportedIn`, with the extension `clinvarAssertionMethodCitation`.

---

## Output Record Structure

<div class="field-table" markdown>

| Field | Source | Description |
|---|---|---|
| `id` | SCV | Statement identifier in the format `clinvar.submission:{accession}.{version}` |
| `type` | Static | Always `Statement` |
| `proposition` | Step 5 | Full proposition with variant, condition, and qualifiers |
| `classification` | SCV | Classification struct with name, primaryCoding, and description extension |
| `strength` | SCV | Evidence strength with coded value (somatic assertions only) |
| `direction` | SCV | `supports` or `disputes` |
| `description` | SCV | Classification comment text |
| `contributions` | SCV | Three Contribution entries: submitted, created, and evaluated |
| `specifiedBy` | `temp_scv_method` | Assertion method with its citation Document |
| `reportedIn` | `temp_scv_citations` | Array of citation Documents, one per ClinVar citation |
| `extensions` | SCV | Array of SCV-level extensions (see below) |
| `hasEvidenceLines` | Step 6 | Somatic evidence lines with target proposition and outcome |

</div>

### Extensions

The `extensions` array on each statement includes:

- **clinvarScvId** -- the SCV accession identifier
- **clinvarScvVersion** -- the SCV version number
- **clinvarScvReviewStatus** -- the review status assigned by ClinVar
- **submittedScvClassification** -- the original submitted classification label
- **submittedScvLocalKey** -- the submitter's local key for the assertion
- **submissionLevel** -- the submission level code and label

### Classification Description Extension

The `classification.extensions` array contains a formatted description string assembled from multiple fields:

```
for <condition_name>
Classification is based on the <submission_level_label> submission
<evaluated_date> by <submitter_name>
```

This provides a human-readable summary of the classification context, including the condition, submission level, evaluation date, and submitting organization.

### Somatic Evidence Lines

For somatic clinical impact assertions, the `hasEvidenceLines` field contains evidence line records that wrap the target proposition from Step 6. Each evidence line includes the target proposition (with its somatic-specific predicate and therapy/condition references) and the outcome classification.

---

## Output

**`gkm_dict_scv`** -- one row per SCV with the complete VA-Spec Statement record. <span class="role-badge badge-pipeline">Pipeline table</span>

Consumed by `gkm_vcv_proc` and `gkm_vcv_statement_proc` for VCV aggregation, and assembled directly into the published bundle by the export pipeline.

---

## Dependencies

- **Upstream Steps**: Step 1 (`temp_gkm_scv`), Step 5 (`temp_gkm_scv_proposition`), Step 6 (`temp_gkm_scv_target_proposition`)
- **Upstream Procedures**: `gkm_scv_condition_proc` (provides `gkm_scv_condition_sets`)
- **Downstream Consumers**: `gkm_vcv_proc`, `gkm_vcv_statement_proc`, change-log / delta build (`gkm_change_log`), export pipeline
