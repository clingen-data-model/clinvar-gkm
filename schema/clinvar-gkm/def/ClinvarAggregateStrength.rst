.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The strength of a ClinVar VCV or RCV aggregate statement: a ClinvarTerm (no coding) whose concept type is 'Strength'.

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
   *  - name
      -
      - string
      - 0..1
      - A primary name for the concept.
   *  - conceptType
      -
      - string
      - 0..1
      - Must be 'Strength'.

**Composes:** :ref:`ClinvarTerm`

**Used in:** :ref:`ClinvarAggregateStatementProperties`
