.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A custom proposition describing the protective role of a variant against a condition. Used for ClinVar submissions classified as "protective". ClinVar has stopped accepting new submissions with this classification, but historical submissions remain.

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
      - MUST be "ClinvarProtectiveProposition".
   *  - subject
      -
      - :ref:`iriReference`
      - 1..1
      - A variant that is the subject of the Proposition.
   *  - predicate
      -
      - string
      - 1..1
      - The relationship the Proposition describes between the subject variant and object condition. MUST be "isProtectiveFor".
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

**Composes:** :ref:`ClinvarGermlineCustomProposition`
