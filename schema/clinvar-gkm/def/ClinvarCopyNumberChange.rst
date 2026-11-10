.. admonition:: Draft
    :class: warning

    May change significantly in future releases. See |maturity-model|.

**Computational Definition**

A record of the copyNumberChange section: a VRS CopyNumberChange whose location is a pointer to a record of the location section. No name, description, aliases, extensions or expressions.

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
      - 0..1
      - The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another.
   *  - type
      -
      - string
      - 1..1
      - MUST be "CopyNumberChange"
   *  - digest
      -
      - string
      - 0..1
      - A sha512t24u digest created using the VRS Computed Identifier algorithm.
   *  - location
      -
      - :ref:`iriReference`
      - 1..1
      - The location of the copy number change, a '#/location/<id>' pointer into this bundle.
   *  - copyChange
      -
      - string
      - 1..1
      - MUST use one of the defined enumerations that are based on the corresponding EFO ontological terms for copy number variation. See Implementation Guidance for more details.

**Composes:** :ref:`CopyNumberChange`
