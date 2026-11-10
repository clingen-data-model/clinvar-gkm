# ClinvarDocument

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A Document as ClinVar-GKM writes it for a ClinVar citation: its PubMed id, DOI and URLs, the name and document type when ClinVar gives them, and extensions that keep ClinVar's citation text and record repairs of its ids. No id, title, description or aliases.

**JSON Schema:** [ClinvarDocument](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarDocument){ target=_blank }

Some ClinvarDocument attributes are inherited from [Document](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/entities/information-entities/document.html#document){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`Document` | 1..1 | Must be "Document" |
| `name` | `string` | 0..1 | A primary name for the entity. |
| `extensions` | [ExtensionClinvarCitationText](ClinvarDocument.md#extensionclinvarcitationtext) \| [ExtensionOriginalClinvarCitation](ClinvarDocument.md#extensionoriginalclinvarcitation) \| [ExtensionOriginalClinvarCitationSource](ClinvarDocument.md#extensionoriginalclinvarcitationsource) \| [ExtensionCitationRepaired](ClinvarDocument.md#extensioncitationrepaired) \| [ExtensionClinvarDoi](ClinvarDocument.md#extensionclinvardoi) \| [ExtensionInvalidClinvarCitation](ClinvarDocument.md#extensioninvalidclinvarcitation) \| [ExtensionUnmappedClinvarCitation](ClinvarDocument.md#extensionunmappedclinvarcitation)[] (unordered) | 0..m | ClinVar's citation text, the record of any repair of the citation's id, and ids that are invalid or from an unmapped source. |
| `documentType` | `string` (draft) | 0..1 | A specific type of document that a Document instance represents (e.g.  'publication', 'patent', 'pathology report') |
| `urls` | `string`[] (unordered)<br>pattern `^(https?|s?ftp)://` | 0..m | One or more URLs from which the content of the Document can be retrieved. |
| `doi` | `string`<br>pattern `^10.(\d+)(\.\d+)*/[\w\-\.]+` | 0..1 | A `Digital Object Identifier <https://www.doi.org/the-identifier/what-is-a-doi/>`_ for the document. |
| `pmid` | `string` | 0..1 | A `PubMed unique identifier <https://en.wikipedia.org/wiki/PubMed#PubMed_identifier>`_ for the document. |

**Not used by ClinVar-GKM:** `id`, `description`, `aliases`, `title`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

## Extensions

These extensions are defined for `ClinvarDocument`.

### ExtensionCitationRepaired

Says that ClinVar-GKM repaired the citation's id.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`citationRepaired` | 0..1 | Must be 'citationRepaired'. |
| `value` | `boolean`<br>`true` | 0..1 | Always true. |

### ExtensionClinvarCitationText

The free text of a ClinVar citation. A citation that is only text is a Document whose only content is this extension.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`clinvarCitationText` | 0..1 | Must be 'clinvarCitationText'. |
| `value` | `string` | 0..1 | The citation text, verbatim. |

### ExtensionClinvarDoi

A valid DOI that VA-Spec's doi pattern rejects (a SICI DOI, say). The document's doi stays empty and the DOI's doi.org URL is in urls.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`clinvarDoi` | 0..1 | Must be 'clinvarDoi'. |
| `value` | `string` | 0..1 | The DOI as ClinVar has it. |

### ExtensionInvalidClinvarCitation

A citation id that cannot be used (a DOI of "https", say). No doi or URL is derived from it.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`invalidClinvarCitation` | 0..1 | Must be 'invalidClinvarCitation'. |
| `value` | `string` | 0..1 | ClinVar's citation id. |

### ExtensionOriginalClinvarCitation

The citation id as ClinVar has it, when ClinVar-GKM repaired it.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`originalClinvarCitation` | 0..1 | Must be 'originalClinvarCitation'. |
| `value` | `string` | 0..1 | ClinVar's citation id. |

### ExtensionOriginalClinvarCitationSource

ClinVar's source of a citation id that ClinVar-GKM moved to another source.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`originalClinvarCitationSource` | 0..1 | Must be 'originalClinvarCitationSource'. |
| `value` | `string` | 0..1 | ClinVar's citation source. |

### ExtensionUnmappedClinvarCitation

A citation id from a source ClinVar-GKM does not map ('<source>:<id>'). No doi, pmid or URL is derived from it.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`unmappedClinvarCitation` | 0..1 | Must be 'unmappedClinvarCitation'. |
| `value` | `string` | 0..1 | ClinVar's citation source and id, as '<source>:<id>'. |

