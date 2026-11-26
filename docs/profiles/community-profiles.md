# Community Profiles

!!! abstract "What this page answers"
    How ClinVar-GKM's SCV statements compare with the VA-Spec community statement profiles for ACMG 2015, CCV 2022
    and AMP/ASCO/CAP 2017: what each ClinVar-GKM profile allows, where it differs from the community profile, and
    why. It also shows how many SCVs in a release conform to each community profile. Read it before you validate
    ClinVar-GKM SCVs against a community profile, or when you need to know why a record would fail one.

VA-Spec publishes **community profiles**: statement profiles that fix how a guideline's classifications are coded,
which strengths go with them, and what a statement must carry. They are intentionally strict. ClinVar's submissions
cannot all meet them as written: many have no assertion method, ClinVar accepts classification terms the 2015
guidelines do not define, and ClinVar names the AMP/ASCO/CAP tiers in its own way.

ClinVar-GKM therefore holds its SCVs to **its own profiles**, each modelled on a community profile. Each one restates
the community profile's rules and keeps them, except for the differences listed on this page. The community
profiles are unchanged. A difference is never hidden: it appears here, in the profile's description, and in the
[record counts](#record-counts) each release.

---

## Which SCVs each profile covers

The bundle schema picks the profile from the section the SCV's `proposition` points into. Every SCV also stays a
[ClinvarScvStatement](../output-reference/classes/ClinvarScvStatement.md).

| Proposition section | ClinVar-GKM profile | Modelled on (VA-Spec community profile) |
| --- | --- | --- |
| `propositionPathogenicity` | [ClinvarScvPathogenicityStatement](../output-reference/classes/ClinvarScvPathogenicityStatement.md) | ACMG 2015 `VariantPathogenicityStatement` |
| `propositionOncogenicity` | [ClinvarScvOncogenicityStatement](../output-reference/classes/ClinvarScvOncogenicityStatement.md) | CCV 2022 `VariantOncogenicityStatement` |
| `propositionSomaticClinicalImpact` | [ClinvarScvClinicalSignificanceStatement](../output-reference/classes/ClinvarScvClinicalSignificanceStatement.md) | AMP/ASCO/CAP 2017 `VariantClinicalSignificanceStatement` |
| `propositionClinvarCustom` | none (ClinvarScvStatement only) | none: ClinVar's other statement types have no community profile |

VCV and RCV aggregate statements are not covered: their classifications are ClinVar's aggregate labels, which no
community profile defines.

---

## Guideline systems

A coding's `system` names the guideline that defines the code. A strength is always coded in the same system as its
classification.

| Short name | `system` | Defines |
| --- | --- | --- |
| ACMG 2015 | `ACMG Guidelines, 2015` | pathogenicity classifications and their strengths |
| ClinGen 2024 | `ClinGen Low Penetrance and Risk Allele Recommendations, 2024` | low-penetrance and risk-allele classifications and their strengths |
| SVCv4 | `ACMG/AMP/CAP/ClinGen SVCv4.0` | the VUS sub-tiers (VUS-high, VUS-mid, VUS-low) and their strengths (high, mid, low) |
| CCV 2022 | `ClinGen/CGC/VICC Guidelines for Oncogenicity, 2022` | oncogenicity classifications and their strengths |
| AMP/ASCO/CAP 2017 | `AMP/ASCO/CAP Guidelines, 2017` | the somatic clinical impact tiers and their strengths |
| ClinVar | `ClinVar` | ClinVar's combined labels and its other statement types |

---

## ACMG 2015: variant pathogenicity

| Rule | VA-Spec community profile | ClinVar-GKM [profile](../output-reference/classes/ClinvarScvPathogenicityStatement.md) | Why |
| --- | --- | --- | --- |
| Proposition | a `VariantPathogenicityProposition` | a `#/propositionPathogenicity/` pointer to one | Same. Bundle records point to each other. |
| Classification codes and systems | ACMG 2015: `pathogenic`, `likely pathogenic`, `uncertain significance`, `likely benign`, `benign`. ClinGen 2024: `pathogenic, low penetrance`, `likely pathogenic, low penetrance`, `established risk allele`, `likely risk allele`, `uncertain risk allele` | the same, **plus** SVCv4: `vus-high`, `vus-mid`, `vus-low`; and ClinVar: `benign/likely benign`, `pathogenic/likely pathogenic`. The coding is required. | **Difference.** ClinVar accepts the SVCv4 VUS sub-tiers and the combined labels, and ClinVar-GKM keeps what was submitted rather than dropping it. |
| Strength | ACMG 2015: `definitive`, `likely` | in the classification's system: ACMG 2015 or ClinGen 2024: `definitive`, `likely`; SVCv4: `high`, `mid`, `low` | **Difference.** A strength belongs to the guideline that defines its classification, so low-penetrance and risk-allele strengths are coded under ClinGen 2024, and the VUS sub-tiers' strengths under SVCv4. |
| `specifiedBy` | required | optional | **Difference.** ClinVar does not require an assertion method, and many submissions have none. |
| Evidence lines | `VariantPathogenicityEvidenceLine`s | none | Same. ClinVar submissions carry no ACMG criteria. |

## CCV 2022: variant oncogenicity

| Rule | VA-Spec community profile | ClinVar-GKM [profile](../output-reference/classes/ClinvarScvOncogenicityStatement.md) | Why |
| --- | --- | --- | --- |
| Proposition | a `VariantOncogenicityProposition` | a `#/propositionOncogenicity/` pointer to one | Same. |
| Classification codes and systems | CCV 2022: `oncogenic`, `likely oncogenic`, `uncertain significance`, `likely benign`, `benign` | the same. The coding is required. | Same. `benign` and `likely benign` are CCV 2022 codes here, not ACMG 2015 ones. |
| Strength | CCV 2022: `definitive`, `likely` | the same | Same. |
| `specifiedBy` | required | optional | **Difference.** As for ACMG 2015. |
| Evidence lines | `VariantOncogenicityEvidenceLine`s | none | Same. |

## AMP/ASCO/CAP 2017: clinical significance

| Rule | VA-Spec community profile | ClinVar-GKM [profile](../output-reference/classes/ClinvarScvClinicalSignificanceStatement.md) | Why |
| --- | --- | --- | --- |
| Proposition | a `VariantClinicalSignificanceProposition` | a `#/propositionSomaticClinicalImpact/` pointer to one | Same. |
| Classification codes and systems | AMP/ASCO/CAP 2017: `tier i`, `tier ii`, `tier iii`, `tier iv` | the same. The coding is required. | Same. |
| Tier name | `classification.name` is `Tier I`, `Tier II`, `Tier III` or `Tier IV` | `classification.primaryCoding.name` is `Tier I` … `Tier IV`; `classification.name` is ClinVar's label, such as `Tier I - Strong` | **Difference.** The canonical term name belongs to the coding. The name of the classification is the producer's to present. |
| Strength | AMP/ASCO/CAP 2017: tier i `strong`, tier ii `potential` (required) | the same; tier iii and tier iv carry no strength | Same, and stricter: tiers III and IV have no strength in the guidelines. |
| Direction | tier i and ii `supports`, tier iii `neutral`, tier iv `disputes` | the same | Same. |
| `specifiedBy` | required | optional | **Difference.** As for ACMG 2015. |
| Evidence lines | tier I and II: therapeutic, diagnostic or prognostic evidence lines | `#/evidenceLine/` pointers to [ClinvarSomaticEvidenceLine](../output-reference/classes/ClinvarSomaticEvidenceLine.md)s, whose outcome is named `Level A/B` (tier i) or `Level C/D` (tier ii), without a coding | Allowed (pointers are references). ClinVar reports the evidence level only as A/B or C/D, which is not a single AMP/ASCO/CAP level to code. |

---

## Record counts

How many SCVs in a release conform to each community profile as written, and why the others do not. A record is
counted once under each reason it fails. The counts are regenerated by hand for each monthly full release with
`src/scripts/community-profile-conformance.py <bundle> --write-docs docs/profiles/community-profiles.md`.

<!-- community-conformance:start -->
Counts appear here from the first 1.3.0 monthly full release.
<!-- community-conformance:end -->
