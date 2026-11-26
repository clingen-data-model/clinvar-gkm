.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A ClinVar SCV statement about a variant's somatic clinical impact, modelled on the VA-Spec AMP/ASCO/CAP 2017 VariantClinicalSignificanceStatement. Its classification is coded under the AMP/ASCO/CAP 2017 guidelines as 'tier i' to 'tier iv', with each tier's strength and direction. It differs from the community profile in two ways: specifiedBy is optional; and the canonical tier name ('Tier I') is on the classification's primaryCoding.name, while classification.name keeps ClinVar's label (e.g. 'Tier I - Strong'). See the Community Profiles page.

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
      - MUST be "Statement".
   *  - description
      -
      - string
      - 0..1
      - A free-text description of the Entity.
   *  - extensions
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`Extension` & :ref:`ExtensionClinvarScvId` | :ref:`ExtensionClinvarScvVersion` | :ref:`ExtensionClinvarScvReviewStatus` | :ref:`ExtensionSubmittedScvLocalKey` | :ref:`ExtensionSubmissionLevel` | :ref:`ExtensionSubmittedScvClassification` | :ref:`ExtensionSubmittedCondition` | :ref:`ExtensionSubmittedConditionSet`
      - 0..m
      - A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.
   *  - specifiedBy
      -
      - :ref:`Method` | :ref:`iriReference` & :ref:`ClinvarMethod`
      - 0..1
      - A specification that describes all or part of the process that led to creation of the Information Entity
   *  - contributions
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Ordered">&#8595;</span>
      - :ref:`Contribution` & :ref:`ClinvarContribution`
      - 0..m
      - Specific actions taken by an Agent toward the creation, modification, validation, or deprecation of an Information Entity.
   *  - reportedIn
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`Document` | :ref:`iriReference` & :ref:`ClinvarDocument`
      - 0..m
      - A document in which the the Information Entity is reported.
   *  - proposition
      -
      - :ref:`iriReference`
      - 1..1
      - The clinical significance proposition, a pointer into the bundle's propositionSomaticClinicalImpact section.
   *  - direction
      -
      - string
      - 0..1
      - A term indicating whether the Statement supports, disputes, or remains neutral w.r.t. the validity of the Proposition it evaluates.
   *  - strength
      -
      - object
      - 0..1
      - The strength of a tier i or tier ii classification, coded under AMP/ASCO/CAP 2017.
   *  - quality
      -
                        .. raw:: html

                            <span style="background-color: #D3D3D3; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Draft Maturity Level">D</span>
      - :ref:`MappableConcept` | :ref:`iriReference` & :ref:`ClinvarQuality`
      - 1..1
      - A term used to report the quality of the assessment of a Proposition taking into consideration the reliability of the method, the contributor's self-reporting of the rigor of the evaluation, and the overall robustness of the supporting or disputing evidence. This is useful when there is a consistent policy and authority that manages and a governing framework for evaluating the quality of evidence. Also known as trust rating, review status or ranking.
   *  - classification
      -
      - object
      - 1..1
      - The classification, coded under AMP/ASCO/CAP 2017 with the tier's canonical name.
   *  - hasEvidenceLines
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`iriReference`
      - 0..m
      - An evidence-based argument that supports or disputes the validity of the proposition that a Statement assesses or puts forth as true. The strength and direction of this argument (whether it supports or disputes the proposition, and how strongly) is based on an interpretation of one or more pieces of information as evidence (i.e. 'Evidence Items).

**Additional Constraints**

.. list-table::
   :class: clean-wrap
   :header-rows: 1
   :align: left
   :widths: auto

   *  - If property...
      - has value...
      - then property...
      - must...
   *  - *classification.primaryCoding.code*
      - **tier i**
      - *classification.primaryCoding.name*
      - have value **Tier I**
   *  - *classification.primaryCoding.code*
      - **tier i**
      - *strength.primaryCoding.code*
      - have value **strong**
   *  - *classification.primaryCoding.code*
      - **tier i**
      - *direction*
      - have value **supports**
   *  - *classification.primaryCoding.code*
      - **tier ii**
      - *classification.primaryCoding.name*
      - have value **Tier II**
   *  - *classification.primaryCoding.code*
      - **tier ii**
      - *strength.primaryCoding.code*
      - have value **potential**
   *  - *classification.primaryCoding.code*
      - **tier ii**
      - *direction*
      - have value **supports**
   *  - *classification.primaryCoding.code*
      - **tier iii**
      - *classification.primaryCoding.name*
      - have value **Tier III**
   *  - *classification.primaryCoding.code*
      - **tier iii**
      - *strength*
      - not be provided
   *  - *classification.primaryCoding.code*
      - **tier iii**
      - *direction*
      - have value **neutral**
   *  - *classification.primaryCoding.code*
      - **tier iv**
      - *classification.primaryCoding.name*
      - have value **Tier IV**
   *  - *classification.primaryCoding.code*
      - **tier iv**
      - *strength*
      - not be provided
   *  - *classification.primaryCoding.code*
      - **tier iv**
      - *direction*
      - have value **disputes**


**Composes:** :ref:`ClinvarScvStatement`
