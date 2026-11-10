.. admonition:: Draft
    :class: warning

    May change significantly in future releases. See |maturity-model|.

**Computational Definition**

A somatic clinical impact proposition of the propositionSomaticClinicalImpact section: a VariantClinicalSignificanceProposition whose subject is a variation pointer and whose object is a condition or condition set pointer. SCV propositions may carry a gene context qualifier. No name, description, aliases, extensions or allele origin qualifier.

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
      - MUST be "VariantClinicalSignificanceProposition".
   *  - subject
      -
      - :ref:`iriReference`
      - 1..1
      - The variant, a '#/variation/<id>' pointer into this bundle.
   *  - predicate
      -
      - string
      - 1..1
      - The predicate associating the subject variant to clinical significance for the object Condition. MUST be "hasClinicalSignificanceFor".
   *  - object
      -
      - :ref:`iriReference`
      - 1..1
      - The condition, a '#/condition/<id>' or '#/conditionSet/<id>' pointer into this bundle.
   *  - geneContextQualifier
      -
      - :ref:`ClinvarGeneContextQualifier`
      - 0..1
      - The variant's gene (SCV propositions only).

**Composes:** :ref:`VariantClinicalSignificanceProposition`
