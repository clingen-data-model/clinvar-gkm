# ClinvarSomaticEvidenceLine

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.0/appendices/maturity_model.html){ target=_blank rel=noopener }.

An evidence line for ClinVar somatic clinical impact (SCI) statements. Carries a target proposition (therapeutic response, diagnostic, or prognostic) and an evidence outcome reflecting the AMP/ASCO/CAP tiered classification. SCI statements use this evidence line to link the parent VariantClinicalSignificanceProposition to specific clinical assertion types.

**JSON Schema:** [ClinvarSomaticEvidenceLine](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarSomaticEvidenceLine){ target=_blank }

Some ClinvarSomaticEvidenceLine attributes are inherited from [EvidenceLine](https://va-spec.ga4gh.org/en/latest/core-information-model/entities/information-entities/evidence-line.html#evidenceline){ target=_blank rel=noopener }, `ClinvarSomaticEvidenceLineProperties`.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 0..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string` | 0..1 | MUST be "EvidenceLine". |
| `name` | `string` | 0..1 | A primary name for the entity. |
| `description` | `string` | 0..1 | A free-text description of the Entity. |
| `aliases` | `string`[] (unordered) | 0..m | Alternative name(s) for the Entity. |
| `extensions` | [Extension](https://va-spec.ga4gh.org/en/latest/core-information-model/elements/extension.html#extension){ target=_blank rel=noopener }[] (unordered) | 0..m | A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model. |
| `specifiedBy` | [Method](https://va-spec.ga4gh.org/en/latest/core-information-model/entities/information-entities/method.html#method){ target=_blank rel=noopener } \| [iriReference](https://va-spec.ga4gh.org/en/latest/core-information-model/data-types.html#irireference){ target=_blank rel=noopener } | 0..1 | A specification that describes all or part of the process that led to creation of the Information Entity |
| `contributions` | [Contribution](https://va-spec.ga4gh.org/en/latest/core-information-model/entities/contribution.html#contribution){ target=_blank rel=noopener }[] (ordered) | 0..m | Specific actions taken by an Agent toward the creation, modification, validation, or deprecation of an Information Entity. |
| `reportedIn` | [Document](https://va-spec.ga4gh.org/en/latest/core-information-model/entities/information-entities/document.html#document){ target=_blank rel=noopener } \| [iriReference](https://va-spec.ga4gh.org/en/latest/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }[] (unordered) | 0..m | A document in which the the Information Entity is reported. |
| `targetProposition` | [VariantTherapeuticResponseProposition](https://va-spec.ga4gh.org/en/latest/va-standard-profiles/base-profiles/proposition-profiles.html#varianttherapeuticresponseproposition){ target=_blank rel=noopener } \| [VariantDiagnosticProposition](https://va-spec.ga4gh.org/en/latest/va-standard-profiles/base-profiles/proposition-profiles.html#variantdiagnosticproposition){ target=_blank rel=noopener } \| [VariantPrognosticProposition](https://va-spec.ga4gh.org/en/latest/va-standard-profiles/base-profiles/proposition-profiles.html#variantprognosticproposition){ target=_blank rel=noopener } \| [iriReference](https://va-spec.ga4gh.org/en/latest/core-information-model/data-types.html#irireference){ target=_blank rel=noopener } | 0..1 | The target proposition for this evidence line. For somatic clinical impact statements, this is one of the specific assertion type propositions: VariantTherapeuticResponseProposition (TR), VariantDiagnosticProposition (DIAG), or VariantPrognosticProposition (PROG). |
| `hasEvidenceItems` | [InformationEntity](https://va-spec.ga4gh.org/en/latest/core-information-model/entities/information-entities/index.html#informationentity){ target=_blank rel=noopener } \| [iriReference](https://va-spec.ga4gh.org/en/latest/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }[] (unordered) | 0..m | An individual piece of information that was evaluated as evidence in building the argument represented by an Evidence Line. |
| `directionOfEvidenceProvided` | `string` | 0..1 | The direction of support that the Evidence Line is determined to provide toward its target Proposition (supports, disputes, neutral) |
| `strengthOfEvidenceProvided` | [MappableConcept](https://va-spec.ga4gh.org/en/latest/core-information-model/elements/mappable-concept.html#mappableconcept){ target=_blank rel=noopener } \| [iriReference](https://va-spec.ga4gh.org/en/latest/core-information-model/data-types.html#irireference){ target=_blank rel=noopener } | 0..1 | The strength of support that an Evidence Line is determined to provide for or against its target Proposition, evaluated relative to the direction indicated by the directionOfEvidenceProvided value. |
| `scoreOfEvidenceProvided` | `number` | 0..1 | A quantitative score indicating the strength of support that an Evidence Line is determined to provide for or against its target Proposition, evaluated relative to the direction indicated by the directionOfEvidenceProvided value. |
| `evidenceOutcome` | [MappableConcept](https://va-spec.ga4gh.org/en/latest/core-information-model/elements/mappable-concept.html#mappableconcept){ target=_blank rel=noopener } | 0..1 | The evidence level outcome for the somatic clinical impact assertion, based on the AMP/ASCO/CAP tiered evidence framework. Values reflect the tier mapping (e.g., "Level A/B" for Tier I, "Level C/D" for Tier II). Present only on somatic clinical impact evidence lines. |

