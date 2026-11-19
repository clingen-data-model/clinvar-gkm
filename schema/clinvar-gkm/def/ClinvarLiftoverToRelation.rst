.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The `liftover_to` relation of a ClinVar defining allele or defining location constraint: a MappableConcept with only its type and primary coding (code `liftover_to`, system `ga4gh-gks-term:allele-relation`, no IRIs).

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
   *  - type
      -
      - string
      - 1..1
      - MUST be "MappableConcept".
   *  - primaryCoding
      -
      - object
      - 1..1
      - The relation's code and system.

**Composes:** :ref:`MappableConcept`

**Used in:** :ref:`ClinvarDefiningAlleleConstraint`, :ref:`ClinvarDefiningLocationConstraint`
