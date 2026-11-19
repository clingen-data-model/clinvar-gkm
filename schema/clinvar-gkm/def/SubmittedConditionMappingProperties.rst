.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Abstract Class** — not instantiated directly; concrete subclasses inherit its attributes.

**Computational Definition**

The properties of a submitted condition's mapping, shared by SubmittedConditionMapping and SubmittedCondition.

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
      - The submitted trait category assignment identifier (cat_id).
   *  - name
      -
      - string
      - 0..1
      - The condition name as submitted by the submitter.
   *  - type
      -
      - string
      - 0..1
      - The condition type as submitted (e.g., "Disease", "Finding").
   *  - medgen_id
      -
      - string
      - 0..1
      - The MedGen ID submitted by the submitter, if provided.
   *  - xrefs
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`ClinvarTermCoding`
      - 0..m
      - Cross-references submitted by the submitter for this condition.
   *  - original_medgen_match
      -
      - object
      - 0..1
      - The original MedGen match when the submitted MedGen ID was remapped to a different canonical MedGen concept. Contains id and name of the original match. Null when no remapping occurred.
   *  - direct_match
      -
      - string
      - 0..1
      - The CURIE of the directly matched condition (e.g., "clinvar.trait:123"; the key of the corresponding #/condition/ bundle entry). Present only when the direct match differs from the normalized match.
   *  - normalized_match
      -
      - string
      - 0..1
      - The CURIE of the final normalized condition (e.g., "clinvar.trait:456"; the key of the corresponding #/condition/ bundle entry).
   *  - normalized_resolution
      -
      - string
      - 0..1
      - How the condition normalization was resolved: by the trait mapping of one of the submitted references ("tm reftype xref medgen", "tm reftype preferred name", ...), or, when none matched, by "random trait assignment".
   *  - mapping
      -
      - object
      - 1..1
      - The mapping details used to resolve the submitted condition to a ClinVar trait, including mapping type, reference field, and value.

**Used in:** :ref:`SubmittedCondition`, :ref:`SubmittedConditionMapping`
