.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The coding of a ClinVar term: a ClinvarCoding with only its code and system. No name or IRIs.

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

**Used in:** :ref:`ClinvarCodedTerm`, :ref:`ClinvarScvClassification`, :ref:`SubmittedConditionMappingProperties`
