.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The classification of a ClinVar VCV or RCV aggregate statement: a MappableConcept with its concept type and the aggregate classification label as its name and, when the submissions conflict, an ExtensionConflictingExplanation. No id, description, aliases, coding or mappings.

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
   *  - extensions
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`ExtensionConflictingExplanation`
      - 0..m
      - The conflicting classifications, in an ExtensionConflictingExplanation.
   *  - conceptType
      -
      - string
      - 0..1
      - Must be 'Classification'.

**Composes:** :ref:`MappableConcept`

**Used in:** :ref:`ClinvarAggregateStatementProperties`
