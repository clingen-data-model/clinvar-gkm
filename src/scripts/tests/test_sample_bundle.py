"""sample-bundle.py must keep records verbatim, spread them over each section, and write a bundle the engines read."""

import gzip
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "sample-bundle.py"


def assembled(sections):
    lines = ["{\n", '  "schema_version": "9.9.9"']
    for section, records in sections.items():
        body = ",\n".join(f"    {json.dumps(k)}: {json.dumps(r, separators=(',', ':'))}" for k, r in records.items())
        lines.append(f',\n  "{section}": {{\n' + body + "\n  }")
    return "".join(lines) + "\n}\n"


def run(tmp_path, sections, *args):
    src, out = tmp_path / "full.json.gz", tmp_path / "sample.json.gz"
    with gzip.open(src, "wt") as f:
        f.write(assembled(sections))
    subprocess.run([sys.executable, SCRIPT, src, out, *args], check=True, capture_output=True)
    with gzip.open(out, "rt") as f:
        return f.read()


def test_sample_is_spread_verbatim_and_parses(tmp_path):
    big = {f"k{i:03d}": {"n": i, "s": "x é"} for i in range(200)}
    small = {"a": {"n": 1}, "b": {"n": 2}}
    text = run(tmp_path, {"big": big, "small": small}, "--fraction", "0.1", "--min", "5")
    sample = json.loads(text)
    assert sample["schema_version"] == "9.9.9"
    assert len(sample["big"]) == 20 and sample["small"] == small  # 10% of 200; all of a section below --min
    assert {int(k[1:]) // 20 for k in sample["big"]} == set(range(10))  # one in every tenth, not the first 20
    assert all(sample["big"][k] == big[k] for k in sample["big"])
    assert all(f'    "{k}": {json.dumps(big[k], separators=(",", ":"))}' in text for k in sample["big"])


def test_other_layouts_are_refused(tmp_path):
    src = tmp_path / "full.json.gz"
    with gzip.open(src, "wt") as f:
        f.write(json.dumps({"schema_version": "9.9.9", "big": {"a": {"n": 1}}}, indent=1))
    result = subprocess.run([sys.executable, SCRIPT, src, tmp_path / "o.json.gz"], capture_output=True, text=True)
    assert result.returncode != 0
