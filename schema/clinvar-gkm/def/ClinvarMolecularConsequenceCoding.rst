.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A Sequence Ontology molecular consequence of a HgvsListItem: ClinVar's SO code, the SO system, one identifiers.org IRI and, when the pipeline knows the term, its label as the name.

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
   *  - name
      -
      - string
      - 0..1
      - The SO term label, from the pipeline's SO lookup. Absent for a code the lookup does not list.
   *  - system
      -
      - string
      - 1..1
      - Must be 'http://www.sequenceontology.org/'.
   *  - code
      -
      - string
      - 1..1
      - The SO identifier ClinVar gives, passed through as is (e.g. `SO:0001583`).
   *  - iris
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`iriReference`
      - 0..m
      - The identifiers.org IRI of the SO term.

**Composes:** :ref:`ClinvarCoding`

**Used in:** :ref:`HgvsListItem`
