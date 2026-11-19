.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The `transcribed_to` relation of a ClinVar defining allele constraint: a MappableConcept with only its type and primary coding (code `transcribed_to`, system `http://www.sequenceontology.org/` and the term's IRI).

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
      - The relation's code, system and IRI.

**Composes:** :ref:`MappableConcept`

**Used in:** :ref:`ClinvarDefiningAlleleConstraint`
