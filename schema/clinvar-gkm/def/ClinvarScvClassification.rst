.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The classification of a ClinVar SCV statement: a MappableConcept with its concept type, name, a ClinvarTermCoding, and ClinVar's description of it in an extension. No id, description, aliases or mappings.

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
      - :ref:`ExtensionClassificationDescription`
      - 0..m
      - The classification's description, in an ExtensionClassificationDescription.
   *  - conceptType
      -
      - string
      - 0..1
      - Must be 'Classification'.
   *  - primaryCoding
      -
      - :ref:`ClinvarTermCoding`
      - 0..1
      - The classification's code and its system (the guideline that defines it).

**Composes:** :ref:`MappableConcept`

**Used in:** :ref:`ClinvarScvStatementProperties`
