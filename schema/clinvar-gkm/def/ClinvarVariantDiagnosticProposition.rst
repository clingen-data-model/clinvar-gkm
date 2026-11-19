.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The target proposition of a diagnostic somatic clinical impact SCV's evidence line, in the propositionSomaticClinicalImpact section: a VariantDiagnosticProposition whose subject is a variation pointer and whose object is a condition or condition set pointer, with the SCV's gene context qualifier. No name, description, aliases, extensions or allele origin qualifier.

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
      - 1..1
      - The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another.
   *  - type
      -
      - string
      - 1..1
      - MUST be "VariantDiagnosticProposition".
   *  - subject
      -
      - :ref:`iriReference`
      - 1..1
      - The variant, a '#/variation/<id>' pointer into this bundle.
   *  - predicate
      -
      - string
      - 1..1
      - The relationship the Proposition describes between the subject variant and object Condition. MUST be one of "isDiagnosticInclusionCriterionFor" or "isDiagnosticExclusionCriterionFor".
   *  - object
      -
      - :ref:`iriReference`
      - 1..1
      - The disease, a '#/condition/<id>' or '#/conditionSet/<id>' pointer into this bundle.
   *  - geneContextQualifier
      -
      - :ref:`ClinvarGeneContextQualifier`
      - 0..1
      - The variant's gene.

**Composes:** :ref:`VariantDiagnosticProposition`
