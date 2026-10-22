# Data Use and Citation

ClinVar-GKM re-represents ClinVar data. ClinVar is produced by the National Center for Biotechnology Information
(NCBI), part of the U.S. National Library of Medicine (NLM). ClinVar-GKM is produced by ClinGen. ClinGen's
[CC0 dedication](#license) covers what ClinGen adds. The ClinVar content inside the files remains subject to
NCBI's and ClinVar's own policies, which apply to everyone who uses or redistributes these files.

!!! info "In short"
    - **Not for direct clinical use.** The ClinVar disclaimer applies to this data unchanged: the information
      "is not intended for direct diagnostic use or medical decision-making without review by a genetics
      professional." See [Clinical use](#clinical-use).
    - **Attribute ClinVar.** ClinVar asks that anyone who distributes or copies its data provide attribution
      to ClinVar as a data source. Cite ClinVar, and cite ClinVar-GKM if you used these files. See
      [How to cite](#how-to-cite).
    - **CC0 covers ClinGen's contribution only.** It adds no restriction, and it cannot grant rights that
      NCBI or ClinVar's submitters hold. See [License](#license).
    - **Pass this on.** If you redistribute these files or data derived from them, carry the attribution and
      the disclaimer with them. See [Redistributing the data](#redistributing-the-data).

---

## Data source

The ClinVar content comes from the public XML releases of [ClinVar](https://www.ncbi.nlm.nih.gov/clinvar/), at
NCBI, NLM, National Institutes of Health (NIH). The pipeline adds the GKM structure and the VRS identifiers it
computes. Weekly and delta file names carry the ClinVar release date, and each version line's `index.json` and
the Parquet `manifest.json` name the release each file was built from; see
[How Releases Work](data-access/release-model.md).

ClinVar is an archive of classifications made by its submitters. When submitters disagree, ClinVar's
[FAQ](https://www.ncbi.nlm.nih.gov/clinvar/docs/faq/#conflicts) says that "ClinVar does not arbitrate and resolve
these conflicts", and its disclaimer says that "NIH does not independently verify the
submitted information." ClinVar-GKM changes the representation, not the classifications. It keeps each
submission's submitter and dates: every SCV statement's `contributions` reference a record in the `submitter`
section. ClinVar remains the authoritative source. Check a record on ClinVar before you rely on it, and see
[Known Issues](reference/known-issues.md) for what the transformation does not yet carry.

---

## Clinical use

ClinVar's [disclaimer and data use policy](https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/#disclaimer)
applies to ClinVar-GKM data as it does to ClinVar:

> The information on this website is not intended for direct diagnostic use or medical decision-making without
> review by a genetics professional. Individuals should not change their health behavior solely on the basis of
> information contained on this website.

NLM's [Medical Information and Advice Disclaimer](https://www.ncbi.nlm.nih.gov/home/about/policies/#medical)
urges users "to consult with a qualified physician for diagnosis and for answers to your personal questions."
The same advice applies to this data.

---

## How to cite

### ClinVar

ClinVar asks for attribution in its
[data use policy](https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/#disclaimer): "If you distribute or
copy data from ClinVar, we ask that you provide attribution to ClinVar as a data source in publications and
websites." It asks you to cite one of the
[ClinVar publications](https://www.ncbi.nlm.nih.gov/clinvar/intro/). The newest is:

> Landrum MJ, Chitipiralla S, Kaur K, et al. ClinVar: updates to support classifications of both germline and
> somatic variants. *Nucleic Acids Res.* 2025;53(D1):D1313–D1321.
> [doi:10.1093/nar/gkae1090](https://doi.org/10.1093/nar/gkae1090). PMID: 39578691.

The data use policy gives PMID [29165669](https://pubmed.ncbi.nlm.nih.gov/29165669/) as an example (Landrum MJ
et al., *Nucleic Acids Res.* 2018;46(D1):D1062–D1067).

To refer to a specific ClinVar record, follow ClinVar's
[FAQ](https://www.ncbi.nlm.nih.gov/clinvar/docs/faq/#citation): cite the SCV accession and version for a
submission, and the VCV or RCV accession and version for an aggregate record. ClinVar-GKM keeps these accessions
and versions in its statement ids and extensions.

### ClinVar-GKM

If you used these files, also cite ClinVar-GKM and name the release you used, for example the bundle file name
or the Parquet `manifest.json` `source_release`:

> Babb L, Ferriter K, O'Neill T. *ClinVar-GKM*. ClinGen. [doi:10.5281/zenodo.18343663](https://doi.org/10.5281/zenodo.18343663).

The repository's [CITATION.cff](https://github.com/clingen-data-model/clinvar-gkm/blob/main/CITATION.cff) has
the machine-readable citation, and GitHub's **Cite this repository** button formats it.

---

## License

ClinGen dedicates the ClinVar-GKM code and the published files, the transformed bundles and Parquet sets, to the
public domain under [CC0 1.0 Universal](https://github.com/clingen-data-model/clinvar-gkm/blob/main/LICENSE).
CC0 covers what ClinGen contributes: the transformation, the structure and the identifiers it computes. It adds
no restriction of its own.

CC0 does not change the terms that apply to the ClinVar content inside the files:

- NCBI's [Molecular Data Usage](https://www.ncbi.nlm.nih.gov/home/about/policies/#data) policy says that "NCBI
  itself places no restrictions on the use or distribution of the data". It also says that some submitters "may
  claim patent, copyright, or other intellectual property rights in all or a portion of the data", and that
  NCBI "cannot provide comment or unrestricted permission concerning the use, copying, or distribution" of it.
  CC0 waives only rights that ClinGen holds, so it grants nothing in rights that a submitter may claim.
- ClinVar's [submission policy](https://www.ncbi.nlm.nih.gov/clinvar/docs/submit/#consent) says that "Once the
  data are in ClinVar, they are available for unrestricted distribution."
- CC0 itself (section 4) offers the work as-is, with no warranty, and disclaims responsibility for clearing
  other people's rights in it.

You are responsible for following NCBI's and ClinVar's policies, including their attribution request, when you
use or redistribute this data.

---

## Redistributing the data

You may redistribute ClinVar-GKM files, or data derived from them, under CC0. When you do:

- **Keep the attribution.** Name ClinVar as the data source, as ClinVar asks, and name ClinVar-GKM and the
  release.
- **Keep the disclaimer visible.** Carry the [clinical use](#clinical-use) disclaimer, or link to it, wherever
  people see the data. NCBI asks the same of services built on its servers: its
  [Guidelines for Scripting Calls to NCBI Servers](https://www.ncbi.nlm.nih.gov/home/about/policies/#scripting)
  state that "NCBI's Disclaimer and Copyright notice must be evident to users of your service."
- **Keep the submitter attribution.** ClinVar's [introduction](https://www.ncbi.nlm.nih.gov/clinvar/intro/)
  says that "Each submitter is explicitly acknowledged". Do not strip the `submitter` records
  or SCV `contributions` from data you pass on as ClinVar's classifications.
- **Don't imply endorsement.** See [No endorsement](#no-endorsement).

---

## No endorsement

ClinVar-GKM is not an NCBI, NLM or NIH product and is not endorsed by them. NCBI's
[Website Disclaimer](https://www.ncbi.nlm.nih.gov/home/about/policies/#disclaimer) says that "NCBI does not
endorse or recommend any commercial products, processes, or services", and NLM's
[logo policy](https://www.nlm.nih.gov/web_policies.html#logo_policy) restricts use of its logo. ClinVar-GKM uses
no NCBI or NLM logo. Products built on this data should likewise name ClinVar as a source without suggesting
that NCBI, NLM, NIH or ClinGen endorses them.
