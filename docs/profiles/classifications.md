# Classifications

!!! abstract "What this page answers"
    Which classification values each statement type allows, and the `direction` and `strength` each value maps to
    in a statement. Read it when you filter or compare classifications, or need to know why a statement says
    `supports` or `likely`.

Each statement type has a set list of classification values to which ClinVar normalizes historic or similar classification terms used by some submitters. These classification terms are mapped to the GKS VA statement class' **direction** and **strength**.

**System** is the guideline whose code an SCV's classification carries (its `primaryCoding.system`), by short name; [Community Profiles](community-profiles.md#guideline-systems) gives each system's full value and compares the SCVs with the VA-Spec community profiles for ACMG 2015, CCV 2022 and AMP/ASCO/CAP 2017.

## Germline Classification

The Germline Classification category groups 9 statement types.

| # | Statement Type | Classification | System | Direction | Strength |
| --- | --- | --- | --- | --- | --- |
| G.01 | Pathogenicity | Pathogenic | ACMG 2015 | supports | definitive |
|  |  | Pathogenic, low penetrance | ClinGen 2024 | supports | definitive |
|  |  | Established risk allele | ClinGen 2024 | supports | definitive |
|  |  | Likely pathogenic | ACMG 2015 | supports | likely |
|  |  | Likely pathogenic, low penetrance | ClinGen 2024 | supports | likely |
|  |  | Likely risk allele | ClinGen 2024 | supports | likely |
|  |  | Pathogenic/Likely pathogenic | ClinVar | supports | \<null\> |
|  |  | Uncertain significance | ACMG 2015 | neutral | \<null\> |
|  |  | VUS-high | SVCv4 | neutral | high |
|  |  | VUS-mid | SVCv4 | neutral | mid |
|  |  | VUS-low | SVCv4 | neutral | low |
|  |  | Uncertain risk allele | ClinGen 2024 | neutral | \<null\> |
|  |  | conflicting data from submitters | ClinVar | neutral | \<null\> |
|  |  | Benign | ACMG 2015 | disputes | definitive |
|  |  | Likely benign | ACMG 2015 | disputes | likely |
|  |  | Benign/Likely benign | ClinVar | disputes | \<null\> |
| G.02 | Drug Response | drug response | ClinVar | supports | \<null\> |
| G.03 | Risk Factor | risk factor | ClinVar | supports | \<null\> |
| G.04 | Protective | protective | ClinVar | supports | \<null\> |
| G.05 | Affects | Affects | ClinVar | supports | \<null\> |
| G.06 | Association | association | ClinVar | supports | \<null\> |
|  |  | association not found | ClinVar | disputes | \<null\> |
| G.07 | Confers Sensitivity | confers sensitivity | ClinVar | supports | \<null\> |
| G.08 | Other | other | ClinVar | supports | \<null\> |
| G.09 | Not Provided | not provided | ClinVar | supports | \<null\> |

## Oncogenicity Classification

The Oncogenicity Classification category groups only 1 statement type.

| # | Statement Type | Classification | System | Direction | Strength |
| --- | --- | --- | --- | --- | --- |
| O.10 | Oncogenicity | Oncogenic | CCV 2022 | supports | definitive |
|  |  | Likely oncogenic | CCV 2022 | supports | likely |
|  |  | Uncertain significance | CCV 2022 | neutral | \<null\> |
|  |  | Benign | CCV 2022 | disputes | definitive |
|  |  | Likely benign | CCV 2022 | disputes | likely |

## Somatic Clinical Impact

The Somatic Clinical Impact category groups 1 primary statement type with up to 3 evidence statement types.

### Clinical Significance (Primary)

| # | Statement Type | Classification | System | Direction | Strength |
| --- | --- | --- | --- | --- | --- |
| S.11 | Clinical Significance | Tier I - Strong | AMP/ASCO/CAP 2017 | supports | strong |
|  |  | Tier II - Potential | AMP/ASCO/CAP 2017 | supports | potential |
|  |  | Tier III - Unknown | AMP/ASCO/CAP 2017 | neutral | \<null\> |
|  |  | Tier IV - Benign/Likely benign | AMP/ASCO/CAP 2017 | disputes | \<null\> |

### Evidence Statement Types

All Tier I and II Clinical Significance statements MUST have at least one of the following statement types as evidence. These sub-statement types are critical to Tier I and II clinical significance submissions in ClinVar.

| # | Statement Type | Direction | Strength |
| --- | --- | --- | --- |
| S.12 | Therapeutic Response | supports | strong or potential |
| S.13 | Diagnostic | supports | strong or potential |
| S.14 | Prognostic | supports | strong or potential |
