# Examples

Annotated, self-contained example records illustrating the Cat-VRS and VA-Spec structures this
project produces. They assist early adopters and serve as reference targets for validating output.

Each file is regenerated from a single fixed release via
[`src/scripts/extract-example.py`](../src/scripts/extract-example.py): it pulls one record from the
release's BigQuery tables using the repo's own object-construction SQL (so a record equals what the
release ships) and resolves its `#/…` references inline. By policy the **top** statement's direct
references are inlined, while **nested** statements and the `variation` / `scv` subjects are kept as
`#/…` pointers into the full bundle (to avoid unbounded expansion).

## Layout and naming

Files are keyed by their ClinVar accession so they map directly back to the bundle:

- **`cat-vrs/clinvar:{variationId}.jsonc`** — `CategoricalVariant` records (resolved VRS).
- **`scv/{SCV}.{version}-{code}.jsonc|.json`** — VA-Spec `Statement` for one submission.
- **`vcv/{VCV}.{version}-{group}-{code}.jsonc`** — aggregate VCV `Statement`.
- **`rcv/{RCV}.{version}-{group}-{code}.jsonc`** — RCV `Statement`.

Suffix codes: `G` / `S` = germline / somatic context; statement type is `PATH` (pathogenicity),
`NP` (not provided), `ASSOC` (association), `DR` (drug response), `RF` (risk factor),
`ONCO` (oncogenicity), or `SCI` (somatic clinical impact). Somatic clinical-impact files add a tier
and scenario, e.g. `-S-SCI-T1-TR` (Tier I, therapeutic response), `-T2-DIAG`, `-T3-VUS`, `-T4-BLB`.

See the [Examples](../docs/data-access/examples.md) docs page for a curated, described subset.
