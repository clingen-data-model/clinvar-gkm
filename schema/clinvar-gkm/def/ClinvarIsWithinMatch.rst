.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The match characteristic of a ClinVar defining location constraint: a MappableConcept with only its type and primary coding (code `is_within`, system `ga4gh-gks-term:location-match`, no IRIs).

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
   *  - primaryCoding
      -
      - object
      - 0..1
      - The match characteristic's code and system.

**Composes:** :ref:`MappableConcept`

**Used in:** :ref:`ClinvarDefiningLocationConstraint`
