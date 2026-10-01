# ClinVar-GKM Primer

!!! info "Presented at GA4GH Connect — October 2, 2026"
    This primer was prepared for **GA4GH Connect** (October 2, 2026) to introduce ClinVar-GKM to the GKS community.

A ~8-minute (15-slide) introduction to ClinVar-GKM for a technical audience that knows ClinVar but is new to
**VA-Spec** and the **GKM** model. It covers how ClinVar's complete data is organized today (shown with the
real VCV XML schema), how the newest GKM standards
(VRS 2.1.1 · Cat-VRS 1.1.1 · VA-Spec 1.1.0, on GKM-Core 1.3.0) reorganize it for consistent, accurate access,
the bundle shape and class inventory, a worked example, the
community profiles and ClinVar-specific implementer profiles in play, downloads, the transparency of how the
data is produced, and who is adopting it for production.

<p>
  <a class="md-button md-button--primary"
     href="../../assets/presentations/clinvar-gkm-primer.html"
     target="_blank" rel="noopener">Open the presentation (fullscreen) ↗</a>
</p>

The deck is interactive — use the arrow keys to navigate and hover any **info chip** for a definition. The
preview below runs the same deck inline; open it fullscreen (link above) for presenting.

<iframe src="../../assets/presentations/clinvar-gkm-primer.html"
        style="width:100%; height:520px; border:1px solid rgba(128,128,128,.25); border-radius:8px;"
        title="ClinVar-GKM Primer presentation"
        loading="lazy"></iframe>

## Keyboard shortcuts

| Key | Action |
| --- | --- |
| `→` · `Space` · `PgDn` | Next slide |
| `←` · `PgUp` | Previous slide |
| `Home` / `End` | First / last slide |
| `S` or `N` | Toggle speaker notes |
| `T` | Toggle light / dark theme |
| `F` | Toggle fullscreen |
| `?` | Show / hide the shortcut help |

## Agenda

1. **The starting point** — ClinVar's complete truth is the weekly XML
2. **Anatomy of the XML** — what "just extract the SCVs" really takes (real VCV schema)
3. **What it is** — every ClinVar release rebuilt as one GKM bundle
4. **The GKM stack** — VRS 2.1.1 · Cat-VRS 1.1.1 · VA-Spec 1.1.0 · GKM-Core 1.3.0 (all newly released)
5. **ClinVar → statements** — SCV / VCV / RCV as VA-Spec Statements
6. **The GKM Bundle** — compaction via ids + `#/section/id` pointers (like foreign keys); schema-driven Starter Kit / Toolkit
7. **Class inventory** — the GKM classes in play (MappableConcept, ConceptSet, CategoricalVariant, Allele, CNV Count/Change, Statement, Proposition, EvidenceLine)
8. **Worked example** — `clinvar:10` (HFE p.His63Asp), statement → proposition → variant → VRS
9. **Profiles & recipes** — Cat-VRS recipes and VA-Spec community profiles
10. **Implementer profiles** — custom propositions + ClinVar-specific extensions
11. **Downloads** — monthly full + weekly deltas, JSON & Parquet
12. **Transparency** — how every value is produced and verified
13. **Momentum** — groups adopting it for production
14. **Get started** — docs, libraries, and the feedback loop

!!! note "Source"
    The deck is a single self-contained HTML file:
    [`docs/assets/presentations/clinvar-gkm-primer.html`](https://github.com/clingen-data-model/clinvar-gkm/blob/main/docs/assets/presentations/clinvar-gkm-primer.html).
    It has no external dependencies and works offline.
