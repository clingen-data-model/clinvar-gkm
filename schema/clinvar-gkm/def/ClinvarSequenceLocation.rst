.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A record of the location section: a VRS SequenceLocation whose sequence reference is a pointer to a record of the sequenceReference section. No name, description, aliases, extensions or sequence.

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
      - MUST be "SequenceLocation"
   *  - digest
      -
      - string
      - 0..1
      - A sha512t24u digest created using the VRS Computed Identifier algorithm.
   *  - sequenceReference
      -
      - :ref:`iriReference`
      - 0..1
      - The reference sequence for the location, a '#/sequenceReference/<id>' pointer into this bundle.
   *  - start
      -
      - integer | :ref:`Range`
      - 0..1
      - The start coordinate or range of the SequenceLocation. The minimum value of this coordinate or range is 0. For locations on linear sequences, this MUST represent a coordinate or range less than or equal to the value of `end`. For circular sequences, `start` is greater than `end` when the location spans the sequence 0 coordinate.
   *  - end
      -
      - integer | :ref:`Range`
      - 0..1
      - The end coordinate or range of the SequenceLocation. The minimum value of this coordinate or range is 0. For locations on linear sequences, this MUST represent a coordinate or range greater than or equal to the value of `start`. For circular sequences, `end` is less than `start` when the location spans the sequence 0 coordinate.

**Composes:** :ref:`SequenceLocation`
