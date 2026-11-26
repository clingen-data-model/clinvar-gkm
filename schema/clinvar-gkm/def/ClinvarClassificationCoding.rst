.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The coding of a ClinVar SCV classification: a ClinvarCoding with its code, its system and, when the guideline defines one, the term's canonical name (e.g. 'Tier I' for 'tier i'). No IRIs.

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
      - The human-readable name for the coded concept, as defined by the code system.
   *  - system
      -
      - string
      - 1..1
      - The terminology/code system that defined the code. May be reported as a free-text name (e.g. 'Sequence Ontology'), but it is preferable to provide a uri/url for the system.
   *  - code
      -
      - :ref:`code`
      - 1..1
      - A symbol uniquely identifying the concept, as in a syntax defined by the code system. e.g. 'civic.did:30', 'MONDO:005061', and 'C3512' are codes defined by different systems for representing the concept of 'lung adenocarcinoma'.  If a dereferencable identifier is available for the code, it should be provided in the `iris` field.

**Composes:** :ref:`ClinvarCoding`

**Used in:** :ref:`ClinvarScvClassification`
