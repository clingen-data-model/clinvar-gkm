.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The quality of a ClinVar statement's assessment, named from its submission level: a ClinvarTerm whose concept type is 'Quality'.

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
      - Must be 'Quality'.

**Composes:** :ref:`ClinvarTerm`

**Used in:** :ref:`ClinvarAggregateStatementProperties`, :ref:`ClinvarScvStatementProperties`
