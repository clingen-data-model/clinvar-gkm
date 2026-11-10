# ClinvarProteinExpression

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The protein HGVS expression of a HgvsListItem: an HGVS syntax and the expression text. No id, extensions or syntax version.

**JSON Schema:** [ClinvarProteinExpression](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarProteinExpression){ target=_blank }

Some ClinvarProteinExpression attributes are inherited from [Expression](https://va-spec.ga4gh.org/en/1.1.0/appendices/imported-models/expression.html#expression){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `syntax` | `string`<br>one of `hgvs.g`, `hgvs.m`, `hgvs.c`, `hgvs.n`, `hgvs.r`, `hgvs.p` | 1..1 | `hgvs.` and the HGVS type letter of the expression (`hgvs.p`). |
| `value` | `string` | 1..1 | The expression of the variation in the specified syntax. The value should be a valid expression in the specified syntax. |

**Not used by ClinVar-GKM:** `id`, `extensions`, `syntax_version`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

