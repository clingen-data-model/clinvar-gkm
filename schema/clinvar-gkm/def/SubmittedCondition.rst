.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The value of a submittedCondition extension: the submitted condition's mapping, with the condition (or, rarely, the condition set) it resolved to.

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
      - 0..1
      - The mapping details used to resolve the submitted condition to a ClinVar trait, including mapping type, reference field, and value.
   *  - condition
      -
      - string
      - 0..1
      - The CURIE of the resolved condition (e.g., "clinvar.trait:123"; the key of the corresponding #/condition/ bundle entry).
   *  - conditionSet
      -
      - string
      - 0..1
      - Usually absent for single-condition submissions; when a single-trait submission maps to a multi-trait RCV it holds the CURIE of that condition set (e.g., clinvar.traitset:123).

**Composes:** :ref:`SubmittedConditionMappingProperties`

**Used in:** :ref:`ExtensionEvidenceLineSubmittedCondition`, :ref:`ExtensionSubmittedCondition`
