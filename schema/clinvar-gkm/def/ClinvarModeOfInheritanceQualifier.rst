.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The mode of inheritance qualifier on a ClinVar SCV proposition: a MappableConcept named by the submitted mode of inheritance, with its HPO coding when the name matches an HPO term, and the submitted value in an ExtensionSubmittedModeOfInheritance. No id, description, aliases or mappings.

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
      - :ref:`ExtensionSubmittedModeOfInheritance`
      - 0..m
      - The submitted mode of inheritance, in an ExtensionSubmittedModeOfInheritance.
   *  - conceptType
      -
      - string
      - 0..1
      - Always 'modeOfInheritance'.
   *  - primaryCoding
      -
      - :ref:`ClinvarCoding`
      - 0..1
      - The HPO term whose label matches the submitted mode of inheritance (case-insensitively). Absent when no HPO term matches.

**Composes:** :ref:`MappableConcept`

**Used in:** :ref:`ClinvarGermlineCustomPropositionProperties`, :ref:`ClinvarVariantPathogenicityProposition`
