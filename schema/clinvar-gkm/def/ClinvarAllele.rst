.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A record of the allele section: a VRS Allele with its name and expressions, whose location is a pointer to a record of the location section. No description, aliases or extensions.

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
      - MUST be "Allele"
   *  - name
      -
      - string
      - 0..1
      - A primary name for the entity.
   *  - digest
      -
      - string
      - 0..1
      - A sha512t24u digest created using the VRS Computed Identifier algorithm.
   *  - expressions
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`ClinvarAlleleExpression`
      - 0..m
      - The allele's SPDI, HGVS and gnomAD expressions.
   *  - location
      -
      - :ref:`iriReference`
      - 1..1
      - The location of the allele, a '#/location/<id>' pointer into this bundle.
   *  - state
      -
      - :ref:`SequenceExpression`
      - 1..1
      - The allele's state: a LiteralSequenceExpression or a ReferenceLengthExpression (whose length is an integer). No id, name, description, aliases or extensions.

**Composes:** :ref:`Allele`
