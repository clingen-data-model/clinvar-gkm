.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A record of the copyNumberCount section: a VRS CopyNumberCount with an integer copy count, whose location is a pointer to a record of the location section. No name, description, aliases, extensions or expressions.

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
      - MUST be "CopyNumberCount"
   *  - digest
      -
      - string
      - 0..1
      - A sha512t24u digest created using the VRS Computed Identifier algorithm.
   *  - location
      -
      - :ref:`iriReference`
      - 1..1
      - The location of the copy number count, a '#/location/<id>' pointer into this bundle.
   *  - copies
      -
      - integer
      - 1..1
      - The integral number of copies.

**Composes:** :ref:`CopyNumberCount`
