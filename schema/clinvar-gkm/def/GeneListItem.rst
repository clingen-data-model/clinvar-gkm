.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

One gene associated with a ClinVar variation: a reference to the gene's MappableConcept in the bundle's `gene` section, plus ClinVar's `relationship_type` and `source`.

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
   *  - gene
      -
      - :ref:`iriReference`
      - 1..1
      - Reference to the gene MappableConcept in the bundle's `gene` section (e.g. `#/gene/ncbigene:672`).
   *  - relationship_type
      -
      - string
      - 1..1
      - The relationship between the variation and the gene as reported by ClinVar (e.g.,  `within single gene`, `genes overlapped by variant`).
   *  - source
      -
      - string
      - 1..1
      - The source of the gene association: `submitted` (asserted by the submitter) or `calculated` (computed by ClinVar).

**Used in:** :ref:`ExtensionClinvarGeneList`
