# Examples

Example files are maintained in the [examples/](https://github.com/clingen-data-model/clinvar-gkm/tree/main/examples) directory of the repository. These serve as reference targets for the data structures produced by the pipeline and are useful for early adopters and for validating output against expected formats.

---

## File Format

Each file is a **bundle fragment**: a small JSON object with the same shape as a published bundle, `{"schema_version": "1.2.0", "<section>": {"<key>": record}, ...}`. It holds the record the file is named for (the *top record*) exactly as the bundle has it, so its references are `#/<section>/<key>` [pointers](../output-reference/id-references.md), plus the records those pointers lead to.

Every pointer is followed, except pointers into the `scv` and `variation` sections, which stay pointers:

| Pointer kept | What it names | Where to see one |
| --- | --- | --- |
| `#/scv/…` | A submission aggregated by a VCV or RCV statement | The SCV examples below |
| `#/variation/…` | A proposition's `subject` | The Cat-VRS examples below |

Pointers into `vcv` and `rcv` are followed, so a VCV or RCV file holds its whole aggregation hierarchy: the top statement and every nested layer statement below it (such as `…-G-PATH-CP`, or `…-S-SCI-CP` and `…-S-SCI-CP-T1`), each with its proposition, evidence lines and condition or condition set. The hierarchy ends at the `#/scv/` pointers of the lowest layer. An SCV file holds the statement, its proposition, submitter, condition or condition set (with its member conditions), and any evidence line and therapy. A Cat-VRS file holds the variation with its alleles, locations, sequence references and genes, so every pointer in it resolves.

!!! note "Fragments, not closed bundles"
    Every file validates against the [bundle schema](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/clinvar-gkm-bundle.schema.json), but not every `#/…` pointer resolves inside the file. A kept pointer names a record in the full bundle of the same release. A published bundle resolves every pointer; for a closed extract of a few statements, see [Sub-Bundle Extraction](../pipeline/sub-bundle.md).

The files are regenerated from a published full bundle by `src/scripts/extract-example.py`; the [examples readme](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/readme.md) has the command.

---

## Categorical Variants (Cat-VRS)

Examples of `CategoricalVariant` records — the resolved VRS representations of ClinVar variations with expressions, cross-references, and metadata.

| File | Variant | Type | Description |
| --- | --- | --- | --- |
| [clinvar:12582.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/cat-vrs/clinvar%3A12582.jsonc) | KRAS (variation 12582) | CanonicalAllele | Canonical allele with DefiningAlleleConstraint, multiple expression formats, gene associations, cross-references |
| [clinvar:208366.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/cat-vrs/clinvar%3A208366.jsonc) | Variation 208366 | CanonicalAllele | Additional canonical allele example |

See [Categorical Variants output reference](../output-reference/cat-vrs.md) for field documentation.

---

## SCV Statements

Examples of VA-Spec `Statement` records for individual ClinVar submissions.

### Germline Pathogenicity (G.01)

| File | SCV | Classification | Gene / Condition | Description |
| --- | --- | --- | --- | --- |
| [SCV001571657.2-G-PATH.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/scv/SCV001571657.2-G-PATH.jsonc) | SCV001571657.2 | Pathogenic (definitive) | KRAS / Acute myeloid leukemia | VariantPathogenicityProposition, NOCP review status, gene context with HGNC mapping, MedGen/Orphanet/MeSH/MONDO condition xrefs |

### Germline Other Types (G.02-G.09)

| File | SCV | Classification | Type | Description |
| --- | --- | --- | --- | --- |
| [SCV004035006.2-G-ASSOC.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/scv/SCV004035006.2-G-ASSOC.jsonc) | SCV004035006.2 | association (supports) | Association (G.06) | ClinVarAssociationProposition, KRAS variant with multiple endometrial conditions in a ConditionSet |
| [SCV002099547.2-G-NP.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/scv/SCV002099547.2-G-NP.jsonc) | SCV002099547.2 | not provided (supports) | Not Provided (G.09) | ClinVarNotProvidedProposition, KRAS / Encephalocraniocutaneous lipomatosis |

### Oncogenicity (O.10)

| File | SCV | Classification | Gene / Condition | Description |
| --- | --- | --- | --- | --- |
| [SCV005093950.2-S-ONCO.json](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/scv/SCV005093950.2-S-ONCO.json) | SCV005093950.2 | Oncogenic (definitive) | ERBB2 / Neoplasm | VariantOncogenicityProposition, CP review status, ClinGen/CGC/VICC Guidelines 2022 method |

### Somatic Clinical Impact (S.11-S.14)

| File | SCV | Classification | Tier | Sub-type | Description |
| --- | --- | --- | --- | --- | --- |
| [SCV004565358.1-S-SCI-T1-TR.json](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/scv/SCV004565358.1-S-SCI-T1-TR.json) | SCV004565358.1 | Tier I - Strong | Tier I | Therapeutic Response (S.12) | EGFR L858R / NSCLC, drug sensitivity evidence line with erlotinib therapy, AMP/ASCO/CAP Guidelines 2017 |
| [SCV004565361.1-S-SCI-T2-DIAG.json](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/scv/SCV004565361.1-S-SCI-T2-DIAG.json) | SCV004565361.1 | Tier II - Potential | Tier II | Diagnostic (S.13) | ACVR1 / diffuse intrinsic pontine glioma, diagnostic inclusion criterion evidence line |
| [SCV005387955.1-S-SCI-T3-VUS.json](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/scv/SCV005387955.1-S-SCI-T3-VUS.json) | SCV005387955.1 | Tier III - Unknown | Tier III | Clinical Significance (S.11) | TG variant, neutral direction, no paired sub-statement |
| [SCV005061369.1-S-SCI-T4-BLB.json](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/scv/SCV005061369.1-S-SCI-T4-BLB.json) | SCV005061369.1 | Tier IV - Benign/LB | Tier IV | Clinical Significance (S.11) | TP53 / CML, disputes direction, no paired sub-statement |

See [SCV Statements output reference](../output-reference/scv-statements.md) for field documentation.

---

## VCV Statements

Examples of aggregate classification `Statement` records produced by rolling up SCV submissions through the aggregation hierarchy. Each file holds the whole hierarchy: the top statement and, as statements of their own, every layer listed below (for example `VCV000012582.69-G-PATH-CP`), each with its proposition, evidence lines and condition records. The SCVs stay `#/scv/` pointers; an SCV count is the number of pointers in that layer's evidence lines.

### Germline

| File | VCV | Prop Type | Submission Levels | Description |
| --- | --- | --- | --- | --- |
| [VCV000012582.69-G-PATH.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/vcv/VCV000012582.69-G-PATH.jsonc) | VCV000012582 | Pathogenicity | CP, NOCP | Pathogenic/Likely pathogenic. CP contributing with 15 concordant SCVs; NOCP non-contributing with 20 SCVs. The proposition `object` is an `OR` condition set of 8 members minted for the aggregate; one member is itself a ClinVar trait set (`AND`) of 12 conditions |
| [VCV000012582.69-G-ASSOC.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/vcv/VCV000012582.69-G-ASSOC.jsonc) | VCV000012582 | Association | NOCP | Single NOCP submission; the `object` is a ClinVar trait set (`AND`) of two conditions |
| [VCV000012582.69-G-NP.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/vcv/VCV000012582.69-G-NP.jsonc) | VCV000012582 | Not Provided | NOCL | Single NOCL submission for Encephalocraniocutaneous lipomatosis |
| [VCV000007105.214-G-PATH.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/vcv/VCV000007105.214-G-PATH.jsonc) | VCV000007105 | Pathogenicity | PG, EP, CP, NOCP | Pathogenic, practice guideline. PG contributing (1 SCV); EP (1 SCV), CP (83 SCVs) and NOCP (10 SCVs) non-contributing. Cystic fibrosis |
| [VCV000007105.214-G-DR.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/vcv/VCV000007105.214-G-DR.jsonc) | VCV000007105 | Drug Response | EP | Two expert-panel SCVs; the `object` is an `OR` condition set of two drug-response conditions |
| [VCV000007105.214-G-RF.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/vcv/VCV000007105.214-G-RF.jsonc) | VCV000007105 | Risk Factor | NOCP | Single NOCP submission for a bronchiectasis modifier condition |
| [VCV000007105.214-G-NP.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/vcv/VCV000007105.214-G-NP.jsonc) | VCV000007105 | Not Provided | NOCL | Four NOCL SCVs; the `object` is an `OR` condition set of three conditions |

### Somatic

| File | VCV | Prop Type | Tiers | Description |
| --- | --- | --- | --- | --- |
| [VCV000012582.69-S-SCI.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/vcv/VCV000012582.69-S-SCI.jsonc) | VCV000012582 | Somatic Clinical Impact | Tier I, Tier II | Aggregate Contribution → Priority Grouping → Classification Grouping hierarchy, three levels of statements. `-CP` contributes; under it `-CP-T1` (Tier I, 7 SCVs) contributes and `-CP-T2` (Tier II, 3 SCVs) does not. `-NOCP` is non-contributing, with `-NOCP-T1` (Tier I, 1 SCV) under it |
| [VCV000012582.69-S-ONCO.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/vcv/VCV000012582.69-S-ONCO.jsonc) | VCV000012582 | Oncogenicity | N/A | Somatic oncogenicity aggregate (Aggregate Contribution → Classification Grouping). Single CP submission, no priority grouping |

### PG and EP (single-submission levels)

PG (practice guideline) and EP (reviewed by expert panel) submissions are aggregated as separate top-tier submission levels. PG outranks EP in the Aggregate Contribution Layer winner-takes-all selection, followed by CP, NOCP, NOCL, and FLAG. `VCV000007105.214-G-PATH` shows a PG winner with EP, CP and NOCP non-contributing; `VCV000007105.214-G-DR` shows an EP-only aggregate.

See [VCV Statements output reference](../output-reference/vcv-statements.md) for field documentation.

---

## RCV Statements

Examples of RCV `Statement` records: the aggregate for one variant and one condition (or condition set), built with the same layers as VCV statements. As with the VCV files, each file holds the top statement and every layer listed below as a statement, and the SCVs stay `#/scv/` pointers.

### Germline

| File | RCV | Variant | Prop Type | Condition | Description |
| --- | --- | --- | --- | --- | --- |
| [RCV000007523.120-G-PATH.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV000007523.120-G-PATH.jsonc) | RCV000007523 | Variation 7105 | Pathogenicity | Cystic fibrosis | PG contributing (1 SCV); EP (1), CP (45) and NOCP (4) non-contributing |
| [RCV000007523.120-G-NP.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV000007523.120-G-NP.jsonc) | RCV000007523 | Variation 7105 | Not Provided | Cystic fibrosis | NOCL, 2 SCVs |
| [RCV001787370.11-G-DR.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV001787370.11-G-DR.jsonc) | RCV001787370 | Variation 7105 | Drug Response | ivacaftor / lumacaftor response - Efficacy | EP, 1 SCV |
| [RCV001787371.11-G-DR.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV001787371.11-G-DR.jsonc) | RCV001787371 | Variation 7105 | Drug Response | ivacaftor / tezacaftor response - Efficacy | EP, 1 SCV |
| [RCV000029215.25-G-PATH.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV000029215.25-G-PATH.jsonc) | RCV000029215 | KRAS (variation 12582) | Pathogenicity | Linear nevus sebaceous syndrome | CP contributing (4 SCVs); NOCP non-contributing (1) |
| [RCV000272938.40-G-PATH.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV000272938.40-G-PATH.jsonc) | RCV000272938 | KRAS (variation 12582) | Pathogenicity | not provided | CP contributing (4 SCVs); NOCP non-contributing (1) |
| [RCV000548006.14-G-PATH.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV000548006.14-G-PATH.jsonc) | RCV000548006 | KRAS (variation 12582) | Pathogenicity | RASopathy | CP, 2 SCVs |
| [RCV000585796.12-G-PATH.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV000585796.12-G-PATH.jsonc) | RCV000585796 | KRAS (variation 12582) | Pathogenicity | Cerebral arteriovenous malformation | CP contributing (1 SCV); NOCP non-contributing (2) |
| [RCV004018620.1-G-PATH.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV004018620.1-G-PATH.jsonc) | RCV004018620 | KRAS (variation 12582) | Pathogenicity | Cardiovascular phenotype | Likely pathogenic, CP, 1 SCV |
| [RCV004554600.1-G-PATH.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV004554600.1-G-PATH.jsonc) | RCV004554600 | KRAS (variation 12582) | Pathogenicity | Congenital Pulmonary Airway Malformations | CP, 1 SCV |
| [RCV005007840.1-G-PATH.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV005007840.1-G-PATH.jsonc) | RCV005007840 | KRAS (variation 12582) | Pathogenicity | ClinVar trait set of 12 conditions (`AND`) | CP, 1 SCV; the `object` is a `#/conditionSet/` reference |
| [RCV003327361.6-G-ASSOC.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV003327361.6-G-ASSOC.jsonc) | RCV003327361 | KRAS (variation 12582) | Association | ClinVar trait set of 2 conditions (`AND`) | NOCP, 1 SCV |
| [RCV001839445.10-G-NP.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV001839445.10-G-NP.jsonc) | RCV001839445 | KRAS (variation 12582) | Not Provided | Encephalocraniocutaneous lipomatosis | NOCL, 1 SCV |
| [RCV001781420.15-G-PATH.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV001781420.15-G-PATH.jsonc) | RCV001781420 | Variation 97850 | Pathogenicity | Inflammatory bowel disease 1 | Conflicting classifications of pathogenicity, CP, 2 SCVs; `neutral` direction |

### Somatic

| File | RCV | Variant | Prop Type | Condition | Description |
| --- | --- | --- | --- | --- | --- |
| [RCV004668724.2-S-ONCO.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV004668724.2-S-ONCO.jsonc) | RCV004668724 | KRAS (variation 12582) | Oncogenicity | Neoplasm | Oncogenic, CP, 1 SCV |
| [RCV006253518.1-S-SCI.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV006253518.1-S-SCI.jsonc) | RCV006253518 | KRAS (variation 12582) | Somatic Clinical Impact | Precursor B-cell acute lymphoblastic leukemia | Tier I diagnostic, CP, 1 SCV |
| [RCV006253519.1-S-SCI.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV006253519.1-S-SCI.jsonc) | RCV006253519 | KRAS (variation 12582) | Somatic Clinical Impact | Papillary thyroid carcinoma | Tier I diagnostic, CP, 1 SCV |
| [RCV006253521.1-S-SCI.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV006253521.1-S-SCI.jsonc) | RCV006253521 | KRAS (variation 12582) | Somatic Clinical Impact | Glioma | Tier I diagnostic, CP, 1 SCV |
| [RCV006253522.1-S-SCI.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV006253522.1-S-SCI.jsonc) | RCV006253522 | KRAS (variation 12582) | Somatic Clinical Impact | Embryonal rhabdomyosarcoma | Tier I diagnostic, CP, 1 SCV |
| [RCV006253523.1-S-SCI.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV006253523.1-S-SCI.jsonc) | RCV006253523 | KRAS (variation 12582) | Somatic Clinical Impact | Diffuse pediatric-type high-grade glioma, H3-wildtype and IDH-wildtype | Tier I diagnostic, CP, 1 SCV |
| [RCV006253525.1-S-SCI.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV006253525.1-S-SCI.jsonc) | RCV006253525 | KRAS (variation 12582) | Somatic Clinical Impact | Adenocarcinoma of the large intestine | Tier I diagnostic, CP, 1 SCV |
| [RCV006253527.1-S-SCI.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV006253527.1-S-SCI.jsonc) | RCV006253527 | KRAS (variation 12582) | Somatic Clinical Impact | Ovarian mucinous adenocarcinoma | Tier I diagnostic, CP, 1 SCV |
| [RCV006254391.1-S-SCI.jsonc](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV006254391.1-S-SCI.jsonc) | RCV006254391 | Variation 2758242 | Somatic Clinical Impact | Medulloblastoma WNT activated | Tier I diagnostic, CP, 1 SCV |

The somatic clinical impact RCVs follow the Aggregate Contribution → Priority Grouping → Classification Grouping hierarchy, so each file holds three statements: the top statement, `-CP` and `-CP-T1`.

See [RCV Statements output reference](../output-reference/rcv-statements.md) for field documentation.
