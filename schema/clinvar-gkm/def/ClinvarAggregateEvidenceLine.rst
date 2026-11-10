.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

An evidence line of a VCV or RCV aggregate statement. A 'Contributing' line (direction 'supports') lists the statements the aggregate statement is built from; a 'Non-contributing' line (direction 'neutral') lists those of a lower review-status priority that did not contribute. Its items are pointers to SCV statements (at the classification layer) or to VCV or RCV statements (at the priority and aggregate layers). No name, description, aliases, extensions, method, contributions, citations, target proposition, score or evidence outcome.

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
      - MUST be "EvidenceLine".
   *  - hasEvidenceItems
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`iriReference`
      - 0..m
      - The statements the line groups, each a '#/scv/<id>', '#/vcv/<id>' or '#/rcv/<id>' pointer into this bundle.
   *  - directionOfEvidenceProvided
      -
      - string
      - 1..1
      - 'supports' for a Contributing line, 'neutral' for a Non-contributing line.
   *  - strengthOfEvidenceProvided
      -
      - :ref:`ClinvarTerm`
      - 1..1
      - 'Contributing' or 'Non-contributing', as a ClinvarTerm of concept type 'Strength'.

**Composes:** :ref:`EvidenceLine`
