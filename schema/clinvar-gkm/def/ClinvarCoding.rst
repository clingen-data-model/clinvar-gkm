.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A Coding as ClinVar-GKM writes it: a code and its system, with an optional name and IRIs. No id, extensions or system version.

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
   *  - iris
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`iriReference`
      - 0..m
      - A list of IRIs that are associated with the coding. This can be used to provide additional context or to link to additional information about the concept.

**Composes:** :ref:`Coding`

**Used in:** :ref:`ClinvarCondition`, :ref:`ClinvarGene`, :ref:`ClinvarGeneContextQualifier`, :ref:`ClinvarMappingCoding`, :ref:`ClinvarModeOfInheritanceQualifier`, :ref:`ClinvarMolecularConsequenceCoding`, :ref:`ClinvarTermCoding`
