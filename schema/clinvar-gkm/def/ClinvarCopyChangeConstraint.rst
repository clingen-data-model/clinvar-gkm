.. admonition:: Draft
    :class: warning

    May change significantly in future releases. See |maturity-model|.

**Computational Definition**

The copy change constraint of a ClinvarCategoricalCnvChange: a CopyChangeConstraint whose copy change is 'loss' or 'gain'.

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
      - MUST be "CopyChangeConstraint"
   *  - copyChange
      -
      - string
      - 1..1
      - The copy change: 'loss' or 'gain', the only values the pipeline writes.

**Composes:** :ref:`CopyChangeConstraint`

**Used in:** :ref:`ClinvarCategoricalCnvChange`
