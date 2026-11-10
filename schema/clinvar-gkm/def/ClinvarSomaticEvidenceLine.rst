.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The evidence line of a ClinVar somatic clinical impact (SCI) SCV statement. It links the statement's VariantClinicalSignificanceProposition to the specific assertion: its target proposition (a VariantTherapeuticResponseProposition, VariantDiagnosticProposition or VariantPrognosticProposition, in the propositionSomaticClinicalImpact section), always supported, with an evidence outcome reflecting the AMP/ASCO/CAP tier and the submitter's original condition(s) in an extension. No name, description, aliases, method, contributions, citations, evidence items, strength or score.

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
      - The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another.
   *  - type
      -
      - string
      - 1..1
      - MUST be "EvidenceLine".
   *  - extensions
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`ExtensionEvidenceLineSubmittedCondition` | :ref:`ExtensionEvidenceLineSubmittedConditionSet`
      - 0..m
      - The submitter's original condition, in an ExtensionEvidenceLineSubmittedCondition, or conditions, in an ExtensionEvidenceLineSubmittedConditionSet.
   *  - targetProposition
      -
      - :ref:`iriReference`
      - 1..1
      - The specific assertion, a '#/propositionSomaticClinicalImpact/<id>' pointer to a VariantTherapeuticResponseProposition, VariantDiagnosticProposition or VariantPrognosticProposition in this bundle.
   *  - directionOfEvidenceProvided
      -
      - string
      - 1..1
      - Always 'supports'.
   *  - evidenceOutcome
      -
      - :ref:`ClinvarTerm`
      - 1..1
      - The evidence level for the AMP/ASCO/CAP tier, as a ClinvarTerm of concept type 'Outcome': 'Level A/B' for Tier I, 'Level C/D' for Tier II; for any other tier, the SCV's classification code.

**Composes:** :ref:`EvidenceLine`
