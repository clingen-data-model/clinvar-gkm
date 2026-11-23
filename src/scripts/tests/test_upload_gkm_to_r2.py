"""upload-gkm-to-r2.sh must finish a real weekly upload under /bin/bash (3.2 on macOS) and never exit 0 when it aborts."""

import shutil
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "upload-gkm-to-r2.sh"

# The R2 helpers the script sources, as stubs that only log. BREAK makes r2_put_sidecar expand an unset variable, so
# `set -u` aborts the script in its main shell, the way the empty INDEX_ARGS expansion did.
R2_COMMON = """
R2_PUBLIC_URL=https://example.invalid
log() { echo "$*" >> "${CALLS}"; }
r2_listing() { : > "$2"; log "r2_listing $1"; }
r2_layout() { echo 2026-11; }
r2_put() { log "r2_put $2"; }
r2_put_sidecar() { log "r2_put_sidecar $2${BREAK:+ ${UNSET_IN_TEST}}"; }
r2_copy() { log "r2_copy $1 $2"; }
r2_cat() { :; }
r2_size() { :; }
cf_purge() { log "cf_purge $*"; }
"""


def run(tmp_path, **env):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy(SCRIPT, scripts / SCRIPT.name)
    (scripts / "r2-common.sh").write_text(R2_COMMON)
    index = scripts / "generate-r2-index.sh"
    index.write_text('#!/bin/bash\necho "generate-r2-index.sh $*" >> "${CALLS}"\n')
    index.chmod(0o755)
    bundle = tmp_path / "clinvar-gkm-2026-11-15.json.gz"
    bundle.write_bytes(b"bundle")
    calls = tmp_path / "calls"
    result = subprocess.run(
        ["/bin/bash", scripts / SCRIPT.name, "2026-11-15", "v2_7_1", bundle, "--weekly"],
        capture_output=True, text=True,
        env={"PATH": "/usr/bin:/bin", "CALLS": str(calls), "R2_LINE": "v1/1.2/", **env},
    )
    return result, calls.read_text().splitlines() if calls.exists() else []


def test_weekly_upload_regenerates_the_index(tmp_path):
    result, calls = run(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "unbound variable" not in result.stderr
    assert "generate-r2-index.sh " in calls
    assert "r2_put v1/1.2/weekly/clinvar-gkm_2026-1115.json.gz" in calls
    assert "FULL upload complete" in result.stdout


def test_an_abort_is_never_exit_0(tmp_path):
    result, calls = run(tmp_path, BREAK="1")
    assert "unbound variable" in result.stderr
    assert result.returncode != 0
    assert not any(c.startswith("generate-r2-index.sh") for c in calls)
    assert "FULL upload complete" not in result.stdout


def test_upload_always_purges_the_dated_files_it_writes(tmp_path):
    # Without --purge: a new dated path may hold a CDN-cached 404 from a request made before it existed.
    result, calls = run(tmp_path)
    assert result.returncode == 0, result.stderr
    assert ("cf_purge files v1/1.2/weekly/clinvar-gkm_2026-1115.json.gz"
            " v1/1.2/weekly/clinvar-gkm_2026-1115.json.gz.sha256") in calls
