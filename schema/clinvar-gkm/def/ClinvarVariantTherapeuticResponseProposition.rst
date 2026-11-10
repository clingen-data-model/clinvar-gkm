.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The target proposition of a therapeutic somatic clinical impact SCV's evidence line, in the propositionSomaticClinicalImpact section: a VariantTherapeuticResponseProposition whose subject is a variation pointer, whose object is a therapy or therapy group pointer and whose condition qualifier is a condition or condition set pointer, with the SCV's gene context qualifier. No name, description, aliases, extensions or allele origin qualifier.

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
      - MUST be "VariantTherapeuticResponseProposition".
   *  - subject
      -
      - :ref:`iriReference`
      - 1..1
      - The variant, a '#/variation/<id>' pointer into this bundle.
   *  - predicate
      -
      - string
      - 1..1
      - The relationship the Proposition describes between the subject variant and object therapeutic. MUST be one of "predictsSensitivityTo" or "predictsResistanceTo".
   *  - object
      -
      - :ref:`iriReference`
      - 1..1
      - The drug, a '#/therapy/<id>' pointer, or a combination of drugs, a '#/therapyGroup/<id>' pointer into this bundle.
   *  - geneContextQualifier
      -
      - :ref:`ClinvarGeneContextQualifier`
      - 0..1
      - The variant's gene.
   *  - conditionQualifier
      -
      - :ref:`iriReference`
      - 1..1
      - The disease context, a '#/condition/<id>' or '#/conditionSet/<id>' pointer into this bundle.

**Composes:** :ref:`VariantTherapeuticResponseProposition`
