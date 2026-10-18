#!/usr/bin/env python3
"""Summarize the CSVs written by collect-download-stats.sh.

Estimates complete downloads of each JSON bundle as the bytes served with a 2xx status
divided by the object's current size, so ten half downloads count as five. Prints one
table per bundle kind (monthly fulls, deltas) and a per-category summary of every other
file. Distinct clients are counted per day by the collector, so across several days
they are reported as "client-days" (the sum of the daily counts), not as unique clients.

Object sizes come from the published v1/index.json (monthly fulls) plus a HEAD request
for any other bundle path (default), or from an R2 listing of the whole bucket
(--sizes-from r2, needs the `r2` AWS profile). Sizes are today's: a file republished
since the stats were collected may have had a slightly different size.

Usage:
  summarize-download-stats.py [--sizes-from index|r2] CSV_OR_DIR [CSV_OR_DIR ...]
"""
import argparse
import csv
import glob
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

BASE_URL = os.environ.get("R2_PUBLIC_URL", "https://data.clinvar-gkm.org")
R2_ENDPOINT = "https://09208aa33790838db213a21f630c33e7.r2.cloudflarestorage.com"
R2_BUCKET = "clinvar-gkm"
# Cloudflare answers 403 to the default Python-urllib user agent.
HEADERS = {"User-Agent": "clinvar-gkm-summarize-download-stats"}


def read_rows(inputs):
    files = []
    for p in inputs:
        files.extend(sorted(glob.glob(os.path.join(p, "*.csv"))) if os.path.isdir(p) else [p])
    rows = []
    for f in files:
        with open(f, newline="") as fh:
            for r in csv.DictReader(fh):
                rows.append({
                    "date": r["date"], "path": r["path"], "status": int(r["status"]),
                    "requests": int(r["requests"]), "bytes": int(r["bytes"]),
                    "clients": int(r["distinct_clients"]),
                })
    return rows


def kind_of(path):
    if path.endswith(".json.gz"):
        return "delta" if "clinvar-gkm-delta_" in path else "full"
    if path.endswith(".parquet"):
        return "parquet"
    if re.search(r"(index|manifest|MANIFEST)\.json$|feed\.xml$|README\.txt$", path):
        return "index/manifest/feed"
    return "other"


def where_of(path):
    if re.match(r"^/archive/", path) or "/archives/" in path:
        return "archive"
    if re.match(r"^/v\d+/", path):
        return path.split("/")[1]
    return "flat-root (retired)"


def sizes_from_index():
    req = urllib.request.Request(f"{BASE_URL}/v1/index.json", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        idx = json.load(resp)
    sizes = {"/" + f["path"]: f["size"] for f in idx["datasets"]["monthly"]}
    for year in idx.get("archives", {}).values():
        sizes.update({"/" + f["path"]: f["size"] for f in year.get("monthly", [])})
    return sizes


def head_size(path):
    req = urllib.request.Request(BASE_URL + path, method="HEAD", headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            n = resp.headers.get("Content-Length")
            return int(n) if n else None
    except urllib.error.HTTPError:
        return None


def sizes_from_r2():
    out = subprocess.run(
        ["aws", "s3", "ls", f"s3://{R2_BUCKET}/", "--recursive",
         "--endpoint-url", R2_ENDPOINT, "--profile", "r2"],
        capture_output=True, text=True, check=True).stdout
    sizes = {}
    for line in out.splitlines():
        parts = line.split(None, 3)
        if len(parts) == 4:
            sizes["/" + parts[3]] = int(parts[2])
    return sizes


def gb(n):
    return f"{n / 1e9:8.2f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("inputs", nargs="+", help="CSV files or directories of CSVs")
    ap.add_argument("--sizes-from", choices=("index", "r2"), default="index")
    args = ap.parse_args()

    rows = read_rows(args.inputs)
    if not rows:
        sys.exit("no rows")
    dates = sorted({r["date"] for r in rows})

    per_file = {}
    for r in rows:
        f = per_file.setdefault(r["path"], {"requests": 0, "ok": 0, "bytes": 0, "client_days": 0})
        f["requests"] += r["requests"]
        f["client_days"] += r["clients"]
        if 200 <= r["status"] < 300:
            f["ok"] += r["requests"]
            f["bytes"] += r["bytes"]

    sizes = sizes_from_r2() if args.sizes_from == "r2" else sizes_from_index()
    if args.sizes_from == "index":
        for p in per_file:
            if kind_of(p) in ("full", "delta") and p not in sizes:
                sizes[p] = head_size(p)

    print(f"Download stats for data.clinvar-gkm.org, {dates[0]} to {dates[-1]} "
          f"({len(dates)} days, {len(rows)} rows)")
    print("est. complete = bytes served with a 2xx status / current object size\n")

    for kind, title in (("full", "Monthly full bundles"), ("delta", "Delta bundles")):
        paths = sorted(p for p in per_file if kind_of(p) == kind)
        print(f"== {title} ==")
        if not paths:
            print("  (none)\n")
            continue
        print(f"  {'path':<62} {'where':<20} {'reqs':>5} {'2xx':>5} {'GB served':>9} "
              f"{'size GB':>8} {'est.complete':>12} {'client-days':>11}")
        total = 0.0
        for p in paths:
            f, size = per_file[p], sizes.get(p)
            est = f["bytes"] / size if size else None
            total += est or 0
            print(f"  {p:<62} {where_of(p):<20} {f['requests']:>5} {f['ok']:>5} {gb(f['bytes']):>9} "
                  f"{(gb(size) if size else '       ?'):>8} "
                  f"{(f'{est:.2f}' if est is not None else 'n/a'):>12} {f['client_days']:>11}")
        print(f"  {'total est. complete downloads':<62} {total:.2f}\n")

    print("== Other files ==")
    print(f"  {'category':<22} {'files':>6} {'reqs':>7} {'2xx':>7} {'GB served':>9} {'client-days':>11}")
    for cat in ("parquet", "index/manifest/feed", "other"):
        ps = [p for p in per_file if kind_of(p) == cat]
        agg = {k: sum(per_file[p][k] for p in ps) for k in ("requests", "ok", "bytes", "client_days")}
        print(f"  {cat:<22} {len(ps):>6} {agg['requests']:>7} {agg['ok']:>7} {gb(agg['bytes']):>9} "
              f"{agg['client_days']:>11}")


if __name__ == "__main__":
    main()
