.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A Document as ClinVar-GKM writes it for a ClinVar citation: its PubMed id, DOI and URLs, the name and document type when ClinVar gives them, and extensions that keep ClinVar's citation text and record repairs of its ids. No id, title, description or aliases.

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
      - Must be "Document"
   *  - name
      -
      - string
      - 0..1
      - A primary name for the entity.
   *  - extensions
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`ExtensionClinvarCitationText` | :ref:`ExtensionOriginalClinvarCitation` | :ref:`ExtensionOriginalClinvarCitationSource` | :ref:`ExtensionCitationRepaired` | :ref:`ExtensionClinvarDoi` | :ref:`ExtensionInvalidClinvarCitation` | :ref:`ExtensionUnmappedClinvarCitation`
      - 0..m
      - ClinVar's citation text, the record of any repair of the citation's id, and ids that are invalid or from an unmapped source.
   *  - documentType
      -
                        .. raw:: html

                            <span style="background-color: #D3D3D3; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Draft Maturity Level">D</span>
      - string
      - 0..1
      - A specific type of document that a Document instance represents (e.g.  'publication', 'patent', 'pathology report')
   *  - urls
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - string
      - 0..m
      - One or more URLs from which the content of the Document can be retrieved.
   *  - doi
      -
      - string
      - 0..1
      - A `Digital Object Identifier <https://www.doi.org/the-identifier/what-is-a-doi/>`_ for the document.
   *  - pmid
      -
      - string
      - 0..1
      - A `PubMed unique identifier <https://en.wikipedia.org/wiki/PubMed#PubMed_identifier>`_ for the document.

**Composes:** :ref:`Document`

**Used in:** :ref:`ClinvarMethod`, :ref:`ClinvarScvStatementProperties`, :ref:`ExtensionAdditionalClinvarMethodCitations`
