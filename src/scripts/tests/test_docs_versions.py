"""docs-versions.py (ADR 0011): release lines only, and the root 404.html redirects."""

import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("docs_versions", SCRIPTS / "docs-versions.py")
dv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dv)

BASE = "/clinvar-gkm/"


def pages_with(tmp_path, *folders):
    for f in folders:
        (tmp_path / f).mkdir()
    return tmp_path


def test_highest_release_line_is_latest(tmp_path):
    pages = pages_with(tmp_path, "1.1", "1.2")
    versions = dv.update_versions([], ["1.1", "1.2"], pages)
    assert [v["version"] for v in versions] == ["1.2", "1.1"]
    assert versions[0]["aliases"] == ["latest"] and versions[1]["aliases"] == []


def test_add_dev_is_rejected(tmp_path):
    pages = pages_with(tmp_path, "dev")
    with pytest.raises(SystemExit):
        dv.update_versions([], ["dev"], pages)


def test_existing_dev_entry_is_dropped_and_its_folder_removed(tmp_path):
    pages = pages_with(tmp_path, "1.1", "1.2", "dev")
    existing = [
        {"version": "1.2", "title": "1.2", "aliases": ["latest"]},
        {"version": "1.1", "title": "1.1", "aliases": []},
        {"version": "dev", "title": "dev (unreleased)", "aliases": []},
    ]
    versions = dv.update_versions(existing, ["1.2"], pages)
    assert [v["version"] for v in versions] == ["1.2", "1.1"]
    dv.write_root(pages, versions, BASE)
    dv.prune(pages, versions)
    assert not (pages / "dev").exists()
    assert (pages / "1.1").is_dir() and (pages / "1.2").is_dir()
    written = json.loads((pages / "versions.json").read_text())
    assert [v["version"] for v in written] == ["1.2", "1.1"]


# --- the 404.html redirect script, run in node with a fake location and fetch ---------------

HARNESS = """
const script = %(script)s;
const cases = %(cases)s;
(async () => {
  const out = [];
  for (const c of cases) {
    let target = null;
    const location = { pathname: c.path, search: "", hash: "", replace: (u) => { target = u; } };
    const fetch = (u) => Promise.resolve({ ok: c.exists.indexOf(u) >= 0 });
    new Function("location", "fetch", script)(location, fetch);
    await new Promise((r) => setTimeout(r, 0));
    out.push(target);
  }
  console.log(JSON.stringify(out));
})();
"""


def _not_found_script(pages, base):
    (pages / "1.1").mkdir()
    (pages / "1.2").mkdir()
    versions = dv.update_versions([], ["1.1", "1.2"], pages)
    dv.write_root(pages, versions, base)
    html = (pages / "404.html").read_text()
    return re.search(r"<script>(.*?)</script>", html, re.S).group(1)


def _run_404(script, path, exists):
    js = HARNESS % {
        "script": json.dumps(script),
        "cases": json.dumps([{"path": path, "exists": exists}]),
    }
    out = subprocess.run(["node", "-e", js], check=True, capture_output=True, text=True).stdout
    return json.loads(out)


@pytest.fixture(scope="module")
def not_found_script(tmp_path_factory):
    return _not_found_script(tmp_path_factory.mktemp("pages"), BASE)


@pytest.fixture(scope="module")
def not_found_script_at_root(tmp_path_factory):
    return _not_found_script(tmp_path_factory.mktemp("pages_root"), "/")


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
@pytest.mark.parametrize(
    "path, exists, expected",
    [
        # links to the retired dev docs (an announcement email links these)
        ("/clinvar-gkm/dev/parquet/migrating-from-1.1/", ["/clinvar-gkm/1.2/parquet/migrating-from-1.1/"],
         "/clinvar-gkm/1.2/parquet/migrating-from-1.1/"),
        ("/clinvar-gkm/dev/parquet/build-your-own/", ["/clinvar-gkm/1.2/parquet/build-your-own/"],
         "/clinvar-gkm/1.2/parquet/build-your-own/"),
        ("/clinvar-gkm/dev/no-such-page/", [], "/clinvar-gkm/1.2/"),
        ("/clinvar-gkm/dev/", ["/clinvar-gkm/1.2/"], "/clinvar-gkm/1.2/"),
        ("/clinvar-gkm/dev", ["/clinvar-gkm/1.2/"], "/clinvar-gkm/1.2/"),
        # unchanged behaviour
        ("/clinvar-gkm/reference/changelog/", ["/clinvar-gkm/1.2/reference/changelog/"],
         "/clinvar-gkm/1.2/reference/changelog/"),
        ("/clinvar-gkm/latest/reference/", [], "/clinvar-gkm/1.2/reference/"),
        ("/clinvar-gkm/1.1/no-such-page/", [], "/clinvar-gkm/1.1/"),
    ],
)
def test_404_redirects(not_found_script, path, exists, expected):
    assert _run_404(not_found_script, path, exists) == [expected]


# The site at the root of clinvar-gkm.org (ADR 0013): links that still carry the former /clinvar-gkm/ prefix
# drop it (the 404 page then runs again on the new path if that page is missing too).
@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
@pytest.mark.parametrize(
    "path, exists, expected",
    [
        ("/clinvar-gkm/1.2/data-access/download/", [], "/1.2/data-access/download/"),
        ("/clinvar-gkm/reference/changelog/", [], "/reference/changelog/"),
        ("/clinvar-gkm/dev/parquet/migrating-from-1.1/", [], "/dev/parquet/migrating-from-1.1/"),
        ("/clinvar-gkm/", [], "/"),
        ("/clinvar-gkm", [], "/"),
        # the second pass, on the path without the prefix
        ("/reference/changelog/", ["/1.2/reference/changelog/"], "/1.2/reference/changelog/"),
        ("/dev/parquet/migrating-from-1.1/", ["/1.2/parquet/migrating-from-1.1/"],
         "/1.2/parquet/migrating-from-1.1/"),
        ("/latest/reference/", [], "/1.2/reference/"),
        ("/1.1/no-such-page/", [], "/1.1/"),
        ("/no-such-page/", [], "/1.2/"),
        # a path that only starts with the same letters is not the former prefix
        ("/clinvar-gkmx/", [], "/1.2/"),
    ],
)
def test_404_redirects_at_root(not_found_script_at_root, path, exists, expected):
    assert _run_404(not_found_script_at_root, path, exists) == [expected]


def test_former_prefix_only_at_root(tmp_path):
    pages = pages_with(tmp_path, "1.2")
    dv.write_root(pages, dv.update_versions([], ["1.2"], pages), BASE)
    assert "FORMER = null" in (pages / "404.html").read_text()
