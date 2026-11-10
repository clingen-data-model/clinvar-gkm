.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A ConceptMapping as ClinVar-GKM writes it: a ClinvarMappingCoding and its relation. No id or extensions.

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
   *  - coding
      -
      - :ref:`ClinvarMappingCoding`
      - 1..1
      - The coding the concept maps to.
   *  - relation
      -
      - string
      - 1..1
      - A mapping relation between concepts as defined by the Simple Knowledge Organization System (SKOS).

**Composes:** :ref:`ConceptMapping`

**Used in:** :ref:`ClinvarCondition`, :ref:`ClinvarGene`, :ref:`ClinvarGeneContextQualifier`, :ref:`ClinvarVariationMapping`
