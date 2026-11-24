# Where a Value Comes From

!!! abstract "What this page answers"
    Where a value in a published bundle came from: the ClinVar data it was read from, and the pipeline step that
    built it. Read it when you need to know whether a field is ClinVar's own value, a lookup, or something the
    pipeline computed, or to find the procedure page that explains it in full.

Every value in a bundle starts in ClinVar's XML release. The upstream
[clinvar-ingest](https://github.com/clingen-data-model/clinvar-ingest) pipeline loads the XML into relational
BigQuery tables (`variation`, `scv_summary`, `clinical_assertion`, `trait`, `rcv_mapping` and others); the
procedures in [`src/procedures/`](https://github.com/clingen-data-model/clinvar-gkm/tree/main/src/procedures) read
those tables and build one `gkm_dict_*` table per bundle section; the assembler turns those tables into the
bundle ([Export & Distribute](export.md#step-2-assemble-bundle)).

---

## How to Read the Tables { #how-to-read-the-tables }

Each table below has four columns:

- **Field** — the bundle section and property, as on the [Output Format](../output-reference/overview.md) pages
- **ClinVar source** — the ingested table and column the procedure reads. Where it reads part of a record's
  `content` (the rest of the XML element, kept as JSON), the XML element is named, e.g. *`HGVSlist` element*.
  *Lookup* marks a value taken from a ClinVar-GKM mapping table rather than from the release, and *Computed*
  one the pipeline derives.
- **Built in** — the pipeline page and step that document it, and the procedure file
- **Notes** — what happens to the value on the way

The procedures and their files:

| Procedure | File | Builds |
| --- | --- | --- |
| `variation_identity` | [`variation-identity-proc.sql`](https://github.com/clingen-data-model/clinvar-gkm/blob/main/src/procedures/variation-identity-proc.sql) | The expression sent to vrs-python, HGVS, locations and cross-references per variation |
| `gkm_catvar_proc` | [`gkm-catvar-proc.sql`](https://github.com/clingen-data-model/clinvar-gkm/blob/main/src/procedures/gkm-catvar-proc.sql) | `variation`, `allele`, `location`, `sequenceReference`, copy number sections, `gene` |
| `gkm_scv_condition_proc` | [`gkm-scv-condition-proc.sql`](https://github.com/clingen-data-model/clinvar-gkm/blob/main/src/procedures/gkm-scv-condition-proc.sql) | `condition`, ClinVar trait sets in `conditionSet`, each SCV's resolved condition |
| `gkm_scv_statement_proc` | [`gkm-scv-statement-proc.sql`](https://github.com/clingen-data-model/clinvar-gkm/blob/main/src/procedures/gkm-scv-statement-proc.sql) | `scv`, SCV propositions, SCV evidence lines, `therapy`, `therapyGroup`, `submitter` |
| `gkm_vcv_proc`, `gkm_vcv_statement_proc` | [`gkm-vcv-proc.sql`](https://github.com/clingen-data-model/clinvar-gkm/blob/main/src/procedures/gkm-vcv-proc.sql), [`gkm-vcv-statement-proc.sql`](https://github.com/clingen-data-model/clinvar-gkm/blob/main/src/procedures/gkm-vcv-statement-proc.sql) | `vcv`, VCV propositions and evidence lines, condition sets minted for VCVs |
| `gkm_rcv_proc`, `gkm_rcv_statement_proc` | [`gkm-rcv-proc.sql`](https://github.com/clingen-data-model/clinvar-gkm/blob/main/src/procedures/gkm-rcv-proc.sql), [`gkm-rcv-statement-proc.sql`](https://github.com/clingen-data-model/clinvar-gkm/blob/main/src/procedures/gkm-rcv-statement-proc.sql) | `rcv`, RCV propositions and evidence lines |

---

## Variations

The `variation` section, one [Cat-VRS](../reference/glossary.md#cat-vrs) categorical variant per ClinVar
variation. Field reference: [Variations](../output-reference/cat-vrs.md).

| Field | ClinVar source | Built in | Notes |
| --- | --- | --- | --- |
| `id` | `variation.id` (the Variation ID) | [Cat-VRS, Step 6](cat-vrs/index.md#step-6-build-gkm_catvar_pre) — `gkm-catvar-proc.sql` | Written as `clinvar:{variation_id}` |
| `name` | `variation.name` | [Variation Identity, Step 1](variation-identity/index.md#step-1-extract-variation-records); [`variation_identity` fields](variation-identity/variation-identity.md#fields) | ClinVar's display name, passed through |
| `members` | *Computed*: the vrs-python result for the variation | [Cat-VRS, Step 6](cat-vrs/index.md#step-6-build-gkm_catvar_pre) | A `#/allele/`, `#/copyNumberCount/` or `#/copyNumberChange/` pointer. Absent when no VRS record could be made |
| `constraints` | *Computed*: the vrs-python result, typed by the variation's VRS class | [Cat-VRS, Step 6](cat-vrs/index.md#step-6-build-gkm_catvar_pre) | `DefiningAlleleConstraint` for a canonical allele; `DefiningLocationConstraint` plus `CopyCountConstraint` or `CopyChangeConstraint` for a copy number variant. The relations are fixed codings |
| Copy count or change (in `constraints`) | `AbsoluteCopyNumber` or `CopyNumberTuple` attribute of the submitted variation (`clinical_assertion_variation`); `variation.variation_type` for gain or loss | [Variation Identity, Step 1](variation-identity/index.md#step-1-extract-variation-records) | Read from the submitted (SCV-level) variation |
| `mappings` | `XRefList` element of the variation (`variation_xref`) | [Variation Identity, Step 5](variation-identity/index.md#step-5-build-variation_xref); [Cat-VRS, Step 5](cat-vrs/index.md#step-5-build-temp_catvar_mappings) | Plus an `exactMatch` to the ClinVar variation itself. IRIs come from a lookup of URL templates ([External Cross-References](../output-reference/id-references.md#external-cross-references)) |
| `clinvarHgvsList` extension | `HGVSlist` element of the variation (`variation_hgvs`) | [Variation Identity, Step 3](variation-identity/index.md#step-3-build-variation_hgvs); [HGVS List](cat-vrs/catvar-extensions.md#hgvs-list) | Every nucleotide and protein expression ClinVar lists, with MANE Select flags and molecular consequences (Sequence Ontology terms) |
| `clinvarGeneList` extension | `gene_association` (gene, relationship type, source) | [Gene List](cat-vrs/catvar-extensions.md#gene-list) | Each item points to `#/gene/ncbigene:{id}` |
| `clinvarVariationType`, `clinvarSubclassType`, `clinvarCytogeneticLocation` extensions | `variation.variation_type`, `variation.subclass_type`; cytogenetic location from the variation's `Location` element | [CategoricalVariant Extensions](cat-vrs/catvar-extensions.md#categoricalvariant-extensions) | Passed through from ClinVar |
| `categoricalVariationType`, `definingVrsVariationType` extensions | *Computed*: the VRS class and the vrs-python result type | [Variation Identity, Step 4](variation-identity/index.md#step-4-refine-vrs-class-assignments); [Cat-VRS, Step 4](cat-vrs/index.md#step-4-build-temp_catvar_extension) | Derived by the pipeline |
| `vrsPreProcessingIssue`, `vrsProcessingException` extensions | *Computed*: problems found choosing an expression, or errors from vrs-python | [CategoricalVariant Extensions](cat-vrs/catvar-extensions.md#categoricalvariant-extensions) | Present only when VRS resolution had a problem |

---

## VRS Records

The `allele`, `copyNumberCount`, `copyNumberChange`, `location` and `sequenceReference` sections hold the
[VRS](../reference/glossary.md#vrs) records a variation points to. Their identifiers are computed by
[vrs-python](https://github.com/ga4gh/vrs-python), not read from ClinVar.

| Field | ClinVar source | Built in | Notes |
| --- | --- | --- | --- |
| What vrs-python is given | One expression per variation, the best-ranked of: the `CanonicalSPDI` element, an HGVS expression from `HGVSlist`, or a gnomAD-style expression from the VCF fields of the `Location` element | [Variation Identity, Precedence Hierarchy](variation-identity/index.md#precedence-hierarchy); [VRS Processing](vrs-processing.md#step-2-translate-with-vrs-python-cloud-vrsify) | SPDI ranks first. Transcript and protein expressions are not translated |
| `allele` `id` (`ga4gh:VA.…`), `digest`, `state` | *Computed* by vrs-python | [VRS Processing](vrs-processing.md); [Cat-VRS, Step 2b](cat-vrs/index.md#step-2b-build-gkm_dict_allele) | A VRS identifier is a digest of the normalized allele, so the same allele always gets the same id |
| `allele` `expressions` (SPDI, `hgvs.g`, `gnomad`) | The SPDI sent to vrs-python; HGVS from `HGVSlist`; gnomAD (`chr-pos-ref-alt`) from the VCF fields of the `Location` element; HGVS derived from `Location` coordinates | [Cat-VRS, Step 2](cat-vrs/index.md#step-2-build-temp_ctxvar_expression), [Step 2b](cat-vrs/index.md#step-2b-build-gkm_dict_allele) | Gathered from every variation that normalizes to the same allele. See [HGVS](../reference/glossary.md#hgvs) and [SPDI](../reference/glossary.md#spdi) |
| `allele` `name` | *Computed*: the top-ranked of the allele's expressions | [Cat-VRS, Step 2b](cat-vrs/index.md#step-2b-build-gkm_dict_allele) | |
| `copyNumberCount`, `copyNumberChange` records | *Computed* by vrs-python from the copy number data above | [VRS Processing](vrs-processing.md) | |
| `location` `id` (`ga4gh:SL.…`), `start`, `end` | *Computed* by vrs-python | [Cat-VRS, Step 1b](cat-vrs/index.md#step-1b-build-temp_seqloc); [VRS Processing, Step 3](vrs-processing.md#step-3-transform-vrs-locations) | Coordinate ranges for imprecise ends are rebuilt in the procedure |
| `sequenceReference` key (`SQ.…`), `name`, `assembly` extension | *Computed* refget accession; the sequence accession and assembly version of the expression | [Cat-VRS, Step 1a](cat-vrs/index.md#step-1a-build-temp_seqref); [SequenceReference Extensions](cat-vrs/catvar-extensions.md#sequencereference-extensions) | Assembly is written as `GRCh38`, `GRCh37` or `NCBI36` |

---

## Genes

| Field | ClinVar source | Built in | Notes |
| --- | --- | --- | --- |
| `gene` `id`, `name`, `primaryCoding` | `gene.id`, `gene.symbol` | `gkm-catvar-proc.sql` (`gkm_dict_gene`); [Gene List](cat-vrs/catvar-extensions.md#gene-list) | Only genes some variation's gene list names. Keyed `ncbigene:{id}`, coded in NCBI Gene |
| `gene` `mappings` (HGNC) | `gene.hgnc_id` | `gkm-catvar-proc.sql` (`gkm_dict_gene`) | An `exactMatch` to HGNC |

---

## Conditions

The `condition` and `conditionSet` sections, and how each SCV's condition is matched to them. Built by
`gkm-scv-condition-proc.sql` ([Conditions & Traits](conditions-and-traits/index.md)), except the VCV condition sets.

| Field | ClinVar source | Built in | Notes |
| --- | --- | --- | --- |
| `condition` `id`, `conceptType` | `trait.id`, `trait.type` | [Traits](conditions-and-traits/traits.md#concepttype-mapping-clinvar-gks) | Keyed `clinvar.trait:{trait_id}`; ClinVar's trait type mapped to a concept type |
| `condition` `name` | `trait.name`; else the preferred, then the first alternate name in the RCV trait set | [Condition Name](conditions-and-traits/traits.md#condition-name) | |
| `condition` `primaryCoding`, `mappings`, `aliases` | `trait.xrefs`, `trait.alternate_names` | [Traits, Step 3](conditions-and-traits/traits.md#step-3-aggregate-into-temp_gkm_trait) | The MedGen xref is the `primaryCoding`; the others are `relatedMatch` mappings |
| `conditionSet` (`clinvar.traitset:…`) | The RCV trait set (`rcv_mapping.trait_set_id` and its content) | [Condition Sets](conditions-and-traits/condition-sets.md#build-condition-sets-for-multi-condition-scvs) | `membershipOperator` is `AND` for `Finding member` or `co-occurring condition` traits, otherwise `OR` |
| `conditionSet` (`clinvar.conditionset:vcv-…`) | *Computed* from the conditions of a VCV group's SCVs | `gkm-vcv-statement-proc.sql` | Minted when a VCV's contributing SCVs name more than one condition: an `OR` set keyed by the MD5 of its sorted members ([ID References](../output-reference/id-references.md#identifier-namespaces)) |
| SCV `submittedCondition`, `submittedConditionSet` extensions | The submitted traits (`clinical_assertion_trait_set`, `clinical_assertion_trait`: name, type, xrefs, MedGen id), ClinVar's `trait_mapping`, and `rcv_mapping` | [Condition Mapping](conditions-and-traits/condition-mapping.md); [Submitted Condition](scv-statements/scv-extensions.md#submitted-condition) | Records how the [submitted condition](../reference/glossary.md#submitted-condition) was resolved to a `clinvar.trait:{id}` (`normalized_resolution`). Values are bare ids, not pointers |

---

## SCV Statements

The `scv` section, built by `gkm-scv-statement-proc.sql` from `scv_summary` joined to `clinical_assertion`
([SCV Statements procedure](scv-statements/index.md)). Field reference: [SCV Statements](../output-reference/scv-statements.md).

| Field | ClinVar source | Built in | Notes |
| --- | --- | --- | --- |
| `id` | `scv_summary.id`, `scv_summary.version` | [Output Record Structure](scv-statements/final-statements.md#output-record-structure) | Written as `clinvar.submission:{SCV}.{version}` |
| `classification` `name` | `scv_summary.submitted_classification` | [Output Record Structure](scv-statements/final-statements.md#output-record-structure) | |
| `classification` `primaryCoding`, `strength`, `direction` | *Lookup*: `clinvar_clinsig_types`, keyed by the SCV's classification and statement type | [Classification and Proposition Type Mapping](scv-statements/scv-records.md#classification-and-proposition-type-mapping) | `strength` is omitted when the lookup has none. See [Classifications](../profiles/classifications.md) |
| `classification` `description` extension | *Computed* from the condition name, submission level, date last evaluated and submitter name | [Classification Description Extension](scv-statements/final-statements.md#classification-description-extension) | Text composed by the pipeline |
| `quality` | *Computed*: the submission level label, from the SCV's review status rank | [Submission Level](scv-statements/scv-records.md#submission-level) | See [Review Status](../profiles/review-status.md) |
| `description` | `scv_summary.classification_comment` | [Output Record Structure](scv-statements/final-statements.md#output-record-structure) | The submitter's comment, passed through |
| `contributions` | `scv_summary.date_last_updated` (`submitted`), `date_created` (`created`), `last_evaluated` (`evaluated`); `scv_summary.submitter_id` | [Contributions](../output-reference/scv-statements.md#contributions) | Each `contributor` points to `#/submitter/clinvar.submitter:{id}` |
| `specifiedBy` | The assertion method attribute and its citation in the SCV's `content` (`clinical_assertion`) | [Assertion Method Parsing](scv-statements/scv-records.md#assertion-method-parsing); [temp_scv_method](scv-statements/final-statements.md#temp_scv_method) | |
| `reportedIn` | The `Citation` entries of the SCV and of its `Classification` element (`clinical_assertion.content`) | [temp_scv_citation_docs](scv-statements/final-statements.md#temp_scv_citation_docs) | One Document per citation, de-duplicated |
| `clinvarScvId`, `clinvarScvVersion` extensions | `scv_summary.id`, `scv_summary.version` | [Statement Extensions](scv-statements/scv-extensions.md#statement-extensions) | |
| `clinvarScvReviewStatus` extension | `scv_summary.review_status` | [Statement Extensions](scv-statements/scv-extensions.md#statement-extensions) | ClinVar's [review status](../reference/glossary.md#review-status), passed through |
| `submittedScvClassification`, `submittedScvLocalKey`, `submissionLevel` extensions | `scv_summary.submitted_classification`, `scv_summary.local_key`; the submission level | [Statement Extensions](scv-statements/scv-extensions.md#statement-extensions) | `submittedScvClassification` appears only when the submitted text differs from the lookup's label |
| `hasEvidenceLines` (somatic) | The SCV's clinical impact assertion type and clinical significance | [Somatic Evidence Lines](scv-statements/final-statements.md#somatic-evidence-lines); [Step 6](scv-statements/propositions.md#step-6-target-proposition-somatic) | Tier I and II somatic clinical impact SCVs only |

### SCV Propositions { #scv-propositions }

| Field | ClinVar source | Built in | Notes |
| --- | --- | --- | --- |
| `id`, `type`, `predicate` | *Lookup*: proposition type and predicate by statement type (`clinvar_proposition_types`, `clinvar_clinsig_types`) | [Step 5: Primary Proposition](scv-statements/propositions.md#step-5-primary-proposition) | Id `{SCV}-{CODE}`; the type picks the bundle section ([Proposition Types](../profiles/propositions.md)) |
| `subject` | `scv_summary.variation_id` | [Step 5: Primary Proposition](scv-statements/propositions.md#step-5-primary-proposition) | `#/variation/clinvar:{id}` |
| `object` | The SCV's resolved condition (see [Conditions](#conditions)) | [Step 5: Primary Proposition](scv-statements/propositions.md#step-5-primary-proposition) | `#/condition/` or `#/conditionSet/` |
| `geneContextQualifier` and its `geneContextSource` | The variant's single representative gene (`single_gene_variation`); the submitted gene symbols of the SCV's variation | [Step 2: Gene Context Qualifiers](scv-statements/propositions.md#step-2-build-temp_gene_context_qualifiers) | `geneContextSource` is computed by comparing the symbols ([gene context FAQ](../reference/faq.md#where-does-an-scv-propositions-gene-context-come-from)) |
| `modeOfInheritanceQualifier` | The `ModeOfInheritance` attribute of the SCV; *Lookup*: HPO terms | [Step 3: Mode of Inheritance Qualifiers](scv-statements/propositions.md#step-3-build-temp_moi_qualifiers) | HPO coding added when the text matches a term |
| `penetranceQualifier` | *Computed* from the classification (low penetrance and risk allele terms) | [Step 4: Penetrance Qualifiers](scv-statements/propositions.md#step-4-build-temp_penetrance_qualifiers) | `low` or `risk` |

---

## VCV and RCV Statements

The `vcv` and `rcv` sections are not copied from ClinVar's own VCV and RCV classifications: the pipeline
recomputes each aggregate from the SCVs, following ClinVar's rules ([Aggregation Rules](vcv-statements/vcv-aggregation-rules.md)).
Field reference: [VCV Statements](../output-reference/vcv-statements.md), [RCV Statements](../output-reference/rcv-statements.md).

| Field | ClinVar source | Built in | Notes |
| --- | --- | --- | --- |
| VCV `id` | `variation_archive.id`, `.version` | [VCV Procedures, Step 1](vcv-statements/vcv-proc.md#step-1-build-temp_vcv_base_data) | Plus lane, classification code and level, e.g. `VCV000012582.63-G-PATH-CP` ([VCV Statement IDs](../output-reference/id-references.md#vcv-statement-ids)) |
| RCV `id` | `rcv_accession.id`, `.version`; grouped by `rcv_mapping.trait_set_id` | [RCV Procedures, Step 1](rcv-statements/rcv-proc.md#step-1-build-temp_rcv_base_data) | ([RCV Statement IDs](../output-reference/id-references.md#rcv-statement-ids)) |
| `classification` `name`, `conflictingExplanation` extension | *Computed* from the classifications of the SCVs in the group | [Classification](vcv-statements/vcv-aggregation-rules.md#classification) | A conflict lists each classification with its count |
| `classification` `primaryCoding` | *Lookup*: `clinvar_clinsig_types`; else the label with system `ClinVar` | [classification.primaryCoding](vcv-statements/vcv-aggregation-rules.md#classification-primarycoding) | |
| `clinvarReviewStatus` extension | *Computed* from the submission level, the number of submitters and whether they conflict | [Aggregate Review Status](vcv-statements/vcv-aggregation-rules.md#aggregate-review-status) | |
| `direction`, `strength`, `quality` | *Lookup* and *Computed*: the label's `clinvar_clinsig_types` row; the submission level | [`quality`, `direction`, and `strength`](vcv-statements/vcv-aggregation-rules.md#quality-direction-and-strength) | |
| `hasEvidenceLines` | *Computed*: the lower-layer statements or SCVs, split into contributing and non-contributing | [Base Statement Steps](vcv-statements/vcv-proc.md#base-statement-steps) | See the [layer hierarchy](../output-reference/vcv-statements.md#layer-hierarchy) |
| VCV proposition `object` | The resolved conditions of the contributing SCVs | [Base Statement Steps](vcv-statements/vcv-proc.md#base-statement-steps) | One condition gives a pointer to it; several give a minted `clinvar.conditionset:vcv-…` set |
| RCV proposition `object` | The resolved condition of the RCV's lowest-id member SCV; else the RCV's own trait set (`rcv_mapping`) | [Condition Data Resolution](rcv-statements/rcv-proc.md#condition-data-resolution) | |

---

## Therapies and Submitters

Built by `gkm-scv-statement-proc.sql`.

| Field | ClinVar source | Built in | Notes |
| --- | --- | --- | --- |
| `therapy` `id`, `name` | The `DrugForTherapeuticAssertion` attribute of the SCV's `SomaticClinicalImpact` classification (`clinical_assertion.content`), split on `;` | [Drug Therapy Extraction](scv-statements/scv-records.md#drug-therapy-extraction) | Keyed `clinvar.therapy:{sha256}` of the record: therapies have no ClinVar id |
| `therapyGroup` | Two or more drugs on one SCV | [Drug Therapy Extraction](scv-statements/scv-records.md#drug-therapy-extraction); [Step 6](scv-statements/propositions.md#step-6-target-proposition-somatic) | Keyed `clinvar.therapygroup:{sha256}`; `membershipOperator` `AND` |
| `submitter` `id`, `name` | `scv_summary.submitter_id`, `scv_summary.submitter_name` | [Submitter Struct](scv-statements/scv-records.md#submitter-struct) | Keyed `clinvar.submitter:{id}` |

---

## From Tables to the Bundle { #from-tables-to-the-bundle }

The assembler (`src/scripts/assemble-gkm-dicts.py` with `gkm_json_cleanup.py`) changes the form of values, not
their content. It drops null and empty fields, collapses typed extension values (`value_<type>`) to `value`, sorts
the few arrays whose order carries no meaning, and writes each record as compact JSON with its keys sorted, so an
unchanged record has the same bytes in every release ([Export & Distribute, Step 2](export.md#step-2-assemble-bundle)).

---

## Tracing One Value { #tracing-one-value }

The proposition of `clinvar.submission:SCV008145211.1` (the record in the
[annotated walk-through](../data-access/examples.md#annotated-walk-through)) has
`"object": "#/condition/clinvar.trait:66395"`. Its path back to ClinVar:

1. The submitter named the condition with a MONDO code, `MONDO:0800400`, on the submitted trait
   (`clinical_assertion_trait`).
2. `gkm_scv_condition_proc` matched that code to ClinVar trait 66395 through ClinVar's trait mapping; the SCV's
   `submittedCondition` extension records it as `"normalized_resolution": "tm reftype xref mondo"` and
   `"condition": "clinvar.trait:66395"` ([Condition Mapping](conditions-and-traits/condition-mapping.md)).
3. The `condition` record `clinvar.trait:66395` comes from the `trait` table: its name, RP1-related dominant
   retinopathy, and its MedGen `primaryCoding`, `CN322606` ([Traits](conditions-and-traits/traits.md)).
4. `gkm_scv_statement_proc` wrote the proposition's `object` as a pointer to that record
   ([Step 5: Primary Proposition](scv-statements/propositions.md#step-5-primary-proposition)).

---

## See Also { #see-also }

- [Pipeline Overview](index.md) — the steps in order
- [Output Format](../output-reference/overview.md) — the bundle's sections
- [Mapping & Vocabularies](../profiles/index.md) — the lookups behind classifications, propositions and review status
