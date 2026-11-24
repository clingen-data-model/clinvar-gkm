# Strict Profiles, Fast Tables

A 27-slide explainer for people who use ClinVar-GKM data. It shows why the GA4GH GKM specifications — VRS,
Cat-VRS, VA-Spec and gkm-core — are written to be open and flexible, and how ClinVar-GKM narrows them into
**strict implementation profiles** that describe exactly the data ClinVar produces. It then shows what that
strictness gives the JSON bundles and the **Parquet tables** built from them: a default column set that holds the
whole bundle, and slices and mini-bundles cut down to a specific use.

!!! info "Educational preview — not presented at an event"
    This deck was not given as a talk. It is a self-paced preview that explains how and why strict implementation
    profiles and Parquet extraction are useful. The speaker notes (`S`) carry the narration for each slide.

<p>
  <a class="md-button md-button--primary"
     href="../../assets/presentations/clinvar-gkm-strict-profiles.html"
     target="_blank" rel="noopener">Open the presentation (fullscreen) ↗</a>
</p>

The deck is interactive — use the arrow keys to navigate. The preview below runs the same deck inline; open it
fullscreen (link above) to read it at full size.

<iframe src="../../assets/presentations/clinvar-gkm-strict-profiles.html"
        style="width:100%; height:520px; border:1px solid rgba(128,128,128,.25); border-radius:8px;"
        title="ClinVar-GKM — Strict Profiles, Fast Tables presentation"
        loading="lazy"></iframe>

## Keyboard shortcuts

| Key | Action |
| --- | --- |
| `→` · `Space` | Next slide |
| `←` | Previous slide |
| `Home` / `End` | First / last slide |
| `S` or `N` | Toggle speaker notes |
| `T` | Toggle light / dark theme |
| `F` | Toggle fullscreen |
| `?` | Show / hide the shortcut help |

## What it covers

The deck describes schema 1.2.0 and the `gkm-bundle-parquet` 2.0.0 tool, as of November 2026.

1. **Open specs, strict profiles** — why base classes are open; three layers that only restrict (base classes,
   standard profiles and recipes, implementation profiles); five ways a profile narrows; a proposition and a
   variant traced end to end
2. **What ClinVar-GKM materializes** — the subset of each specification it uses, where it stands on the ACMG 2015
   statement profile, and the ClinVar profiles it adds where no standard exists yet
3. **The 1.2.0 narrowing** — what was pruned, locked and made required, and what the bundles now guarantee
4. **Parquet from the bundle** — Parquet as a reversible projection of the bundle; a default column set generated
   from the schema; why a narrowed schema makes narrower, typed, joinable tables
5. **Why every producer should narrow** — what open schemas do to generated tables, and the narrow-and-require
   approach recommended for any GKM implementation
6. **Slices and mini-bundles** — from the full default set to SQL slices, mini-bundles and named projections, with
   use-case recipes

For the details behind each part, see [An Implementation Schema](../../output-reference/classes/index.md#an-implementation-schema),
[Changelog](../changelog.md) and [Release Validation](../release-validation.md).

!!! note "Source"
    A single self-contained HTML file:
    [`docs/assets/presentations/clinvar-gkm-strict-profiles.html`](https://github.com/clingen-data-model/clinvar-gkm/blob/main/docs/assets/presentations/clinvar-gkm-strict-profiles.html).
    No external dependencies; works offline.
