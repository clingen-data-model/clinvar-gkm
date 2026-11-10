.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A record of the propositionPathogenicity section: a VariantPathogenicityProposition whose subject is a variation pointer and whose object is a condition or condition set pointer. SCV propositions may carry gene context, mode of inheritance and penetrance qualifiers; VCV and RCV propositions carry none. No name, description, aliases, extensions or allele origin qualifier.

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
      - Must be "VariantPathogenicityProposition"
   *  - subject
      -
      - :ref:`iriReference`
      - 1..1
      - The variant, a '#/variation/<id>' pointer into this bundle.
   *  - predicate
      -
      - string
      - 1..1
      - The relationship the Proposition describes between the subject variant and object condition. MUST be "isCausalFor".
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
   *  - penetranceQualifier
      -
      - :ref:`ClinvarPenetranceQualifier`
      - 0..1
      - The penetrance implied by a low-penetrance or risk-allele classification (SCV propositions only).
   *  - modeOfInheritanceQualifier
      -
      - :ref:`ClinvarModeOfInheritanceQualifier`
      - 0..1
      - The submitted mode of inheritance (SCV propositions only).

**Composes:** :ref:`VariantPathogenicityProposition`
