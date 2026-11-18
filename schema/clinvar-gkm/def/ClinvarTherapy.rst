.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A record of the therapy section: a Therapy named by its submitted text. No id, description, aliases, extensions, codings or mappings.

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
   *  - type
      -
      - string
      - 1..1
      - MUST be "MappableConcept".
   *  - name
      -
      - string
      - 1..1
      - A primary name for the concept.
   *  - conceptType
      -
      - string | string
      - 1..1
      - A term indicating the type of concept being represented by the MappableConcept.

**Composes:** :ref:`Therapy`
