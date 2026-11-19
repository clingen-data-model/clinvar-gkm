.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A ClinVar canonical allele — the most common variant type. ClinVar identifies each variation by mapping submitted attributes to a GRCh38 genomic allele, which becomes the defining allele constraint. Carries ClinVar-specific extensions (HGVS list, gene list, cytogenetic location, variation type, etc.) alongside the Cat-VRS CanonicalAllele structure.

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
   *  - id
      -
      - string
      - 1..1
      - The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another.
   *  - type
      -
      - string
      - 1..1
      - MUST be "CategoricalVariant"
   *  - name
      -
      - string
      - 1..1
      - A primary name for the entity.
   *  - extensions
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`Extension` & :ref:`ExtensionClinvarHgvsList` | :ref:`ExtensionClinvarGeneList` | :ref:`ExtensionCategoricalVariationType` | :ref:`ExtensionDefiningVrsVariationType` | :ref:`ExtensionClinvarVariationType` | :ref:`ExtensionClinvarSubclassType` | :ref:`ExtensionClinvarCytogeneticLocation` | :ref:`ExtensionVrsPreProcessingIssue` | :ref:`ExtensionsVrsProcessingException`
      - 0..m
      - A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.
   *  - members
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`iriReference`
      - 0..m
      - The defining allele, a '#/allele/<id>' pointer into this bundle.
   *  - constraints
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`DefiningAlleleConstraint`
      - 1..1
      - The defining allele constraint.
   *  - mappings
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`ConceptMapping` & :ref:`ClinvarVariationMapping`
      - 0..m
      - A list of mappings to concepts in terminologies or code systems. Each mapping should include a coding and a relation.

**Composes:** :ref:`CanonicalAllele`, :ref:`ClinvarCategoricalVariantProperties`

**Used in:** :ref:`ClinvarCategoricalVariant`
