.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The protein HGVS expression of a HgvsListItem: an HGVS syntax and the expression text. No id, extensions or syntax version.

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
      - `hgvs.` and the HGVS type letter of the expression (`hgvs.p`).
   *  - value
      -
      - string
      - 1..1
      - The expression of the variation in the specified syntax. The value should be a valid expression in the specified syntax.

**Composes:** :ref:`Expression`

**Used in:** :ref:`HgvsListItem`
