.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A custom proposition type for ClinVar germline submissions that do not have a corresponding GA4GH VA-Spec proposition type. Includes ClinVar submission categories such as "risk factor", "protective", "drug response", "affects", "association", "confers sensitivity", "other", "not provided", and "conflicting data from submitters". These custom proposition types are used to represent variant-condition associations in ClinVar. No name, description, aliases or extensions.

**Information Model**


.. list-table::
   :class: clean-wrap
   :header-rows: 1
   :align: left
   :widths: auto

   *  - Field
      - Flags
      - Type
      - Limits
      - Description
   *  - id
      -
      - string
      - 0..1
      - The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another.
   *  - type
      -
      - string
      - 1..1
      - The name of the class that is instantiated by a data object representing the Entity.
   *  - subject
      -
      - :ref:`iriReference`
      - 1..1
      - A variant that is the subject of the Proposition.
   *  - predicate
      -
      - string
      - 1..1
      - The relationship declared to hold between the subject and the object of the Proposition.
   *  - object
      -
      - :ref:`iriReference`
      - 1..1
      - An Entity or concept that is related to the subject of a Proposition via its predicate.
   *  - geneContextQualifier
      -
      - :ref:`ClinvarGeneContextQualifier`
      - 0..1
      - Reports a gene impacted by the variant, which may contribute to the association described in the Proposition (SCV propositions only).
   *  - modeOfInheritanceQualifier
      -
      - :ref:`ClinvarModeOfInheritanceQualifier`
      - 0..1
      - Reports a pattern of inheritance expected for the effect of the variant (SCV propositions only).
   *  - penetranceQualifier
      -
      - :ref:`ClinvarPenetranceQualifier`
      - 0..1
      - Reports the penetrance of the effect - the extent to which the variant impact is expressed by carriers (SCV propositions only).

**Composes:** :ref:`SubjectVariantProposition`, :ref:`ClinvarGermlineCustomPropositionProperties`

**Used in:** :ref:`ClinvarAffectsProposition`, :ref:`ClinvarAssociationProposition`, :ref:`ClinvarConfersSensitivityProposition`, :ref:`ClinvarConflictingDataFromSubmitterProposition`, :ref:`ClinvarDrugResponseProposition`, :ref:`ClinvarNotProvidedProposition`, :ref:`ClinvarOtherProposition`, :ref:`ClinvarProtectiveProposition`, :ref:`ClinvarRiskFactorProposition`, :ref:`ClinvarUndefinedProposition`
