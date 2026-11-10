.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The gene context qualifier on a ClinVar SCV proposition: a gene MappableConcept with the codings of a ClinvarGene, and extensions saying where its gene came from (ExtensionGeneContextSource) and which gene symbols the submitter gave (ExtensionSubmittedGeneSymbols). No id, description or aliases.

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
      - 1..1
      - A primary name for the concept.
   *  - extensions
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`ExtensionGeneContextSource` | :ref:`ExtensionSubmittedGeneSymbols`
      - 0..m
      - The qualifier's extensions, each an ExtensionGeneContextSource or an ExtensionSubmittedGeneSymbols.
   *  - conceptType
      -
      - string
      - 1..1
      - Always 'gene'.
   *  - primaryCoding
      -
      - :ref:`ClinvarCoding`
      - 0..1
      - The gene's NCBI Gene coding. Absent on a placeholder qualifier (geneContextSource 'submittedNotNormalized').
   *  - mappings
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`ClinvarConceptMapping`
      - 0..m
      - Mappings of the gene to other gene codes (its HGNC coding). Absent on a placeholder qualifier.

**Composes:** :ref:`MappableConcept`

**Used in:** :ref:`ClinvarGermlineCustomPropositionProperties`, :ref:`ClinvarVariantClinicalSignificanceProposition`, :ref:`ClinvarVariantDiagnosticProposition`, :ref:`ClinvarVariantOncogenicityProposition`, :ref:`ClinvarVariantPathogenicityProposition`, :ref:`ClinvarVariantPrognosticProposition`, :ref:`ClinvarVariantTherapeuticResponseProposition`
