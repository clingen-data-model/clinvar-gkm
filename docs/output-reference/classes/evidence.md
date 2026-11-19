# Evidence Lines

Evidence lines in ClinVar-GKM are stored in the `evidenceLine` bundle section and referenced from statements via `hasEvidenceLines` arrays of `#/evidenceLine/` JSON pointer strings. There are three underlying dict tables that are merged into the single bundle section: `gkm_dict_evidence_line` (SCV), `gkm_dict_vcv_evidence_line` (VCV), and `gkm_dict_rcv_evidence_line` (RCV).

SCV evidence lines appear only on somatic clinical impact (SCI) statements, linking the parent `VariantClinicalSignificanceProposition` to a specific clinical assertion type — therapeutic response, diagnostic, or prognostic. VCV and RCV evidence lines connect aggregate statements to their contributing and non-contributing evidence items at each aggregation layer.

Two ClinVar profiles narrow the VA-Spec `EvidenceLine`, and the bundle schema picks one by the record's key:

| ClinVar Profile | Key Pattern | Used By |
| --- | --- | --- |
| [ClinvarSomaticEvidenceLine](ClinvarSomaticEvidenceLine.md) | `clinvar.submission:{scv_id}.{ver}` | Somatic clinical impact SCV statements |
| [ClinvarAggregateEvidenceLine](ClinvarAggregateEvidenceLine.md) | `{vcv_or_rcv_id}.contributing` or `{vcv_or_rcv_id}.non-contributing` | VCV and RCV aggregate statements |

---

## When Evidence Lines Appear

| Statement Category | Has Evidence Lines? |
| --- | --- |
| Germline classification (PATH, RF, PROTECT, etc.) | No |
| Oncogenicity (ONCO) | No |
| Somatic clinical impact (SCI) — Tier I or II | Yes |
| Somatic clinical impact (SCI) — Tier III or IV | No (no clinical assertion type) |

Evidence lines are present only on Tier I and Tier II SCI statements, where ClinVar requires at least one clinical assertion type (therapeutic response, diagnostic, or prognostic) to support the tier classification.

---

## Target Propositions

Each somatic evidence line carries a `targetProposition` specifying the clinical assertion type, as a `#/propositionSomaticClinicalImpact/` pointer. The target is one of these GA4GH VA-Spec standard types:

| Code | Type | ClinVar Profile | Predicates | Description |
| --- | --- | --- | --- | --- |
| `TR` | VariantTherapeuticResponseProposition | [ClinvarVariantTherapeuticResponseProposition](ClinvarVariantTherapeuticResponseProposition.md) | `predictsSensitivityTo`, `predictsResistanceTo` | Response to a specific therapy |
| `DIAG` | VariantDiagnosticProposition | [ClinvarVariantDiagnosticProposition](ClinvarVariantDiagnosticProposition.md) | `isDiagnosticInclusionCriterionFor`, `isDiagnosticExclusionCriterionFor` | Diagnostic relevance |
| `PROG` | VariantPrognosticProposition | [ClinvarVariantPrognosticProposition](ClinvarVariantPrognosticProposition.md) | `associatedWithBetterOutcomeFor`, `associatedWithWorseOutcomeFor` | Prognostic significance |

A somatic evidence line's `directionOfEvidenceProvided` is always `supports`. It carries no evidence items, strength, or score.

---

## Evidence Outcome

The `evidenceOutcome` field — a [ClinvarTerm](ClinvarTerm.md) whose `conceptType` is `Outcome` — maps the AMP/ASCO/CAP tier to an evidence level:

| Tier | Evidence Outcome |
| --- | --- |
| Tier I - Strong | `Level A/B` |
| Tier II - Potential | `Level C/D` |

---

## Relationship to Parent Statement

An SCI statement's structure connects the tiers to the clinical assertions:

```
SCV Statement
├── proposition: #/propositionSomaticClinicalImpact/{scv_id}-SCI
│   └── VariantClinicalSignificanceProposition (hasClinicalSignificanceFor)
├── classification: "Tier I - Strong"
└── hasEvidenceLines: #/evidenceLine/clinvar.submission:{scv_id}.{ver}
    └── ClinvarSomaticEvidenceLine
        ├── targetProposition: #/propositionSomaticClinicalImpact/{scv_id}-TR
        │   └── VariantTherapeuticResponseProposition (predictsSensitivityTo)
        ├── evidenceOutcome: "Level A/B"
        └── directionOfEvidenceProvided: "supports"
```

The parent statement asserts clinical significance (the tier), while the evidence line specifies *what kind* of clinical significance — which therapy, diagnostic criterion, or prognostic outcome the variant is relevant for.

---

## Aggregate Evidence Lines

A [ClinvarAggregateEvidenceLine](ClinvarAggregateEvidenceLine.md) groups the statements a VCV or RCV aggregate statement is built from:

| Line | `directionOfEvidenceProvided` | `strengthOfEvidenceProvided` | `hasEvidenceItems` |
| --- | --- | --- | --- |
| `{id}.contributing` | `supports` | `Contributing` | The statements the aggregate is built from |
| `{id}.non-contributing` | `neutral` | `Non-contributing` | Statements of a lower review-status priority that did not contribute |

Each item is a `#/scv/`, `#/vcv/`, or `#/rcv/` pointer. The strength is a [ClinvarTerm](ClinvarTerm.md) whose `conceptType` is `Strength`. Aggregate evidence lines carry no target proposition, evidence outcome, or extensions.

---

## Extensions

Somatic evidence lines also carry a `submittedCondition` or `submittedConditionSet` extension with the submitter's original condition details. Their values are a [SubmittedCondition](SubmittedCondition.md) or a [SubmittedConditionSet](SubmittedConditionSet.md), the same structures the SCV statement's extensions carry.
