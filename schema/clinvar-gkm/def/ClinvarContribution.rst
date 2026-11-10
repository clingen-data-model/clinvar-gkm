.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A Contribution as ClinVar-GKM writes it: a submitter's activity on a ClinVar record, with its date. The contributor is a pointer to a record of the submitter section. No id, name, description, aliases or extensions.

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
      - MUST be "Contribution".
   *  - contributor
      -
      - :ref:`iriReference`
      - 0..1
      - The submitter, a '#/submitter/<id>' pointer into this bundle.
   *  - activityType
      -
      - string
      - 0..1
      - What the submitter did on the date: submitted (last updated), created, or evaluated the record.
   *  - date
      -
      - :ref:`datetime`
      - 0..1
      - When the contributing activity was completed.

**Composes:** :ref:`Contribution`

**Used in:** :ref:`ClinvarScvStatementProperties`
