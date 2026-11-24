# Key Concepts

ClinVar-GKM data uses a handful of ideas, each building on the one before: a **variant**, a **proposition** about it, **statements** that classify that proposition, the **aggregate** statements ClinVar builds from them, and the **bundle** that holds them all. This page explains each in a paragraph or two and links to its detailed page. The [Glossary](../reference/glossary.md) defines every term.

The examples follow ClinVar's **variation 10** (the HFE p.His63Asp variant), the same one the [Quick Start](quick-start.md) queries.

---

## Variants: Cat-VRS variations and VRS alleles

A ClinVar **variation** is what ClinVar's website shows at `/clinvar/variation/10/`. In ClinVar-GKM it is a `variation` record with the id `clinvar:10`, of type `CategoricalVariant`, from the GA4GH **Cat-VRS** (Categorical Variation Representation) standard. A categorical variant is a ClinVar-level concept: it names a variant the way ClinVar does, with its HGVS names, genes and cross-references.

Most variations are defined by one precise genomic change, a **VRS allele** (GA4GH Variation Representation Specification). A VRS allele has a computed id, such as `ga4gh:VA.ELQCnIBGqaTl0AEE0Az18XZ2cgIHAQIY` for variation 10: the same change gets the same id in any system that computes it, which is what makes VRS ids useful for matching data across sources. The allele points to its **location**, and the location to its **sequence reference** (a chromosome or transcript).

```text
variation clinvar:10  →  allele ga4gh:VA.ELQ…  →  location ga4gh:SL.…  →  sequenceReference SQ.…
```

Copy-number variants are defined by a location rather than an allele, and some complex variants have no VRS definition at all. See [Variations](../output-reference/cat-vrs.md).

## Propositions: what is being claimed

A **proposition** is the claim a classification is about, separate from the verdict. For a germline pathogenicity classification, the proposition reads "variant `clinvar:10` is causal for *Hereditary hemochromatosis*": a `subject` (the variant), a `predicate` (`isCausalFor`) and an `object` (a condition, or a set of conditions). Its `type` says what kind of claim it is, for example `VariantPathogenicityProposition`, `VariantOncogenicityProposition` or `ClinvarRiskFactorProposition`.

Propositions are stored in four groups by meaning: pathogenicity, oncogenicity, somatic clinical impact, and ClinVar's other classification types. [Proposition Types](../profiles/propositions.md) maps every ClinVar classification type to its proposition.

**Conditions** are ClinVar's traits (diseases and phenotypes), with the id `clinvar.trait:<id>`. A proposition about several conditions points to a **condition set**.

## Statements: SCV, the submitted classification

A **statement** is a classification of a proposition. It carries:

- the **classification** itself, such as *Pathogenic* or *Likely benign*
- the **proposition** it classifies
- a **direction** (supports, disputes, or neutral toward the proposition) and a **strength**
- ClinVar's **review status**, and other details, as **extensions**

Every classification a lab or expert panel submits to ClinVar is an **SCV** (a ClinVar submission accession, such as `SCV000219176`). In ClinVar-GKM each SCV is one `scv` statement, with the id `clinvar.submission:SCV000219176.11` (accession and version). It points to its submitter, its proposition, and the publications and methods it cites. See [SCV Statements](../output-reference/scv-statements.md).

## Aggregates: VCV and RCV statements

ClinVar combines the SCVs about a variant into an overall call, the one at the top of the variant's page. That is a **VCV** (Variation in ClinVar) classification. ClinVar also combines them per variant and condition: an **RCV** (Reference ClinVar) classification.

In ClinVar-GKM these are `vcv` and `rcv` statements, built in layers that follow ClinVar's rules:

- The **overall call** for one kind of classification, such as `VCV000000010.143-G-PATH` (germline pathogenicity).
- Below it, one statement per **submission level**, such as `…-G-PATH-CP` (criteria provided) and `…-G-PATH-NOCP` (no assertion criteria). The overall call comes from the highest level present.
- Each level statement cites its **SCVs**, through an **evidence line** that says whether they count toward the call (*Contributing*) or not (*Non-contributing*).

Somatic clinical-impact statements add a layer for each tier. The diagram shows how a statement id encodes its lane, classification type and level:

<iframe src="../assets/diagrams/parquet-vcv-levels.html" style="width:100%; height:760px; border:1px solid rgba(128,128,128,.25); border-radius:6px;" title="Reading a variant's statements" loading="lazy"></iframe>

See [VCV Statements](../output-reference/vcv-statements.md), [RCV Statements](../output-reference/rcv-statements.md), and [Review Status](../profiles/review-status.md) for how the levels rank.

## Bundles, sections and pointers

A **bundle** is one JSON file that holds a whole release. It is a single object with one **section** per kind of record (`variation`, `allele`, `condition`, `submitter`, the four proposition sections, `evidenceLine`, `scv`, `vcv`, `rcv`, …). Each section maps a record's id to the record, so every record is stored once.

Records refer to each other with **pointers**: strings of the form `#/<section>/<id>`. `#/propositionPathogenicity/VCV000000010-G-PATH` is the record with that id in the `propositionPathogenicity` section. To follow one, split it at the slashes and look the id up in that section. The map shows every section and the pointers between them:

<iframe src="../assets/diagrams/bundle-section-map.html"
        style="width:100%; height:660px; border:1px solid rgba(128,128,128,.25); border-radius:6px;"
        title="ClinVar-GKM bundle section map"
        loading="lazy"></iframe>

The same records are also published as 20 **Parquet** tables, one per section, which you can query with SQL. See [Output Format](../output-reference/overview.md), [ID References](../output-reference/id-references.md) and [The 20 Tables](../parquet/tables.md).

## Releases and deltas

A new release follows each ClinVar weekly release. Each one is published as:

- a **full bundle**: every record, about 4.9 GB compressed. A weekly full is published for each release, and an official **monthly** full once a month, lined up with ClinVar's monthly release.
- a **delta**: only the records added or changed since the previous release, usually a few MB, with a manifest that also lists the records deleted. A monthly plus the deltas after it gives the state at any later week.
- one set of **Parquet** tables, rebuilt from the newest release.

Releases belong to a **version line**, a folder such as `v1/1.2/`. A change to the format starts a new line, and the old one is frozen and kept. See [How Releases Work](../data-access/release-model.md) and [Choose Your Data](choose-your-data.md).
