# Examples

!!! abstract "What this page answers"
    What real ClinVar-GKM records look like, from one variant to a whole VCV hierarchy. Start with the
    [annotated walk-through](#annotated-walk-through) of one submission, then open the example file closest to
    what you need from the tables below.

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

## Annotated Walk-Through { #annotated-walk-through }

One submission, read field by field: `clinvar.submission:SCV008145211.1`, a likely pathogenic classification of
an RP1 deletion for RP1-related dominant retinopathy, from the 2026-11-15 weekly delta of the 1.2 line. The
record below is the delta's `scv` record with its keys reordered for reading; two `contributions` entries, the
classification's `description` extension and most of the `description` text are left out (marked `/* … */`). The
numbered comments are callouts, not part of the data.

```json
{
  "id": "clinvar.submission:SCV008145211.1",               // (1)
  "type": "Statement",
  "proposition": "#/propositionPathogenicity/SCV008145211-PATH",   // (2)
  "classification": {                                       // (3)
    "type": "MappableConcept",
    "conceptType": "Classification",
    "name": "Likely pathogenic",
    "primaryCoding": { "code": "likely pathogenic", "system": "ACMG Guidelines, 2015" },
    "extensions": [ /* … */ ]
  },
  "strength": {
    "type": "MappableConcept",
    "conceptType": "Strength",
    "name": "Likely",
    "primaryCoding": { "code": "likely", "system": "ACMG Guidelines, 2015" }
  },
  "direction": "supports",
  "quality": { "type": "MappableConcept", "conceptType": "Quality", "name": "criteria provided" },   // (4)
  "description": "Deletion in exon 4, within the dominant cluster, creating a premature stop codon. …",
  "contributions": [                                        // (5)
    {
      "type": "Contribution",
      "activityType": "evaluated",
      "contributor": "#/submitter/clinvar.submitter:510572",
      "date": "2026-10-19"
    },
    /* … */
  ],
  "specifiedBy": {                                          // (6)
    "type": "Method",
    "name": "ACMG Guidelines, 2015",
    "methodType": "clinical testing",
    "reportedIn": { "type": "Document", "pmid": "25741868", "urls": [ "https://pubmed.ncbi.nlm.nih.gov/25741868" ] }
  },
  "reportedIn": [
    { "type": "Document", "pmid": "34721897", "urls": [ "https://pubmed.ncbi.nlm.nih.gov/34721897" ] },
    { "type": "Document", "pmid": "42847597", "urls": [ "https://pubmed.ncbi.nlm.nih.gov/42847597" ] }
  ],
  "extensions": [                                           // (7)
    { "name": "clinvarScvId", "value": "SCV008145211" },
    { "name": "clinvarScvVersion", "value": "1" },
    { "name": "submittedCondition", "value": {
        "id": "SCV008145211.0",
        "type": "Disease",
        "medgen_id": "CN322606",
        "xrefs": [ { "code": "MONDO:0800400", "system": "MONDO" } ],
        "mapping": { "type": "XRef", "ref": "mondo", "value": "0800400" },
        "normalized_resolution": "tm reftype xref mondo",
        "normalized_match": "clinvar.trait:66395",
        "condition": "clinvar.trait:66395"
    } },
    { "name": "clinvarScvReviewStatus", "value": "criteria provided, single submitter" },
    { "name": "submittedScvLocalKey", "value": "RP1-012|MONDO:MONDO:0800400" },
    { "name": "submissionLevel", "value": "CP" }
  ]
}
```

The proposition the statement points to, from the `propositionPathogenicity` section (the gene and inheritance
qualifiers trimmed to their names):

```json
{
  "id": "SCV008145211-PATH",
  "type": "VariantPathogenicityProposition",
  "subject": "#/variation/clinvar:5042631",                 // (8)
  "predicate": "isCausalFor",
  "object": "#/condition/clinvar.trait:66395",              // (9)
  "geneContextQualifier": { "name": "RP1", "conceptType": "gene", /* … */ },                       // (10)
  "modeOfInheritanceQualifier": { "name": "Autosomal dominant inheritance", "conceptType": "modeOfInheritance", /* … */ }
}
```

| # | Field | What it tells you |
| --- | --- | --- |
| 1 | `id` | The [SCV](../reference/glossary.md#scv) accession and its version (`.1`). |
| 2 | `proposition` | A [pointer](../output-reference/id-references.md#json-pointer-references) to what is claimed. The section name, `propositionPathogenicity`, already says it is a germline pathogenicity claim. |
| 3 | `classification` | The submitter's classification, coded in the guideline's terms. `strength` and `direction` restate it on the [VA-Spec](../reference/glossary.md#va-spec) scale: `Likely`, `supports`. See [Classifications](../profiles/classifications.md). |
| 4 | `quality` | The submission level: this submitter gave assertion criteria. The ClinVar [review status](../reference/glossary.md#review-status) is in the extensions (7). |
| 5 | `contributions` | Who did what, when: the submitter evaluated the variant on 2026-10-19, and submitted and created the record on 2026-11-14. Each `contributor` points into `submitter`. |
| 6 | `specifiedBy`, `reportedIn` | The method (ACMG 2015, with its own citation) and the papers the submitter cited. |
| 7 | `extensions` | ClinVar facts with no GA4GH field. `submittedCondition` records the condition as submitted (a MONDO code) and how it was matched to ClinVar trait `clinvar.trait:66395`: see [submitted condition](../reference/glossary.md#submitted-condition). |
| 8 | `subject` | The variant: ClinVar variation 5042631, `NM_006269.2(RP1):c.2238_2239del (p.Lys746_Ser747insTer)`. Follow its `members` to the [VRS](../reference/glossary.md#vrs) allele; [ID References](../output-reference/id-references.md#resolution-example) does this in code. |
| 9 | `object` | The condition, RP1-related dominant retinopathy, a record in `condition` with a MedGen coding (`CN322606`). |
| 10 | qualifiers | The gene (RP1, NCBI Gene 6101) and the mode of inheritance (HPO `HP:0000006`). The gene qualifier's `geneContextSource` extension says the submitter's symbol matched. |

Every field is described on [SCV Statements](../output-reference/scv-statements.md), and
[Where a Value Comes From](../pipeline/value-provenance.md) traces each back to ClinVar's XML.

### Read it yourself { #read-it-yourself }

!!! note "Prerequisites"
    Python 3.9 or later (standard library only; tested with 3.14.5) and the 5 MB 2026-11-15
    [weekly delta](weekly-deltas.md), a 1.2.0 bundle. Its path changes when its month ends, so look it up in the
    line's `index.json`:

    ```bash
    DELTA=$(curl -fsS https://data.clinvar-gkm.org/v1/1.2/index.json | python3 -c '
    import json, sys
    print(next(d["bundle"]["path"] for d in json.load(sys.stdin)["deltas"] if d["release"] == "2026-11-15"))')
    curl -fsO "https://data.clinvar-gkm.org/${DELTA}"
    ```

Run from the folder you downloaded the delta to. It loads the delta, follows the statement's pointers and prints
what each one leads to:

```python
import gzip
import json

with gzip.open("clinvar-gkm-delta_2026-1115.json.gz", "rt") as f:
    bundle = json.load(f)

def resolve(ref):
    """Resolve a #/section/key pointer to the record it names."""
    section, key = ref.removeprefix("#/").split("/", 1)
    return bundle[section][key]

scv = bundle["scv"]["clinvar.submission:SCV008145211.1"]
proposition = resolve(scv["proposition"])

print(scv["classification"]["name"], "|", scv["quality"]["name"])
print(proposition["type"], proposition["predicate"])
print(resolve(proposition["subject"])["name"])
print(resolve(proposition["object"])["name"])
print(resolve(scv["contributions"][0]["contributor"])["name"])
```

```text
Likely pathogenic | criteria provided
VariantPathogenicityProposition isCausalFor
NM_006269.2(RP1):c.2238_2239del (p.Lys746_Ser747insTer)
RP1-related dominant retinopathy
Department of Ophthalmology, Seoul National University Bundang Hospital
```

Print `json.dumps(scv, indent=2)` to see the whole record.

---

## Categorical Variants (Cat-VRS)

Examples of `CategoricalVariant` records — the resolved VRS representations of ClinVar variations with expressions, cross-references, and metadata.

| Example | Variant | Type | Description |
| --- | --- | --- | --- |
| [A single-nucleotide variant with its VRS allele, HGVS expressions, genes and cross-references](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/cat-vrs/clinvar%3A12582.jsonc)<br>`clinvar:12582.jsonc` | KRAS (variation 12582) | CanonicalAllele | Canonical allele with DefiningAlleleConstraint, multiple expression formats, gene associations, cross-references |
| [A microsatellite (repeat) variant as a canonical allele](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/cat-vrs/clinvar%3A208366.jsonc)<br>`clinvar:208366.jsonc` | Variation 208366 | CanonicalAllele | Additional canonical allele example |

See [Categorical Variants output reference](../output-reference/cat-vrs.md) for field documentation.

---

## SCV Statements

Examples of VA-Spec `Statement` records for individual ClinVar submissions. Each file name ends with the statement's lane (`G` germline, `S` somatic) and classification code; [Statement Types](../profiles/statement-types.md) lists the codes.

### Germline Pathogenicity { #germline-pathogenicity-g01 }

| Example | SCV | Classification | Gene / Condition | Description |
| --- | --- | --- | --- | --- |
| [A germline pathogenicity classification with its gene and condition](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/scv/SCV001571657.2-G-PATH.jsonc)<br>`SCV001571657.2-G-PATH.jsonc` | SCV001571657.2 | Pathogenic (definitive) | KRAS / Acute myeloid leukemia | VariantPathogenicityProposition, NOCP review status, gene context with HGNC mapping, MedGen/Orphanet/MeSH/MONDO condition xrefs |

### Other Germline Claims { #germline-other-types-g02-g09 }

| Example | SCV | Classification | Type | Description |
| --- | --- | --- | --- | --- |
| [An association claim whose condition is a set of several conditions](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/scv/SCV004035006.2-G-ASSOC.jsonc)<br>`SCV004035006.2-G-ASSOC.jsonc` | SCV004035006.2 | association (supports) | Association | ClinvarAssociationProposition, KRAS variant with multiple endometrial conditions in a ConditionSet |
| [A submission with no classification ("not provided")](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/scv/SCV002099547.2-G-NP.jsonc)<br>`SCV002099547.2-G-NP.jsonc` | SCV002099547.2 | not provided (supports) | Not Provided | ClinvarNotProvidedProposition, KRAS / Encephalocraniocutaneous lipomatosis |

### Oncogenicity { #oncogenicity-o10 }

| Example | SCV | Classification | Gene / Condition | Description |
| --- | --- | --- | --- | --- |
| [A somatic oncogenicity classification and the guideline it used](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/scv/SCV005093950.2-S-ONCO.json)<br>`SCV005093950.2-S-ONCO.json` | SCV005093950.2 | Oncogenic (definitive) | ERBB2 / Neoplasm | VariantOncogenicityProposition, CP review status, ClinGen/CGC/VICC Guidelines 2022 method |

### Somatic Clinical Impact { #somatic-clinical-impact-s11-s14 }

| Example | SCV | Classification | Tier | Sub-type | Description |
| --- | --- | --- | --- | --- | --- |
| [A Tier I somatic claim with a drug-response evidence line](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/scv/SCV004565358.1-S-SCI-T1-TR.json)<br>`SCV004565358.1-S-SCI-T1-TR.json` | SCV004565358.1 | Tier I - Strong | Tier I | Therapeutic Response | EGFR L858R / NSCLC, drug sensitivity evidence line with erlotinib therapy, AMP/ASCO/CAP Guidelines 2017 |
| [A Tier II somatic claim with a diagnostic evidence line](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/scv/SCV004565361.1-S-SCI-T2-DIAG.json)<br>`SCV004565361.1-S-SCI-T2-DIAG.json` | SCV004565361.1 | Tier II - Potential | Tier II | Diagnostic | ACVR1 / diffuse intrinsic pontine glioma, diagnostic inclusion criterion evidence line |
| [A Tier III (unknown significance) somatic claim, with a neutral direction](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/scv/SCV005387955.1-S-SCI-T3-VUS.json)<br>`SCV005387955.1-S-SCI-T3-VUS.json` | SCV005387955.1 | Tier III - Unknown | Tier III | Clinical Significance | TG variant, neutral direction, no paired sub-statement |
| [A Tier IV (benign) somatic claim, with a disputes direction](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/scv/SCV005061369.1-S-SCI-T4-BLB.json)<br>`SCV005061369.1-S-SCI-T4-BLB.json` | SCV005061369.1 | Tier IV - Benign/LB | Tier IV | Clinical Significance | TP53 / CML, disputes direction, no paired sub-statement |

See [SCV Statements output reference](../output-reference/scv-statements.md) for field documentation.

---

## VCV Statements

Examples of aggregate classification `Statement` records produced by rolling up SCV submissions through the aggregation hierarchy. Each file holds the whole hierarchy: the top statement and, as statements of their own, every layer listed below (for example `VCV000012582.69-G-PATH-CP`), each with its proposition, evidence lines and condition records. The SCVs stay `#/scv/` pointers; an SCV count is the number of pointers in that layer's evidence lines.

### Germline

| Example | VCV | Prop Type | Submission Levels | Description |
| --- | --- | --- | --- | --- |
| [Criteria-provided submissions outrank those without criteria; the condition is a set made for the aggregate](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/vcv/VCV000012582.69-G-PATH.jsonc)<br>`VCV000012582.69-G-PATH.jsonc` | VCV000012582 | Pathogenicity | CP, NOCP | Pathogenic/Likely pathogenic. CP contributing with 15 concordant SCVs; NOCP non-contributing with 20 SCVs. The proposition `object` is an `OR` condition set of 8 members minted for the aggregate; one member is itself a ClinVar trait set (`AND`) of 12 conditions |
| [A one-submission aggregate whose condition is a ClinVar trait set](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/vcv/VCV000012582.69-G-ASSOC.jsonc)<br>`VCV000012582.69-G-ASSOC.jsonc` | VCV000012582 | Association | NOCP | Single NOCP submission; the `object` is a ClinVar trait set (`AND`) of two conditions |
| [An aggregate of one submission with no classification](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/vcv/VCV000012582.69-G-NP.jsonc)<br>`VCV000012582.69-G-NP.jsonc` | VCV000012582 | Not Provided | NOCL | Single NOCL submission for Encephalocraniocutaneous lipomatosis |
| [A practice guideline outranks the expert panel and every other submission](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/vcv/VCV000007105.214-G-PATH.jsonc)<br>`VCV000007105.214-G-PATH.jsonc` | VCV000007105 | Pathogenicity | PG, EP, CP, NOCP | Pathogenic, practice guideline. PG contributing (1 SCV); EP (1 SCV), CP (83 SCVs) and NOCP (10 SCVs) non-contributing. Cystic fibrosis |
| [An expert-panel-only drug response aggregate](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/vcv/VCV000007105.214-G-DR.jsonc)<br>`VCV000007105.214-G-DR.jsonc` | VCV000007105 | Drug Response | EP | Two expert-panel SCVs; the `object` is an `OR` condition set of two drug-response conditions |
| [A single risk factor submission without assertion criteria](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/vcv/VCV000007105.214-G-RF.jsonc)<br>`VCV000007105.214-G-RF.jsonc` | VCV000007105 | Risk Factor | NOCP | Single NOCP submission for a bronchiectasis modifier condition |
| [Several submissions with no classification, across three conditions](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/vcv/VCV000007105.214-G-NP.jsonc)<br>`VCV000007105.214-G-NP.jsonc` | VCV000007105 | Not Provided | NOCL | Four NOCL SCVs; the `object` is an `OR` condition set of three conditions |

### Somatic

| Example | VCV | Prop Type | Tiers | Description |
| --- | --- | --- | --- | --- |
| [Somatic clinical impact in three layers: Tier I counts, Tier II does not](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/vcv/VCV000012582.69-S-SCI.jsonc)<br>`VCV000012582.69-S-SCI.jsonc` | VCV000012582 | Somatic Clinical Impact | Tier I, Tier II | Aggregate Contribution → Priority Grouping → Classification Grouping hierarchy, three levels of statements. `-CP` contributes; under it `-CP-T1` (Tier I, 7 SCVs) contributes and `-CP-T2` (Tier II, 3 SCVs) does not. `-NOCP` is non-contributing, with `-NOCP-T1` (Tier I, 1 SCV) under it |
| [Somatic oncogenicity in two layers, with no tier layer](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/vcv/VCV000012582.69-S-ONCO.jsonc)<br>`VCV000012582.69-S-ONCO.jsonc` | VCV000012582 | Oncogenicity | N/A | Somatic oncogenicity aggregate (Aggregate Contribution → Classification Grouping). Single CP submission, no priority grouping |

### Practice Guideline and Expert Panel Submissions { #pg-and-ep-single-submission-levels }

PG (practice guideline) and EP (reviewed by expert panel) submissions are aggregated as separate top-tier submission levels. PG outranks EP in the Aggregate Contribution Layer winner-takes-all selection, followed by CP, NOCP, NOCL, and FLAG. `VCV000007105.214-G-PATH` shows a PG winner with EP, CP and NOCP non-contributing; `VCV000007105.214-G-DR` shows an EP-only aggregate.

See [VCV Statements output reference](../output-reference/vcv-statements.md) for field documentation.

---

## RCV Statements

Examples of RCV `Statement` records: the aggregate for one variant and one condition (or condition set), built with the same layers as VCV statements. As with the VCV files, each file holds the top statement and every layer listed below as a statement, and the SCVs stay `#/scv/` pointers.

### Germline

| Example | RCV | Variant | Prop Type | Condition | Description |
| --- | --- | --- | --- | --- | --- |
| [A practice guideline aggregate for one condition](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV000007523.120-G-PATH.jsonc)<br>`RCV000007523.120-G-PATH.jsonc` | RCV000007523 | Variation 7105 | Pathogenicity | Cystic fibrosis | PG contributing (1 SCV); EP (1), CP (45) and NOCP (4) non-contributing |
| [No-classification submissions for one condition](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV000007523.120-G-NP.jsonc)<br>`RCV000007523.120-G-NP.jsonc` | RCV000007523 | Variation 7105 | Not Provided | Cystic fibrosis | NOCL, 2 SCVs |
| [An expert panel drug response for one drug combination](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV001787370.11-G-DR.jsonc)<br>`RCV001787370.11-G-DR.jsonc` | RCV001787370 | Variation 7105 | Drug Response | ivacaftor / lumacaftor response - Efficacy | EP, 1 SCV |
| [The same variant's drug response for another drug combination](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV001787371.11-G-DR.jsonc)<br>`RCV001787371.11-G-DR.jsonc` | RCV001787371 | Variation 7105 | Drug Response | ivacaftor / tezacaftor response - Efficacy | EP, 1 SCV |
| [Criteria-provided submissions outrank one without criteria, for one condition](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV000029215.25-G-PATH.jsonc)<br>`RCV000029215.25-G-PATH.jsonc` | RCV000029215 | KRAS (variation 12582) | Pathogenicity | Linear nevus sebaceous syndrome | CP contributing (4 SCVs); NOCP non-contributing (1) |
| [An aggregate whose condition is "not provided"](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV000272938.40-G-PATH.jsonc)<br>`RCV000272938.40-G-PATH.jsonc` | RCV000272938 | KRAS (variation 12582) | Pathogenicity | not provided | CP contributing (4 SCVs); NOCP non-contributing (1) |
| [Two criteria-provided submissions that agree](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV000548006.14-G-PATH.jsonc)<br>`RCV000548006.14-G-PATH.jsonc` | RCV000548006 | KRAS (variation 12582) | Pathogenicity | RASopathy | CP, 2 SCVs |
| [One criteria-provided submission outranks two without criteria](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV000585796.12-G-PATH.jsonc)<br>`RCV000585796.12-G-PATH.jsonc` | RCV000585796 | KRAS (variation 12582) | Pathogenicity | Cerebral arteriovenous malformation | CP contributing (1 SCV); NOCP non-contributing (2) |
| [A single likely pathogenic submission](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV004018620.1-G-PATH.jsonc)<br>`RCV004018620.1-G-PATH.jsonc` | RCV004018620 | KRAS (variation 12582) | Pathogenicity | Cardiovascular phenotype | Likely pathogenic, CP, 1 SCV |
| [A single criteria-provided submission for one condition](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV004554600.1-G-PATH.jsonc)<br>`RCV004554600.1-G-PATH.jsonc` | RCV004554600 | KRAS (variation 12582) | Pathogenicity | Congenital Pulmonary Airway Malformations | CP, 1 SCV |
| [An aggregate whose condition is a ClinVar trait set of 12 conditions](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV005007840.1-G-PATH.jsonc)<br>`RCV005007840.1-G-PATH.jsonc` | RCV005007840 | KRAS (variation 12582) | Pathogenicity | ClinVar trait set of 12 conditions (`AND`) | CP, 1 SCV; the `object` is a `#/conditionSet/` reference |
| [An association aggregate whose condition is a two-condition trait set](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV003327361.6-G-ASSOC.jsonc)<br>`RCV003327361.6-G-ASSOC.jsonc` | RCV003327361 | KRAS (variation 12582) | Association | ClinVar trait set of 2 conditions (`AND`) | NOCP, 1 SCV |
| [One submission with no classification](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV001839445.10-G-NP.jsonc)<br>`RCV001839445.10-G-NP.jsonc` | RCV001839445 | KRAS (variation 12582) | Not Provided | Encephalocraniocutaneous lipomatosis | NOCL, 1 SCV |
| [Conflicting classifications, with a neutral direction](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV001781420.15-G-PATH.jsonc)<br>`RCV001781420.15-G-PATH.jsonc` | RCV001781420 | Variation 97850 | Pathogenicity | Inflammatory bowel disease 1 | Conflicting classifications of pathogenicity, CP, 2 SCVs; `neutral` direction |

### Somatic

| Example | RCV | Variant | Prop Type | Condition | Description |
| --- | --- | --- | --- | --- | --- |
| [Somatic oncogenicity for one tumor type](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV004668724.2-S-ONCO.jsonc)<br>`RCV004668724.2-S-ONCO.jsonc` | RCV004668724 | KRAS (variation 12582) | Oncogenicity | Neoplasm | Oncogenic, CP, 1 SCV |
| [A Tier I diagnostic claim for one tumor type](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV006253518.1-S-SCI.jsonc)<br>`RCV006253518.1-S-SCI.jsonc` | RCV006253518 | KRAS (variation 12582) | Somatic Clinical Impact | Precursor B-cell acute lymphoblastic leukemia | Tier I diagnostic, CP, 1 SCV |
| [A Tier I diagnostic claim for one tumor type](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV006253519.1-S-SCI.jsonc)<br>`RCV006253519.1-S-SCI.jsonc` | RCV006253519 | KRAS (variation 12582) | Somatic Clinical Impact | Papillary thyroid carcinoma | Tier I diagnostic, CP, 1 SCV |
| [A Tier I diagnostic claim for one tumor type](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV006253521.1-S-SCI.jsonc)<br>`RCV006253521.1-S-SCI.jsonc` | RCV006253521 | KRAS (variation 12582) | Somatic Clinical Impact | Glioma | Tier I diagnostic, CP, 1 SCV |
| [A Tier I diagnostic claim for one tumor type](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV006253522.1-S-SCI.jsonc)<br>`RCV006253522.1-S-SCI.jsonc` | RCV006253522 | KRAS (variation 12582) | Somatic Clinical Impact | Embryonal rhabdomyosarcoma | Tier I diagnostic, CP, 1 SCV |
| [A Tier I diagnostic claim for one tumor type](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV006253523.1-S-SCI.jsonc)<br>`RCV006253523.1-S-SCI.jsonc` | RCV006253523 | KRAS (variation 12582) | Somatic Clinical Impact | Diffuse pediatric-type high-grade glioma, H3-wildtype and IDH-wildtype | Tier I diagnostic, CP, 1 SCV |
| [A Tier I diagnostic claim for one tumor type](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV006253525.1-S-SCI.jsonc)<br>`RCV006253525.1-S-SCI.jsonc` | RCV006253525 | KRAS (variation 12582) | Somatic Clinical Impact | Adenocarcinoma of the large intestine | Tier I diagnostic, CP, 1 SCV |
| [A Tier I diagnostic claim for one tumor type](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV006253527.1-S-SCI.jsonc)<br>`RCV006253527.1-S-SCI.jsonc` | RCV006253527 | KRAS (variation 12582) | Somatic Clinical Impact | Ovarian mucinous adenocarcinoma | Tier I diagnostic, CP, 1 SCV |
| [A Tier I diagnostic claim for one tumor type](https://github.com/clingen-data-model/clinvar-gkm/blob/main/examples/rcv/RCV006254391.1-S-SCI.jsonc)<br>`RCV006254391.1-S-SCI.jsonc` | RCV006254391 | Variation 2758242 | Somatic Clinical Impact | Medulloblastoma WNT activated | Tier I diagnostic, CP, 1 SCV |

The somatic clinical impact RCVs follow the Aggregate Contribution → Priority Grouping → Classification Grouping hierarchy, so each file holds three statements: the top statement, `-CP` and `-CP-T1`.

See [RCV Statements output reference](../output-reference/rcv-statements.md) for field documentation.

---

## See Also { #see-also }

- [Output Format](../output-reference/overview.md) — the bundle's sections and how records point to each other
- [ID References](../output-reference/id-references.md) — every identifier and pointer pattern
- [Sub-Bundle Extraction](../pipeline/sub-bundle.md) — cut your own closed extract of a few statements
