.. admonition:: Draft
    :class: warning

    May change significantly in future releases. See |maturity-model|.

**Computational Definition**

Any proposition type valid in ClinVar-GKM statements. Includes the GA4GH standard proposition types (pathogenicity, oncogenicity, clinical significance) and ClinVar-specific proposition types for submission categories not covered by the GA4GH specifications.

**Information Model**

This class must match **one of** the following:

* :ref:`VariantPathogenicityProposition`
* :ref:`VariantOncogenicityProposition`
* :ref:`VariantClinicalSignificanceProposition`
* :ref:`ClinvarRiskFactorProposition`
* :ref:`ClinvarProtectiveProposition`
* :ref:`ClinvarDrugResponseProposition`
* :ref:`ClinvarAffectsProposition`
* :ref:`ClinvarAssociationProposition`
* :ref:`ClinvarConfersSensitivityProposition`
* :ref:`ClinvarOtherProposition`
* :ref:`ClinvarNotProvidedProposition`
* :ref:`ClinvarConflictingDataFromSubmitterProposition`
* :ref:`ClinvarUndefinedProposition`


**Used in:** :ref:`ClinvarAggregateStatementProperties`, :ref:`ClinvarScvStatementProperties`
