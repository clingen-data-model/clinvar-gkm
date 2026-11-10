.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A term of a ClinVar vocabulary with no coding (a quality, say): a ClinvarCodedTerm with only its concept type and name.

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
      - 1..1
      - A term indicating the type of concept being represented by the MappableConcept.

**Composes:** :ref:`ClinvarCodedTerm`

**Used in:** :ref:`ClinvarAggregateEvidenceLine`, :ref:`ClinvarAggregateStrength`, :ref:`ClinvarQuality`, :ref:`ClinvarSomaticEvidenceLine`
