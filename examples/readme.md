# Examples

Example records illustrating the Cat-VRS and VA-Spec structures this project produces. They help early adopters
and serve as reference targets for validating output.

## Format: bundle fragments

Each file is a small fragment of a bundle, with the same shape as a published bundle:

```json
{
  "schema_version": "1.2.0",
  "<section>": { "<key>": { ... } },
  ...
}
```

It holds one **top record**, the record the file is named for, exactly as the bundle has it. Its references are
`#/<section>/<key>` pointers, as in the bundle, not inline objects. The file also holds the records those pointers
lead to, following pointers from those records in turn, with one exception.

**The rule:** every pointer is followed, except pointers into the `scv` and `variation` sections. Those stay
pointers, and their records are not in the file:

- `#/scv/…`: the submissions that a VCV or RCV statement aggregates. The `scv/` files are examples of SCVs.
- `#/variation/…`: a proposition's `subject`. The two `cat-vrs/` files are examples of variations.

Pointers into `vcv` and `rcv` are followed, so a VCV or RCV file holds the whole aggregation hierarchy below its top
statement: every nested layer statement (for example a `…-G-PATH` statement's evidence line points to `…-G-PATH-CP`;
a somatic `…-S-SCI-CP` points on to `…-S-SCI-CP-T1`), each with its proposition, evidence lines, and condition or
condition set. The hierarchy ends at the `#/scv/` pointers of the lowest layer. An SCV file holds the statement, its
proposition, its submitter, its condition or condition set (with the set's member conditions), and any evidence line
and therapy. A cat-vrs file holds the variation with its alleles, locations, sequence references and genes, so every
pointer in it resolves.

Every file validates against the bundle schema,
[`clinvar-gkm-bundle.schema.json`](../schema/clinvar-gkm/clinvar-gkm-bundle.schema.json). The schema cannot check
that pointers resolve, and these fragments do not promise it: a pointer into `scv` or `variation` names a record in the
full bundle of the same release. A published bundle, full or delta, does resolve every pointer. For a
closed extract of a few statements, see [`sub-bundle.py`](../docs/pipeline/sub-bundle.md).

## Layout and naming

Files are keyed by their ClinVar accession so they map directly back to the bundle:

- **`cat-vrs/clinvar:{variationId}.jsonc`**: a `CategoricalVariant` (`variation` section).
- **`scv/{SCV}.{version}-{code}.jsonc|.json`**: the VA-Spec `Statement` for one submission (`scv` section, key
  `clinvar.submission:{SCV}.{version}`).
- **`vcv/{VCV}.{version}-{group}-{code}.jsonc`**: the top aggregate VCV `Statement` (`vcv` section, same key) and
  its nested layer statements.
- **`rcv/{RCV}.{version}-{group}-{code}.jsonc`**: the top RCV `Statement` (`rcv` section, same key) and its nested
  layer statements.

The files are plain JSON (none has comments); the `.jsonc` names are kept so links to them stay stable.

Suffix codes: `G` / `S` = germline / somatic context; statement type is `PATH` (pathogenicity),
`NP` (not provided), `ASSOC` (association), `DR` (drug response), `RF` (risk factor),
`ONCO` (oncogenicity), or `SCI` (somatic clinical impact). Somatic clinical-impact SCV files add a tier
and scenario, for example `-S-SCI-T1-TR` (Tier I, therapeutic response), `-T2-DIAG`, `-T3-VUS`, `-T4-BLB`.

See the [Examples](../docs/data-access/examples.md) docs page for a described list.

## Regenerating

[`src/scripts/extract-example.py`](../src/scripts/extract-example.py) writes every file from one published full
bundle, in the assembler's one-record-per-line layout. The list of examples (`EXAMPLES`) is in the script; it names
each example by accession, so when ClinVar issues a new version, the file is renamed and the script prints the rename
so links to it can be fixed. Records are copied from the bundle verbatim. The run makes three streaming passes over
the bundle (about 4 minutes for a full):

```bash
python3 src/scripts/extract-example.py --bundle clinvar-gkm_YYYY-MM.json.gz --all
```

`--schema-version` overrides the `schema_version` written to the files. To print one fragment instead, pass a section
and a key: `extract-example.py --bundle <bundle> vcv VCV000012582.69-G-PATH`.

To validate a file, gzip it and run the official toolkit engine, which reads any JSON layout (the default `rs`
engine reads only the bundle's one-record-per-line layout, and these files are indented):
`gzip -c examples/vcv/VCV000012582.69-G-PATH.jsonc > /tmp/x.json.gz && src/scripts/validate-bundle.sh /tmp/x.json.gz --engine toolkit`.

The current files come from the first 1.2.0 full bundle, `v1/1.2/clinvar-gkm_2026-11.json.gz` (built from the
2026-10-31 release; sha256 `157ef338…`), regenerated on 2026-11-23. Every file validates against the 1.2.0 bundle
schema (42 files, 425 records, 0 failing).
