.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A record of the gene section: a MappableConcept for an NCBI Gene, with its primary coding and its mappings to other gene codes. No description, aliases or extensions.

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
      - MUST be "MappableConcept".
   *  - name
      -
      - string
      - 0..1
      - A primary name for the concept.
   *  - conceptType
      -
      - string
      - 0..1
      - A term indicating the type of concept being represented by the MappableConcept.
   *  - primaryCoding
      -
      - :ref:`ClinvarCoding`
      - 0..1
      - The gene's NCBI Gene coding.
   *  - mappings
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`ClinvarConceptMapping`
      - 0..m
      - Mappings of the gene to other gene codes.

**Composes:** :ref:`MappableConcept`
