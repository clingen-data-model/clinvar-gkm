# ClinvarNucleotideExpression

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The nucleotide HGVS expression of a HgvsListItem: an HGVS syntax and the expression text, with extensions only when ClinVar supplied an expression with no HGVS type letter. No id or syntax version.

**JSON Schema:** [ClinvarNucleotideExpression](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarNucleotideExpression){ target=_blank }

Some ClinvarNucleotideExpression attributes are inherited from [Expression](https://va-spec.ga4gh.org/en/1.1.0/appendices/imported-models/expression.html#expression){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `extensions` | [ExtensionInvalidClinvarExpression](ClinvarNucleotideExpression.md#extensioninvalidclinvarexpression) \| [ExtensionExpressionMerged](ClinvarNucleotideExpression.md#extensionexpressionmerged) \| [ExtensionOriginalClinvarExpression](ClinvarNucleotideExpression.md#extensionoriginalclinvarexpression) \| [ExtensionExpressionRepaired](ClinvarNucleotideExpression.md#extensionexpressionrepaired)[] (unordered) | 0..m | ClinVar's submitted text when it had no HGVS type letter: either `invalidClinvarExpression` (one per such text) and `expressionMerged`, when this is ClinVar's valid expression for the same accession, or `originalClinvarExpression` and `expressionRepaired`, when this is the repaired expression. |
| `syntax` | `string`<br>one of `hgvs.g`, `hgvs.m`, `hgvs.c`, `hgvs.n`, `hgvs.r`, `hgvs.p` | 1..1 | `hgvs.` and the HGVS type letter of the expression. |
| `value` | `string` | 1..1 | The expression of the variation in the specified syntax. The value should be a valid expression in the specified syntax. |

**Not used by ClinVar-GKM:** `id`, `syntax_version`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

## Extensions

These extensions are defined for `ClinvarNucleotideExpression`.

### ExtensionExpressionMerged

Marks a nucleotide expression that carries one or more invalidClinvarExpression extensions.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`expressionMerged` | 1..1 | Must be 'expressionMerged'. |
| `value` | `boolean`<br>`true` | 1..1 | Always `true`. |

### ExtensionExpressionRepaired

Marks a nucleotide expression that is a repair of the expression ClinVar supplied (the HGVS type letter restored).

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`expressionRepaired` | 1..1 | Must be 'expressionRepaired'. |
| `value` | `boolean`<br>`true` | 1..1 | Always `true`. |

### ExtensionInvalidClinvarExpression

A nucleotide expression ClinVar supplied with no HGVS type letter (e.g. `NC_000017.10:9481617_9489649del`), kept as submitted on ClinVar's valid expression for the same accession.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`invalidClinvarExpression` | 1..1 | Must be 'invalidClinvarExpression'. |
| `value` | `string` | 1..1 | The expression as ClinVar supplied it. |

### ExtensionOriginalClinvarExpression

The nucleotide expression as ClinVar supplied it (with no HGVS type letter), on the repaired expression listed in its place.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`originalClinvarExpression` | 1..1 | Must be 'originalClinvarExpression'. |
| `value` | `string` | 1..1 | The expression as ClinVar supplied it. |

