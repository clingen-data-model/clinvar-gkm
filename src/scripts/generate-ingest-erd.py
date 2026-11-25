#!/usr/bin/env python3
"""Generate docs/assets/diagrams/clinvar-ingest-erd.html, the UML diagram of the tables clinvar-ingest builds
from each ClinVar XML release, in the style of the original "ClinVar Phase 1 Model" diagram.

Column names and types come from the BigQuery schemas of one release dataset (`bq show --schema`, metadata
only, no query cost), or from a directory of saved `<table>.json` schema files (--schema-dir). The script
fails if a table has a column the diagram does not list, or lists one the table does not have. Box
positions, relationships and notes are declared below; adjust them when a schema change moves a box.

Usage:
  python3 src/scripts/generate-ingest-erd.py --dataset clinvar_2026_11_22_v2_7_1
  python3 src/scripts/generate-ingest-erd.py --dataset ... --schema-dir DIR   # saved schemas, no bq
  python3 src/scripts/generate-ingest-erd.py --dataset ... --geom             # print box geometry only
"""
import argparse
import html
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
ap.add_argument("--dataset", required=True, help="ClinVar release dataset, e.g. clinvar_2026_11_22_v2_7_1")
ap.add_argument("--project", default="clingen-dev")
ap.add_argument("--schema-dir", help="read <table>.json schemas from here instead of calling bq; "
                                     "with --save-schemas, write them here")
ap.add_argument("--save-schemas", action="store_true", help="fetch with bq and save into --schema-dir")
ap.add_argument("--out", default=os.path.join(REPO, "docs/assets/diagrams/clinvar-ingest-erd.html"))
ap.add_argument("--geom", action="store_true", help="print box geometry and exit")
ARGS = ap.parse_args()
DATASET = ARGS.dataset

TYPE = {"STRING": "string", "INTEGER": "int", "DATE": "date", "TIMESTAMP": "timestamp", "RECORD": "struct"}

# table: (label, kind, x, y, width, columns in display order, key marks)
#   kind: sub = submitter data (green), cv = ClinVar-produced data (blue)
#   marks: col -> "pk" | "fk" | "fk[]"
TABLES = {}


def table(name, label, kind, x, y, w, cols, marks=None, unread=False, rcvfile=False):
    TABLES[name] = dict(label=label, kind=kind, x=x, y=y, w=w, cols=cols, marks=marks or {},
                        unread=unread, rcvfile=rcvfile)


# ---- layout (x, y in px; heights are computed) ----
table("clinical_assertion_variation", "clinical_assertion_variation", "sub", 330, 24, 310,
      ["id", "clinical_assertion_id", "variation_type", "subclass_type", "child_ids", "descendant_ids", "content"],
      {"id": "pk", "clinical_assertion_id": "fk", "child_ids": "fk[]", "descendant_ids": "fk[]"})
table("variation", "variation", "cv", 860, 24, 290,
      ["id", "name", "variation_type", "subclass_type", "allele_id", "protein_change", "num_chromosomes",
       "child_ids", "descendant_ids", "content"],
      {"id": "pk", "child_ids": "fk[]", "descendant_ids": "fk[]"})
table("variation_archive", "variation_archive (VCV)", "cv", 1400, 24, 300,
      ["id", "version", "variation_id", "record_status", "species", "date_created", "date_last_updated",
       "num_submitters", "num_submissions", "content"],
      {"id": "pk", "variation_id": "fk"})
table("variation_archive_classification", "variation_archive_classification", "cv", 1400, 230, 300,
      ["vcv_id", "statement_type", "review_status", "interp_description", "interp_explanation",
       "num_submitters", "num_submissions", "date_created", "date_last_evaluated", "most_recent_submission",
       "clinical_impact_assertion_type", "clinical_impact_clinical_significance", "content"],
      {"vcv_id": "pk, fk", "statement_type": "pk"}, unread=True)
table("gene_association", "gene_association", "cv", 905, 260, 200,
      ["variation_id", "gene_id", "relationship_type", "source", "content"],
      {"variation_id": "pk, fk", "gene_id": "pk, fk"})
table("gene", "gene", "cv", 905, 410, 200, ["id", "hgnc_id", "symbol", "full_name"], {"id": "pk"})

table("submitter", "submitter", "cv", 24, 430, 238,
      ["id", "current_name", "current_abbrev", "org_category", "all_names", "all_abbrevs"], {"id": "pk"})
table("submission", "submission", "cv", 24, 640, 238,
      ["id", "submitter_id", "additional_submitter_ids", "submission_date"],
      {"id": "pk", "submitter_id": "fk", "additional_submitter_ids": "fk[]"})
table("clinical_assertion", "clinical_assertion (SCV)", "sub", 330, 330, 310,
      ["id", "version", "internal_id", "local_key", "title", "assertion_type", "record_status",
       "statement_type", "review_status", "interpretation_description", "interpretation_date_last_evaluated",
       "interpretation_comments", "clinical_impact_assertion_type", "clinical_impact_clinical_significance",
       "date_created", "date_last_updated", "submitted_assembly", "submission_names",
       "variation_archive_id", "variation_id", "submitter_id", "submission_id", "rcv_accession_id",
       "trait_set_id", "clinical_assertion_trait_set_id", "clinical_assertion_observation_ids", "content"],
      {"id": "pk", "statement_type": "fk", "variation_archive_id": "fk", "variation_id": "fk", "submitter_id": "fk",
       "submission_id": "fk", "rcv_accession_id": "fk", "trait_set_id": "fk",
       "clinical_assertion_trait_set_id": "fk", "clinical_assertion_observation_ids": "fk[]"})
table("trait_mapping", "trait_mapping", "cv", 760, 640, 230,
      ["clinical_assertion_id", "trait_type", "mapping_type", "mapping_value", "mapping_ref", "medgen_id",
       "medgen_name"], {"clinical_assertion_id": "fk"})
table("clinical_assertion_observation", "clinical_assertion_observation", "sub", 330, 860, 310,
      ["id", "clinical_assertion_trait_set_id", "content"],
      {"id": "pk", "clinical_assertion_trait_set_id": "fk"}, unread=True)
table("clinical_assertion_trait_set", "clinical_assertion_trait_set", "sub", 330, 1010, 310,
      ["id", "type", "clinical_assertion_trait_ids", "content"],
      {"id": "pk", "clinical_assertion_trait_ids": "fk[]"})
table("clinical_assertion_trait", "clinical_assertion_trait", "sub", 760, 1000, 230,
      ["id", "type", "name", "alternate_names", "medgen_id", "trait_id", "xrefs", "content"],
      {"id": "pk", "trait_id": "fk"})

table("rcv_accession", "rcv_accession (RCV)", "cv", 1400, 520, 300,
      ["id", "version", "title", "variation_archive_id", "variation_id", "trait_set_id",
       "independent_observations", "content"],
      {"id": "pk", "variation_archive_id": "fk", "variation_id": "fk", "trait_set_id": "fk"})
table("rcv_accession_classification", "rcv_accession_classification", "cv", 1400, 700, 300,
      ["rcv_id", "statement_type", "review_status", "agg_classification", "content"],
      {"rcv_id": "pk, fk", "statement_type": "pk"}, unread=True)
table("rcv_mapping", "rcv_mapping", "cv", 1080, 640, 220,
      ["rcv_accession", "scv_accessions", "trait_set_id", "trait_set_content"],
      {"rcv_accession": "fk", "scv_accessions": "fk[]", "trait_set_id": "fk"}, rcvfile=True)
table("trait_set", "trait_set", "cv", 1120, 880, 220, ["id", "type", "trait_ids", "content"],
      {"id": "pk", "trait_ids": "fk[]"})
table("trait", "trait", "cv", 1120, 1010, 220,
      ["id", "type", "name", "symbol", "medgen_id", "gard_id", "alternate_names", "alternate_symbols",
       "keywords", "xrefs", "attribute_content", "public_definition", "gene_reviews_short", "ghr_links",
       "mode_of_inheritance", "disease_mechanism", "disease_mechanism_id", "content"], {"id": "pk"})

# ---- types from the live schema ----
HEAD = 20
ROW = 14
SUBROW = 13


def fetch_schema(name):
    path = os.path.join(ARGS.schema_dir, f"{name}.json") if ARGS.schema_dir else None
    if path and not ARGS.save_schemas:
        with open(path) as fh:
            return json.load(fh)
    raw = subprocess.run(["bq", "show", "--schema", "--format=json", f"{ARGS.project}:{DATASET}.{name}"],
                         check=True, capture_output=True, text=True).stdout
    fields = json.loads(raw)
    if path:
        os.makedirs(ARGS.schema_dir, exist_ok=True)
        with open(path, "w") as fh:
            json.dump(fields, fh, indent=1)
    return fields


def schema(name):
    out = {}
    for f in fetch_schema(name):
        ty = TYPE[f["type"]] + ("[]" if f.get("mode") == "REPEATED" else "")
        out[f["name"]] = (ty, [(g["name"], TYPE[g["type"]]) for g in f.get("fields", [])])
    return out


for name, t in TABLES.items():
    s = schema(name)
    shown = set(t["cols"]) | {"release_date"}
    missing = set(s) - shown
    extra = set(t["cols"]) - set(s)
    assert not missing and not extra, (name, missing, extra)
    rows = []
    for c in t["cols"]:
        ty, sub = s[c]
        if c in ("content", "trait_set_content"):
            ty = "json"
        rows.append((c, ty, t["marks"].get(c, ""), 0))
        for sn, st in sub:
            rows.append((sn, st, "", 1))
    t["rows"] = rows
    t["h"] = HEAD + 4 + sum(ROW if r[3] == 0 else SUBROW for r in rows) + 4


def rowy(name, col):
    """Vertical centre of a column's row."""
    t = TABLES[name]
    y = t["y"] + HEAD + 4
    for c, _, _, lvl in t["rows"]:
        h = ROW if lvl == 0 else SUBROW
        if c == col and lvl == 0:
            return y + h / 2
        y += h
    raise KeyError(col)


if ARGS.geom:
    for n, t in TABLES.items():
        print(f"{n:34s} x={t['x']:5} y={t['y']:5} w={t['w']:4} h={t['h']:4} bottom={t['y']+t['h']:5} right={t['x']+t['w']}")
    sys.exit(0)


# ---- relationship helpers ----
def box(n):
    t = TABLES[n]
    return t["x"], t["y"], t["x"] + t["w"], t["y"] + t["h"]


def L(n, y): return (box(n)[0], y)
def R(n, y): return (box(n)[2], y)
def Tp(n, x): return (x, box(n)[1])
def B(n, x): return (x, box(n)[3])


CA = "clinical_assertion"
CAR = box(CA)[2]          # CA right edge
# Each edge: points (start .. end), ends (start_deco, end_deco), labels [(text, x, y, anchor, cls)]
#   deco: fd = filled diamond (nested in the XML element), od = open diamond (member of a set or tree), "" = none
EDGES = []


def edge(pts, start="", end="", labels=(), cls="r"):
    EDGES.append(dict(pts=pts, start=start, end=end, labels=list(labels), cls=cls))


vx0, vy0, vx1, vy1 = box("variation")
ax0, ay0, ax1, ay1 = box("variation_archive")
cvx0, cvy0, cvx1, cvy1 = box("clinical_assertion_variation")
cx0, cy0, cx1, cy1 = box(CA)
gx0, gy0, gx1, gy1 = box("gene_association")
rx0, ry0, rx1, ry1 = box("rcv_accession")
mx0, my0, mx1, my1 = box("rcv_mapping")
tsx0, tsy0, tsx1, tsy1 = box("trait_set")
tx0, ty0, tx1, ty1 = box("trait")
ox0, oy0, ox1, oy1 = box("clinical_assertion_observation")
sx0, sy0, sx1, sy1 = box("clinical_assertion_trait_set")
kx0, ky0, kx1, ky1 = box("clinical_assertion_trait")
mpx0, mpy0, mpx1, mpy1 = box("trait_mapping")
smx0, smy0, smx1, smy1 = box("submitter")
sbx0, sby0, sbx1, sby1 = box("submission")

# SCV <-> its submitted variation (nested), and the variation tree
edge([Tp(CA, 380), B("clinical_assertion_variation", 380)], start="fd",
     labels=[("1", 388, cy0 - 8, "start", "m"), ("1..*", 388, cvy1 + 14, "start", "m"),
             ("SimpleAllele | Haplotype | Genotype", 388, cvy1 + 30, "start", "lb")])
edge([R("clinical_assertion_variation", cvy1 - 34), (cvx1 + 22, cvy1 - 34), (cvx1 + 22, cvy0 + 30),
      R("clinical_assertion_variation", cvy0 + 30)], end="od",
     labels=[("children", cvx1 + 28, (cvy0 + cvy1) / 2 + 4, "start", "lb"), ("0..*", cvx1 + 6, cvy1 - 40, "start", "m")])
edge([R("variation", vy1 - 34), (vx1 + 22, vy1 - 34), (vx1 + 22, vy0 + 100), R("variation", vy0 + 100)], end="od",
     labels=[("children", vx1 + 28, vy1 - 60, "start", "lb"), ("0..*", vx1 + 6, vy1 - 40, "start", "m")])

# VCV record
edge([L("variation_archive", ay0 + 50), R("variation", ay0 + 50)], start="fd",
     labels=[("1", ax0 - 16, ay0 + 44, "end", "m"), ("1", vx1 + 8, ay0 + 44, "start", "m"),
             ("ClassifiedRecord (root variation)", (vx1 + ax0) / 2, ay0 + 66, "middle", "lb")])
edge([B("variation_archive", 1550), Tp("variation_archive_classification", 1550)], start="fd",
     labels=[("1", 1558, ay1 + 12, "start", "m"), ("0..*", 1558, box("variation_archive_classification")[1] - 4, "start", "m"),
             ("Classifications", 1500, (ay1 + box("variation_archive_classification")[1]) / 2 + 4, "end", "lb")])
edge([R("variation_archive", ay1 - 16), (ax1 + 16, ay1 - 16), (ax1 + 16, ry0 + 24), R("rcv_accession", ry0 + 24)], start="fd",
     labels=[("1", ax1 + 4, ay1 - 22, "start", "m"), ("1..*", ax1 + 4, ry0 + 18, "start", "m"),
             ("RCVList", ax1 - 6, ry0 - 16, "end", "lb")])
edge([B("rcv_accession", 1550), Tp("rcv_accession_classification", 1550)], start="fd",
     labels=[("1", 1558, ry1 + 12, "start", "m"), ("0..*", 1558, box("rcv_accession_classification")[1] - 4, "start", "m"),
             ("RCVClassifications", 1500, (ry1 + box("rcv_accession_classification")[1]) / 2 + 4, "end", "lb")])

# genes
edge([B("variation", 1005), Tp("gene_association", 1005)], start="fd",
     labels=[("1", 1012, vy1 + 12, "start", "m"), ("0..*", 1012, gy0 - 4, "start", "m"),
             ("GeneList", 998, (vy1 + gy0) / 2 + 8, "end", "lb")])
edge([B("gene_association", 1005), Tp("gene", 1005)],
     labels=[("1..*", 1012, gy1 + 12, "start", "m"), ("1", 1012, box("gene")[1] - 4, "start", "m")])

# SCV references up and across
edge([R(CA, cy0 + 215), (CAR + 60, cy0 + 215), (CAR + 60, vy0 + 110), L("variation", vy0 + 110)],
     labels=[("1..*", CAR + 6, cy0 + 209, "start", "m"), ("1", vx0 - 6, vy0 + 104, "end", "m"),
             ("variation_id", CAR + 66, vy0 + 160, "start", "lb")])
edge([R(CA, cy0 + 230), (CAR + 80, cy0 + 230), (CAR + 80, 215), (ax0 - 30, 215), (ax0 - 30, ay1 - 40),
      L("variation_archive", ay1 - 40)], end="fd",
     labels=[("1..*", CAR + 6, cy0 + 226, "start", "m"), ("1", ax0 - 6, ay1 - 46, "end", "m"),
             ("ClinicalAssertionList", 1240, 209, "middle", "lb")])
edge([R(CA, cy0 + 262), L("rcv_accession", cy0 + 262)],
     labels=[("1..*", CAR + 6, cy0 + 258, "start", "m"), ("1", rx0 - 6, cy0 + 256, "end", "m"),
             ("rcv_accession_id", 1150, cy0 + 256, "middle", "lb")])
# SCV -> its VCV and RCV classification for the SCV's own statement type (composite keys)
cvx0_, cvy0_, cvx1_, cvy1_ = box("variation_archive_classification")
edge([R(CA, cy0 + 246), (CAR + 100, cy0 + 246), (CAR + 100, cvy0_ + 154), L("variation_archive_classification", cvy0_ + 154)],
     labels=[("1..*", CAR + 6, cy0 + 242, "start", "m"), ("0..1", cvx0_ - 6, cvy0_ + 148, "end", "m"),
             ("variation_archive_id + statement_type", 1230, cvy0_ + 148, "middle", "lb")])
rax0_, ray0_, rax1_, ray1_ = box("rcv_accession_classification")
edge([R(CA, cy0 + 278), (rax0_ - 15, cy0 + 278), (rax0_ - 15, ray0_ + 50), L("rcv_accession_classification", ray0_ + 50)],
     labels=[("1..*", CAR + 6, cy0 + 274, "start", "m"), ("0..1", rax0_ - 20, ray0_ + 54, "end", "m"),
             ("rcv_accession_id + statement_type", 1150, cy0 + 292, "middle", "lb")])
edge([R(CA, mpy0 + 16), L("trait_mapping", mpy0 + 16)], start="fd",
     labels=[("1", CAR + 6, mpy0 + 10, "start", "m"), ("0..*", mpx0 - 6, mpy0 + 10, "end", "m"),
             ("TraitMappingList", (CAR + mpx0) / 2 + 8, mpy0 + 30, "middle", "lb")])
edge([R(CA, cy1 - 24), (CAR + 45, cy1 - 24), (CAR + 45, tsy0 + 60), L("trait_set", tsy0 + 60)],
     labels=[("1..*", CAR + 6, cy1 - 28, "start", "m"), ("1", tsx0 - 6, tsy0 + 54, "end", "m"),
             ("trait_set_id", 1000, tsy0 + 54, "middle", "lb")])
edge([R(CA, cy1 - 8), (CAR + 22, cy1 - 8), (CAR + 22, sy0 + 40), R("clinical_assertion_trait_set", sy0 + 40)], start="od",
     labels=[("1", CAR + 6, cy1 + 4, "start", "m"), ("0..1", sx1 + 6, sy0 + 34, "start", "m"),
             ("TraitSet", CAR + 28, sy0 + 10, "start", "lb")])

# observations and submitted traits
edge([B(CA, 400), Tp("clinical_assertion_observation", 400)], start="fd",
     labels=[("1", 408, cy1 + 14, "start", "m"), ("0..*", 408, oy0 - 6, "start", "m"),
             ("ObservedInList", 392, (cy1 + oy0) / 2 + 4, "end", "lb")])
edge([B("clinical_assertion_observation", 400), Tp("clinical_assertion_trait_set", 400)], start="od",
     labels=[("1", 408, oy1 + 14, "start", "m"), ("0..1", 408, sy0 - 6, "start", "m"),
             ("TraitSet", 392, (oy1 + sy0) / 2 + 4, "end", "lb")])
edge([R("clinical_assertion_trait_set", sy1 - 14), L("clinical_assertion_trait", sy1 - 14)], start="fd",
     labels=[("1", sx1 + 6, sy1 - 20, "start", "m"), ("1..*", kx0 - 6, sy1 - 20, "end", "m")])
edge([R("clinical_assertion_trait", ky0 + 90), L("trait", ky0 + 90)],
     labels=[("1..*", kx1 + 6, ky0 + 84, "start", "m"), ("0..1", tx0 - 6, ky0 + 84, "end", "m"),
             ("trait_id", (kx1 + tx0) / 2, ky0 + 104, "middle", "lb")])

# RCV file mapping
edge([L("rcv_mapping", my0 + 30), (mx0 - 24, my0 + 30), (mx0 - 24, mpy1 + 34), (CAR + 100, mpy1 + 34),
      (CAR + 100, cy1 - 40), R(CA, cy1 - 40)],
     labels=[("1..*", CAR + 6, cy1 - 44, "start", "m"), ("scv_accessions[]", 880, mpy1 + 28, "middle", "lb")])
edge([R("rcv_mapping", my0 + 14), L("rcv_accession", my0 + 14)],
     labels=[("1", rx0 - 6, my0 + 8, "end", "m"), ("rcv_accession", (mx1 + rx0) / 2 - 10, my0 + 28, "middle", "lb")])
edge([B("rcv_mapping", 1240), Tp("trait_set", 1240)],
     labels=[("1", 1248, tsy0 - 6, "start", "m"), ("trait_set_id", 1248, (my1 + tsy0) / 2 + 4, "start", "lb")])
edge([R("rcv_accession", ry1 - 20), (ax1 + 16, ry1 - 20), (ax1 + 16, tsy0 + 6), R("trait_set", tsy0 + 6)], end="fd",
     labels=[("1..*", ax1 + 4, ry1 - 26, "start", "m"), ("1", tsx1 + 22, tsy0 - 0, "start", "m"),
             ("ClassifiedConditionList", 1550, tsy0 + 20, "middle", "lb")])
edge([B("trait_set", 1230), Tp("trait", 1230)], start="od",
     labels=[("1..*", 1238, tsy1 + 14, "start", "m"), ("0..*", 1238, ty0 - 6, "start", "m")])

# submitters
edge([B("submitter", 70), Tp("submission", 70)],
     labels=[("1", 78, smy1 + 14, "start", "m"), ("0..*", 78, sby0 - 6, "start", "m"),
             ("primary", 62, (smy1 + sby0) / 2 + 4, "end", "lb")])
edge([B("submitter", 190), Tp("submission", 190)],
     labels=[("0..*", 198, smy1 + 14, "start", "m"), ("0..*", 198, sby0 - 6, "start", "m"),
             ("additional", 182, (smy1 + sby0) / 2 + 4, "end", "lb")])
edge([R("submitter", smy0 + 40), L(CA, smy0 + 40)],
     labels=[("1", smx1 + 6, smy0 + 34, "start", "m"), ("1..*", cx0 - 6, smy0 + 34, "end", "m"),
             ("submitter_id", (smx1 + cx0) / 2, smy0 + 56, "middle", "lb")])
edge([R("submission", sby0 + 40), L(CA, sby0 + 40)], start="od",
     labels=[("1", sbx1 + 10, sby0 + 34, "start", "m"), ("1..*", cx0 - 6, sby0 + 34, "end", "m"),
             ("submission_id", (sbx1 + cx0) / 2, sby0 + 56, "middle", "lb")])

# ---- notes ----
NOTES = []


def note(x, y, w, lines, to=None):
    NOTES.append(dict(x=x, y=y, w=w, lines=lines, to=to))


note(24, 352, 220, ["ID = OrgID. One row per submitter."], to=(110, smy0))
note(24, sby1 + 24, 280, ["ID = OrgID.SubmissionDate (3.2019-10-14).",
                          "Submission names stay on the SCV",
                          "(clinical_assertion.submission_names)."], to=(110, sby1))
note(410, 212, 230, ["ID = SCV accession; internal_id is",
                     "ClinVar's integer record ID.",
                     "rcv_accession_id is filled in from",
                     "rcv_mapping after the load."], to=(520, cy0))
note(24, 850, 280, ["content holds Sample, Method,",
                    "ObservedData and FunctionalData: the",
                    "case-level and functional evidence not",
                    "yet in GKM. bq-tools already parses",
                    "them (parseSample, parseMethods,",
                    "parseObservedData)."], to=(ox0, oy0 + 40))
note(24, 1010, 280, ["ID = SCV for the assertion's TraitSet,",
                     "SCV.n for an observation's TraitSet.",
                     "clinical_assertion_trait.id =",
                     "<trait set id>.n"], to=(sx0, sy0 + 40))
note(752, 250, 140, ["key = variation_id", "+ gene_id"], to=(gx0, gy0 + 30))
note(752, 420, 140, ["ID = NCBI GeneID.", "One row per gene."], to=(gx0, box("gene")[1] + 40))
note(752, 812, 238, ["Maps a submitted trait (by name or", "xref) to a MedGen concept; the ingest",
                     "uses it to set", "clinical_assertion_trait.trait_id."], to=(870, mpy1))
note(1370, 1042, 330, ["ID = TraitSetID. Only the record's",
                       "ConditionList TraitSets."], to=(tsx1, tsy0 + 60))
note(1370, 1096, 330, ["ID = TraitID; medgen_id is the MedGen", "CUI from the ConditionList."], to=(tx1, ty0 + 70))
note(1400, 914, 300, ["The two *_classification tables hold one row",
                      "per VCV or RCV and statement type (germline,",
                      "somatic clinical impact, oncogenicity). An SCV",
                      "joins the one for its own statement_type; an",
                      "SCV with no classification provided has no",
                      "statement_type and joins neither. GKM derives",
                      "VCV and RCV classifications from the SCVs, so",
                      "it does not read these tables."], to=None)
note(1370, 1160, 330, ["rcv_mapping comes from the RCV release",
                       "file (ClinVarSet); every other table",
                       "comes from the VCV release file."], to=None)


TEMPLATE = r"""<!DOCTYPE html>
<title>ClinVar ingest model</title>
<meta charset="utf8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- Columns from the live BigQuery schemas of {{DATASET}} (bq show --schema). -->
<style>
  /* Theme-aware tokens, same light/dark contract as the other repo diagrams: a media-query default
     plus explicit :root[data-theme] overrides. Green = submitter data, blue = ClinVar-produced data,
     yellow = notes, as in the original ClinVar Phase 1 Model diagram. */
  :root {
    --bg: #FFFFFF; --ink: #1B2430; --muted: #5B6572; --faint: #8A939E; --rule: #E2E6EA;
    --line: #3B4652; --box: #FFFFFF;
    --sub: #DDF5DA; --sub-hd: #A9E3A3; --sub-bd: #4E8F47;
    --cv: #DCEEFB; --cv-hd: #8CCBF0; --cv-bd: #3F7FA8;
    --note: #FFFBD6; --note-bd: #B8A94A;
    --tag: #9A3B12;
    --sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg: #171D24; --ink: #E7E9EC; --muted: #97A1AC; --faint: #707A85; --rule: #2A323B;
      --line: #A9B3BD; --box: #1B222A;
      --sub: #1C2B1D; --sub-hd: #2F5A2C; --sub-bd: #6FB466;
      --cv: #182633; --cv-hd: #24506E; --cv-bd: #6AAAD4;
      --note: #2E2B17; --note-bd: #8C7F3A;
      --tag: #F0A47E;
    }
  }
  :root[data-theme="dark"] {
    --bg: #171D24; --ink: #E7E9EC; --muted: #97A1AC; --faint: #707A85; --rule: #2A323B;
    --line: #A9B3BD; --box: #1B222A;
    --sub: #1C2B1D; --sub-hd: #2F5A2C; --sub-bd: #6FB466;
    --cv: #182633; --cv-hd: #24506E; --cv-bd: #6AAAD4;
    --note: #2E2B17; --note-bd: #8C7F3A;
    --tag: #F0A47E;
  }

  * { box-sizing: border-box; }
  html, body { margin: 0; background: var(--bg); color: var(--ink); font: 14px/1.5 var(--sans);
    -webkit-font-smoothing: antialiased; }
  /* Natural size; the embedding iframe scrolls when the diagram is wider than the column
     (deliberate repo choice -- no scale-to-fit, matches the other diagrams). */
  .frame { overflow: auto; padding: 4px; }
  svg.erd { display: block; font-family: var(--sans); }

  .tbl .bx { stroke-width: 1.1; }
  .tbl.sub .bx { fill: var(--sub); stroke: var(--sub-bd); }
  .tbl.cv .bx { fill: var(--cv); stroke: var(--cv-bd); }
  .sub .hd { fill: var(--sub-hd); stroke: var(--sub-bd); stroke-width: 1.1; }
  .cv .hd { fill: var(--cv-hd); stroke: var(--cv-bd); stroke-width: 1.1; }
  .tbl.unread .bx, .bx.dash { stroke-dasharray: 5 3; stroke-width: 1.4; }
  .bx.dash { fill: var(--box); stroke: var(--line); }
  .tn { font-size: 11.5px; font-weight: 700; fill: var(--ink); }
  .tn .tag { font-weight: 600; fill: var(--tag); }
  .cl { font-size: 10.5px; fill: var(--ink); }
  .cl.sub { fill: var(--muted); }
  .cl .ty { fill: var(--muted); }
  .mk { font-size: 9.5px; fill: var(--muted); font-style: italic; }

  .r { fill: none; stroke: var(--line); stroke-width: 1.1; }
  .dm.fd { fill: var(--line); stroke: var(--line); stroke-width: 1; }
  .dm.od { fill: var(--bg); stroke: var(--line); stroke-width: 1.1; }
  .m { font-size: 10px; fill: var(--ink); }
  .lb { font-size: 10px; fill: var(--muted); }

  .nt { fill: var(--note); stroke: var(--note-bd); stroke-width: 1; }
  .nf { fill: none; stroke: var(--note-bd); stroke-width: 1; }
  .nl { fill: none; stroke: var(--faint); stroke-width: 1; stroke-dasharray: 3 3; }
  .ntx { font-size: 10.5px; fill: var(--ink); }

  .lgbox { fill: var(--box); stroke: var(--rule); stroke-width: 1; }
  .lgt { font-size: 13px; font-weight: 700; fill: var(--ink); }
  .lgd { font-size: 10.5px; fill: var(--ink); }
</style>
<div class="frame">
{{SVG}}
</div>
"""


# ---- render ----
def esc(s):
    return html.escape(str(s), quote=True)


CHAR = 5.2   # ~10.5px system sans advance, for width checks (measured against the render)


def render_box(n):
    t = TABLES[n]
    x, y, w, h = t["x"], t["y"], t["w"], t["h"]
    k = t["kind"]
    o = [f'<g class="tbl {k}{" unread" if t["unread"] else ""}" id="t-{n}">']
    o.append(f'<rect class="bx" x="{x}" y="{y}" width="{w}" height="{h}"/>')
    o.append(f'<rect class="hd" x="{x}" y="{y}" width="{w}" height="{HEAD}"/>')
    label = t["label"]
    if t["rcvfile"]:
        o.append(f'<text class="tn" x="{x + w / 2}" y="{y + 14}" text-anchor="middle">{esc(label)}'
                 f'<tspan class="tag"> · RCV file</tspan></text>')
    else:
        o.append(f'<text class="tn" x="{x + w / 2}" y="{y + 14}" text-anchor="middle">{esc(label)}</text>')
    yy = y + HEAD + 4
    for c, ty, mark, lvl in t["rows"]:
        rh = ROW if lvl == 0 else SUBROW
        ind = 8 + lvl * 14
        txt = f"{c} : {ty}"
        need = ind + len(txt) * CHAR + (len(mark) * CHAR + 14 if mark else 0) + 8
        if need > w:
            print(f"WARN {n}.{c} needs ~{need:.0f}px > {w}", file=sys.stderr)
        cls = "cl sub" if lvl else "cl"
        o.append(f'<text class="{cls}" x="{x + ind}" y="{yy + rh - 3.5}">{esc(c)}<tspan class="ty"> : {esc(ty)}</tspan></text>')
        if mark:
            o.append(f'<text class="mk" x="{x + w - 7}" y="{yy + rh - 3.5}" text-anchor="end">{esc(mark)}</text>')
        yy += rh
    o.append("</g>")
    return "\n".join(o)


def deco(p, q, kind):
    """Diamond at p, pointing along p->q."""
    if not kind:
        return ""
    import math
    dx, dy = q[0] - p[0], q[1] - p[1]
    L_ = math.hypot(dx, dy) or 1
    ux, uy = dx / L_, dy / L_
    px, py = -uy, ux
    a = p
    b = (p[0] + ux * 8 + px * 5, p[1] + uy * 8 + py * 5)
    c = (p[0] + ux * 16, p[1] + uy * 16)
    d = (p[0] + ux * 8 - px * 5, p[1] + uy * 8 - py * 5)
    pts = " ".join(f"{v[0]:.1f},{v[1]:.1f}" for v in (a, b, c, d))
    return f'<polygon class="dm {"fd" if kind == "fd" else "od"}" points="{pts}"/>'


HOP = 4.5


def segments(i):
    pts = EDGES[i]["pts"]
    return list(zip(pts, pts[1:]))


def hop_path(i):
    """Orthogonal path; a horizontal segment hops (small arc) over any other edge's vertical segment it crosses."""
    verts = []
    for j in range(len(EDGES)):
        if j == i:
            continue
        for (x1, y1), (x2, y2) in segments(j):
            if x1 == x2:
                verts.append((x1, min(y1, y2), max(y1, y2)))
    pts = EDGES[i]["pts"]
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if y1 == y2:
            lo, hi = min(x1, x2), max(x1, x2)
            xs = sorted({vx for vx, vy0, vy1 in verts
                         if lo + HOP < vx < hi - HOP and vy0 + 1 < y1 < vy1 - 1}, reverse=x2 < x1)
            sgn = 1 if x2 > x1 else -1
            for vx in xs:
                d += f" L{vx - sgn * HOP:.1f},{y1:.1f} A{HOP},{HOP} 0 0 {1 if sgn > 0 else 0} {vx + sgn * HOP:.1f},{y1:.1f}"
        d += f" L{x2:.1f},{y2:.1f}"
    return d


def render_edge(e):
    pts = e["pts"]
    d = hop_path(EDGES.index(e))
    o = [f'<path class="{e["cls"]}" d="{d}"/>']
    o.append(deco(pts[0], pts[1], e["start"]))
    o.append(deco(pts[-1], pts[-2], e["end"]))
    for text, lx, ly, anchor, cls in e["labels"]:
        o.append(f'<text class="{cls}" x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}">{esc(text)}</text>')
    return "\n".join(x for x in o if x)


def render_note(nt):
    x, y, w = nt["x"], nt["y"], nt["w"]
    h = 10 + len(nt["lines"]) * 13
    o = []
    if nt["to"]:
        tx, ty = nt["to"]
        cx = min(max(tx, x), x + w)
        cy = y if ty < y else (y + h if ty > y + h else ty)
        if x <= tx <= x + w:
            sx, sy = tx, (y if ty < y else y + h)
        else:
            sx, sy = (x if tx < x else x + w), min(max(ty, y + 6), y + h - 6)
        o.append(f'<path class="nl" d="M{sx:.1f},{sy:.1f} L{tx:.1f},{ty:.1f}"/>')
    f = 8
    o.append(f'<path class="nt" d="M{x},{y} H{x + w - f} L{x + w},{y + f} V{y + h} H{x} Z"/>')
    o.append(f'<path class="nf" d="M{x + w - f},{y} V{y + f} H{x + w}"/>')
    for i, line in enumerate(nt["lines"]):
        o.append(f'<text class="ntx" x="{x + 7}" y="{y + 15 + i * 13}">{esc(line)}</text>')
    return "\n".join(o)


def legend():
    x, y = 24, 24
    o = [f'<rect class="lgbox" x="{x}" y="{y}" width="280" height="262"/>',
         f'<text class="lgt" x="{x + 10}" y="{y + 20}">ClinVar ingest model</text>']
    desc = ["The tables clinvar-ingest builds in BigQuery",
            "from each ClinVar XML release, one dataset",
            "per release (clinvar_YYYY_MM_DD_vX_Y_Z).",
            f"Columns as of {DATASET};",
            "every table also has release_date."]
    for i, line in enumerate(desc):
        o.append(f'<text class="lgd" x="{x + 10}" y="{y + 40 + i * 13}">{esc(line)}</text>')
    yy = y + 118
    for cls, text in (("sub", "Submitter data"), ("cv", "ClinVar-produced data"), ("nt", "Notes")):
        if cls == "nt":
            o.append(f'<rect class="nt" x="{x + 10}" y="{yy - 10}" width="22" height="14"/>')
        else:
            o.append(f'<g class="{cls}"><rect class="hd" x="{x + 10}" y="{yy - 10}" width="22" height="14"/></g>')
        o.append(f'<text class="lgd" x="{x + 42}" y="{yy + 1}">{text}</text>')
        yy += 21
    o.append(f'<rect class="bx dash" x="{x + 10}" y="{yy - 10}" width="22" height="14"/>')
    o.append(f'<text class="lgd" x="{x + 42}" y="{yy + 1}">Not read by the GKM pipeline</text>')
    yy += 27
    o.append(deco((x + 10, yy - 3), (x + 40, yy - 3), "fd"))
    o.append(f'<path class="r" d="M{x + 26},{yy - 3} H{x + 40}"/>')
    o.append(f'<text class="lgd" x="{x + 48}" y="{yy + 1}">nested in the parent\'s XML element</text>')
    yy += 20
    o.append(deco((x + 10, yy - 3), (x + 40, yy - 3), "od"))
    o.append(f'<path class="r" d="M{x + 26},{yy - 3} H{x + 40}"/>')
    o.append(f'<text class="lgd" x="{x + 48}" y="{yy + 1}">member of a set or a variation tree</text>')
    yy += 20
    o.append(f'<path class="r" d="M{x + 10},{yy - 3} H{x + 40}"/>')
    o.append(f'<text class="lgd" x="{x + 48}" y="{yy + 1}">reference by key (label = key column)</text>')
    return "\n".join(o)


WIDTH = max(t["x"] + t["w"] for t in TABLES.values()) + 24
HEIGHT = max(t["y"] + t["h"] for t in TABLES.values()) + 24
svg = "\n".join([
    f'<svg class="erd" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" role="img" '
    'aria-label="UML entity-relationship diagram of the 18 tables clinvar-ingest builds from the ClinVar XML: '
    'the VCV record (variation_archive, variation, genes, classifications), the SCV (clinical_assertion, its '
    'submitted variation, observations, trait sets and traits, submitter and submission), and the RCV '
    '(rcv_accession, its classifications, rcv_mapping, trait_set and trait).">',
    legend(),
    *[render_note(nt) for nt in NOTES],
    *[render_edge(e) for e in EDGES],
    *[render_box(n) for n in TABLES],
    "</svg>"])

out = TEMPLATE.replace("{{SVG}}", svg).replace("{{DATASET}}", DATASET)
with open(ARGS.out, "w") as fh:
    fh.write(out)
print(f"wrote {ARGS.out} {WIDTH}x{HEIGHT}")
