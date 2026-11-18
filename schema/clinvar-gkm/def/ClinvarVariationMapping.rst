.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A mapping of a ClinVar variation: a ClinvarConceptMapping whose relation is `exactMatch` (the ClinVar variation), `closeMatch` (a ClinGen allele) or `relatedMatch` (every other cross-reference).

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
      - `exactMatch` for the ClinVar variation, `closeMatch` for a ClinGen allele, `relatedMatch` for every other cross-reference.

**Composes:** :ref:`ClinvarConceptMapping`

**Used in:** :ref:`ClinvarCategoricalVariantProperties`
