.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The copy count constraint of a ClinvarCategoricalCnvCount: a CopyCountConstraint with an integer copy count.

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
      - MUST be "CopyCountConstraint"
   *  - copies
      -
      - integer
      - 1..1
      - The integral number of copies.

**Composes:** :ref:`CopyCountConstraint`

**Used in:** :ref:`ClinvarCategoricalCnvCount`
