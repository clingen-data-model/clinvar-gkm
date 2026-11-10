.. admonition:: Trial Use
    :class: note

    May change in future releases. See |maturity-model|.

**Computational Definition**

A record of the sequenceReference section: a VRS SequenceReference for an NCBI RefSeq sequence, with its accession as the name, its molecule type and residue alphabet, and its assembly in an extension when the sequence belongs to one. No id, description, aliases, sequence or circular flag.

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
      - MUST be "SequenceReference"
   *  - name
      -
      - string
      - 0..1
      - A primary name for the entity.
   *  - extensions
      -
                        .. raw:: html

                            <span style="background-color: #B2DFEE; color: black; padding: 2px 6px; border: 1px solid black; border-radius: 3px; font-weight: bold; display: inline-block; margin-bottom: 5px;" title="Unordered">&#8942;</span>
      - :ref:`ExtensionAssembly`
      - 0..m
      - The assembly of the sequence, when it belongs to one.
   *  - refgetAccession
      -
      - string
      - 1..1
      - A `GA4GH RefGet <http://samtools.github.io/hts-specs/refget.html>`_ identifier for the referenced sequence, using the sha512t24u digest.
   *  - residueAlphabet
      -
      - string
      - 0..1
      - The interpretation of the character codes referred to by the refget accession, where "aa" specifies an amino acid character set, and "na" specifies a nucleic acid character set.
   *  - moleculeType
      -
      - string
      - 0..1
      - Molecule types as `defined by RefSeq <https://www.ncbi.nlm.nih.gov/books/NBK21091/>`_ (see Table 1). MUST be one of "genomic", "RNA", "mRNA", or "protein".

**Composes:** :ref:`SequenceReference`
