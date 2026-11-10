.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A Sequence Ontology molecular consequence of a HgvsListItem: the SO code, its label as the name, the SO system and one identifiers.org IRI.

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
      - 1..1
      - The SO term label.
   *  - system
      -
      - string
      - 1..1
      - Must be 'http://www.sequenceontology.org/'.
   *  - code
      -
      - string
      - 1..1
      - The SO identifier.
   *  - iris
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`iriReference`
      - 0..m
      - The identifiers.org IRI of the SO term.

**Composes:** :ref:`ClinvarCoding`

**Used in:** :ref:`HgvsListItem`
