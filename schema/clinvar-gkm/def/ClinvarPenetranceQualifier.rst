.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The penetrance qualifier on a ClinVar SCV proposition, derived from a low-penetrance or risk-allele classification: a MappableConcept named 'low' or 'risk', with the submitted classification in an ExtensionSubmittedClassification. No id, description, aliases, primary coding or mappings.

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
      - 'low' for a pathogenic or likely pathogenic, low penetrance classification; 'risk' for an established, likely or uncertain risk allele classification.
   *  - extensions
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`ExtensionSubmittedClassification`
      - 0..m
      - The submitted classification, in an ExtensionSubmittedClassification.
   *  - conceptType
      -
      - string
      - 0..1
      - Always 'penetrance'.

**Composes:** :ref:`MappableConcept`

**Used in:** :ref:`ClinvarGermlineCustomPropositionProperties`, :ref:`ClinvarVariantPathogenicityProposition`
