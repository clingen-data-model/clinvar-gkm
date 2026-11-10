.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

An expression of a ClinvarAllele: an SPDI, HGVS or gnomAD syntax and the expression text. No id, extensions or syntax version.

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
   *  - syntax
      -
      - string
      - 1..1
      - `spdi`, `gnomad`, or `hgvs.` and the HGVS type letter of the expression.
   *  - value
      -
      - string
      - 1..1
      - The expression of the variation in the specified syntax. The value should be a valid expression in the specified syntax.

**Composes:** :ref:`Expression`

**Used in:** :ref:`ClinvarAllele`
