.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A Method as ClinVar-GKM writes it for a submission's assertion method: its method type, its name and its first citation; further citations are in an extension. No id, description or aliases.

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
      - MUST be "Method".
   *  - name
      -
      - string
      - 0..1
      - A primary name for the entity.
   *  - extensions
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`ExtensionAdditionalClinvarMethodCitations`
      - 0..m
      - The method's further citations, in an ExtensionAdditionalClinvarMethodCitations.
   *  - methodType
      -
      - string
      - 0..1
      - A specific type of method that a Method instance represents (e.g. 'Variant Interpretation Guideline', or 'Experimental Protocol').
   *  - reportedIn
      -
      - :ref:`ClinvarDocument`
      - 0..1
      - The method's first citation.

**Composes:** :ref:`Method`

**Used in:** :ref:`ClinvarScvStatementProperties`
