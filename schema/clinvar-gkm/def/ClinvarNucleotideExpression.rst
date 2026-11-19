.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

The nucleotide HGVS expression of a HgvsListItem: an HGVS syntax and the expression text, with extensions only when ClinVar supplied an expression with no HGVS type letter. No id or syntax version.

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
   *  - extensions
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`ExtensionInvalidClinvarExpression` | :ref:`ExtensionExpressionMerged` | :ref:`ExtensionOriginalClinvarExpression` | :ref:`ExtensionExpressionRepaired`
      - 0..m
      - ClinVar's submitted text when it had no HGVS type letter: either `invalidClinvarExpression` (one per such text) and `expressionMerged`, when this is ClinVar's valid expression for the same accession, or `originalClinvarExpression` and `expressionRepaired`, when this is the repaired expression.
   *  - syntax
      -
      - string
      - 1..1
      - `hgvs.` and the HGVS type letter of the expression.
   *  - value
      -
      - string
      - 1..1
      - The expression of the variation in the specified syntax. The value should be a valid expression in the specified syntax.

**Composes:** :ref:`Expression`

**Used in:** :ref:`HgvsListItem`
