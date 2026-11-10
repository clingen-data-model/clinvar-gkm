.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The value of a submittedConditionSet extension: the submitted condition set with the mapping of each of its conditions.

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
   *  - conditionSet
      -
      - string
      - 0..1
      - The CURIE of the resolved condition set (e.g., "clinvar.traitset:123"; the key of the corresponding #/conditionSet/ bundle entry).
   *  - condition
      -
      - string
      - 0..1
      - Usually absent for multi-condition submissions; when present, the CURIE of a condition (e.g., "clinvar.trait:123"; the key of the corresponding #/condition/ bundle entry).
   *  - multiple_condition_explanation
      -
      - string
      - 0..1
      - ClinVar's explanation for how multiple conditions relate (maps to the ConditionSet membership operator: AND or OR).
   *  - concepts
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Ordered">&#8595;</span>
      - :ref:`SubmittedConditionMapping`
      - 0..m
      - Array of individual submitted condition mappings, one per condition in the set. Ordered by the condition's cat_id suffix.

**Used in:** :ref:`ExtensionEvidenceLineSubmittedConditionSet`, :ref:`ExtensionSubmittedConditionSet`
