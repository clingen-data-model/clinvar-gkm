# Propositions (Steps 2--6)

## Overview

Steps 2--6 of `gkm_scv_statement_proc` build the qualifier tables and assemble the primary and target propositions for each SCV. Qualifiers capture gene context, mode of inheritance, and penetrance; propositions combine the variant, condition, and qualifiers into the structured assertion that forms the core of each VA-Spec Statement.

---

## Steps 2--4: Qualifier Tables

### Step 2: Build `temp_gene_context_qualifiers`

Extracts gene context from the upstream `single_gene_variation` table: one representative gene per variant, chosen by the [single-gene method](https://github.com/clingen-data-model/clinvar-ingest-bq-tools/blob/main/docs/methods/single-gene-variation.md) in clinvar-ingest-bq-tools. The gene's `symbol` and `hgnc_id` come from that same table, so this step joins no gene table of its own. For each SCV whose variant has a row, it builds a gene concept with:

- **conceptType**: `"gene"`
- **primaryCoding**: NCBI Gene identifier using both `identifiers.org` and NCBI Gene URLs
- **HGNC mappings**: When an HGNC identifier is available, included as an additional coding
- **submittedGeneSymbols extension**: Gene symbols from `clinical_assertion_variation`, preserving the submitter's original gene annotations. Trimmed of the space a `, `-separated list leaves after the split, distinct, in submitted order: variation record, then gene list, then position in the comma-separated symbol list. That key is unique, so the order is total and an incremental build matches a full one.
- **geneContextSource extension**: Where the gene came from. The submitter's symbols never choose the gene; they only set this value. They are compared with the gene's symbol after trimming spaces and ignoring case:
    - `submittedSymbolMatches` — the submitter's symbols include the gene's symbol
    - `submittedSymbolDiffers` — the submitter gave symbols, none equal to it (mostly previous symbols of the same gene)
    - `inferredFromVariant` — the submitter gave no symbols

When no single-gene match exists for a variation but the submitter gave symbols, the qualifier is a placeholder. Its `name` is the submitter's symbol: several are joined with `, ` in submitted order. It has no `primaryCoding` or `mappings`, keeps `submittedGeneSymbols`, and has `geneContextSource` = `submittedNotNormalized`. Releases before 1.1.0 name the placeholder `submitted genes were not normalized`.

The schema accepts only these four `geneContextSource` values. `ClinvarGeneContextQualifier` defines them, and the bundle schema applies it to every proposition type, including the VA-Spec ones.

The extension values are stored as typed fields (`value_string` for the symbol array, `value_enum` for the source) and collapsed to `value` at publish.

**Output:** `temp_gene_context_qualifiers` -- one row per SCV+gene combination. <span class="role-badge badge-internal">Internal</span>

---

### Step 3: Build `temp_moi_qualifiers`

Extracts ModeOfInheritance from assertion attributes in `clinical_assertion`. When a matching HPO term is available, the qualifier includes a `primaryCoding` with the HPO term identifier and label. All qualifiers include a `submittedModeOfInheritance` extension preserving the original submitted value.

**Output:** `temp_moi_qualifiers` -- one row per SCV with mode of inheritance. <span class="role-badge badge-internal">Internal</span>

---

### Step 4: Build `temp_penetrance_qualifiers`

Derives penetrance qualifiers for specific classification types:

| Classification Category | Penetrance Value |
|---|---|
| Pathogenic-low penetrance (`p-lp`), Likely pathogenic-low penetrance (`lp-lp`) | `"low"` |
| Established risk allele (`era`), Likely risk allele (`lra`), Uncertain risk allele (`ura`) | `"risk"` |

Each penetrance qualifier includes a `submittedClassification` extension preserving the original classification label that triggered the penetrance derivation.

**Output:** `temp_penetrance_qualifiers` -- one row per qualifying SCV. <span class="role-badge badge-internal">Internal</span>

---

## Step 5: Primary Proposition

Assembles the SCV proposition by joining `temp_gkm_scv` with all qualifier tables and condition sets from `gkm_scv_condition_sets`. The resulting proposition contains:

| Field | Description |
|---|---|
| `type` | Proposition type from Step 1 mapping (e.g., `VariantPathogenicityProposition`) |
| `subject` | Reference to the categorical variant via `clinvar:{variation_id}` |
| `predicate` | Predicate from Step 1 mapping (e.g., `isCausalFor`, `isOncogenicFor`) |
| `object_single` | Single condition from the condition pipeline |
| `object_compound` | ConditionSet for SCVs with multiple conditions |
| `geneContextQualifier` | Gene concept from Step 2 |
| `modeOfInheritanceQualifier` | Mode of inheritance from Step 3 |
| `penetranceQualifier` | Penetrance from Step 4 |

**Output:** `temp_gkm_scv_proposition` -- one row per SCV with fully assembled proposition. <span class="role-badge badge-internal">Internal</span>

---

## Step 6: Target Proposition (Somatic)

Builds the evidence line target proposition for somatic clinical impact assertions. This proposition uses the `evidence_line_target_proposition` type and predicate derived in Step 1 and adds somatic-specific fields:

| Field | Description |
|---|---|
| `type` | Target proposition type (e.g., `VariantPrognosticProposition`, `VariantTherapeuticResponseProposition`) |
| `subject` | JSON pointer `4/proposition/subject` referencing the parent proposition's variant |
| `predicate` | Target predicate (e.g., `associatedWithBetterOutcomeFor`, `predictsSensitivityTo`) |
| `object` | For therapeutic assertions, a reference to the therapy: `#/therapy/clinvar.therapy:{sha256}` for a single drug, or `#/therapyGroup/clinvar.therapygroup:{sha256}` for a multi-drug combination. Therapies are extracted (`temp_gkm_scv_therapy`), content-addressed, and deduplicated into the `gkm_dict_therapy` / `gkm_dict_therapygroup` dictionaries; a TherapyGroup's `concepts` reference its member therapies via `#/therapy/` |
| `conditionQualifier` | Condition moved to qualifier position for therapeutic assertions (since `object` becomes the therapy), as a `#/condition/` or `#/conditionSet/` reference |
| `geneContextQualifier` | Gene concept from Step 2 |
| `modeOfInheritanceQualifier` | Mode of inheritance from Step 3 |

The JSON pointer `4/proposition/subject` is used instead of duplicating the variant reference, linking the target proposition back to the same variant defined in the parent (Step 5) proposition.

**Output:** `temp_gkm_scv_target_proposition` -- one row per somatic SCV with target proposition. <span class="role-badge badge-internal">Internal</span>

---

## Dependencies

- **Source Tables**: `single_gene_variation` (with its `symbol` and `hgnc_id` columns), `clinical_assertion`, `clinical_assertion_variation`
- **Lookup Tables**: `hpo_terms`
- **Upstream Steps**: Step 1 (`temp_gkm_scv`), condition pipeline (`gkm_scv_condition_sets`)
