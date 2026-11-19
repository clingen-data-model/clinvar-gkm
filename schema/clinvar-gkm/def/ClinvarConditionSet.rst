.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A record of the conditionSet section: a ConditionSet whose concepts are pointers to records of the condition or conditionSet section. No name, description, aliases or extensions.

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
      - MUST be "ConceptSet".
   *  - conceptSetType
      -
      - string
      - 0..1
      - A term indicating the type of concept being represented by the ConceptSet.
   *  - concepts
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`iriReference`
      - 2..m
      - The set's members, each a '#/condition/<id>' or '#/conditionSet/<id>' pointer into this bundle.
   *  - membershipOperator
      -
      - string
      - 1..1
      - The logical relationship between concepts in the set, in the context of some knowledge reported about them. The value 'AND' indicates that the concepts are dependent and occur together in this context - i.e. the reported assertion is not necessarily true for each concept on its own - only in combination with the other(s). The value 'OR' indicates that each concept applies independently in this context - i.e. the reported assertion is necessarily true for each concept on its own, independent of the presence of the other(s).

**Composes:** :ref:`ConditionSet`
