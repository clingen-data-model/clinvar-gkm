.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The location constraint of a ClinVar copy number variant: a DefiningLocationConstraint whose location is a pointer to a record of the location section, matched `is_within` and related by `liftover_to`.

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
      - MUST be "DefiningLocationConstraint"
   *  - location
      -
      - :ref:`iriReference`
      - 1..1
      - The defining location, a '#/location/<id>' pointer into this bundle.
   *  - relations
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`ClinvarLiftoverToRelation`
      - 0..m
      - The `liftover_to` relation.
   *  - matchCharacteristic
      -
      - :ref:`ClinvarIsWithinMatch`
      - 1..1
      - The `is_within` match characteristic.

**Composes:** :ref:`DefiningLocationConstraint`

**Used in:** :ref:`ClinvarCategoricalCnvChange`, :ref:`ClinvarCategoricalCnvCount`
