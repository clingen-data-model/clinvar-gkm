.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The constraint of a ClinvarCanonicalAllele: a DefiningAlleleConstraint whose allele is a pointer to a record of the allele section, related by `liftover_to` and `transcribed_to`.

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
      - MUST be "DefiningAlleleConstraint"
   *  - allele
      -
      - :ref:`iriReference`
      - 1..1
      - The defining allele, a '#/allele/<id>' pointer into this bundle.
   *  - relations
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`ClinvarLiftoverToRelation` | :ref:`ClinvarTranscribedToRelation`
      - 0..m
      - The `liftover_to` and `transcribed_to` relations.

**Composes:** :ref:`DefiningAlleleConstraint`

**Used in:** :ref:`ClinvarCanonicalAllele`
