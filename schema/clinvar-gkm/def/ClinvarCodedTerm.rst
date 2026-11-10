.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A term of a ClinVar vocabulary (a strength, say) as a MappableConcept: its concept type, its name and, when the term has one, a ClinvarTermCoding. No id, description, aliases, mappings or extensions.

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
      - A term indicating the type of concept being represented by the MappableConcept.
   *  - primaryCoding
      -
      - :ref:`ClinvarTermCoding`
      - 0..1
      - The term's code and its system.

**Composes:** :ref:`MappableConcept`

**Used in:** :ref:`ClinvarStrength`, :ref:`ClinvarTerm`
