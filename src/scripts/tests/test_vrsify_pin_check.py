"""vrsify.sh must stop unless the installed resolver is the commit pinned in requirements.txt.

Each test runs the real script against a throwaway venv holding a fake clinvar-gk-pilot. The fake writes no
output, so a run that passes the check stops at "expected resolver output not found", before any gcloud call.
"""

import json
import os
import re
import stat
import subprocess
import venv
from pathlib import Path

import pytest

VRSIFY = Path(__file__).resolve().parents[2] / "vrsify"
PINNED = re.search(
    r"^clinvar_gk_pilot @ .*@([0-9a-f]+)$", (VRSIFY / "requirements.txt").read_text(), re.M
).group(1)
OLD = "224f87d13cb77aaa05fd671e1c3b486821df6f2f"
PASSED_CHECK = "expected resolver output not found"
STOPPED = "resolver does not match the pin"


@pytest.fixture
def env_dir(tmp_path):
    root = tmp_path / "env"
    venv.create(root, with_pip=False)
    pilot = root / "bin" / "clinvar-gk-pilot"
    pilot.write_text("#!/bin/sh\necho fake resolver ran\n")
    pilot.chmod(pilot.stat().st_mode | stat.S_IEXEC)
    return root


def install(root, commit=None):
    """Give the venv a clinvar-gk-pilot distribution, recording `commit` the way pip records a git install."""
    site = next((root / "lib").glob("python*/site-packages"))
    info = site / "clinvar_gk_pilot-0.0.0.dist-info"
    info.mkdir()
    (info / "METADATA").write_text("Metadata-Version: 2.1\nName: clinvar-gk-pilot\nVersion: 0.0.0\n")
    if commit:
        (info / "direct_url.json").write_text(
            json.dumps({"url": "https://example.test/r", "vcs_info": {"vcs": "git", "commit_id": commit}})
        )


def run(tmp_path, path, **env):
    result = subprocess.run(
        [str(VRSIFY / "vrsify.sh"), "2026-01-01"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={
            "HOME": os.environ.get("HOME", ""),
            "PATH": path,
            "SEQREPO_ROOT_DIR": "x",
            "SEQREPO_DATAPROXY_URL": "x",
            "HGVS_SEQREPO_DIR": "x",
            "GENE_NORM_DB_URL": "x",
            **env,
        },
    )
    return result.returncode, result.stdout + result.stderr


def on_path(root):
    return f"{root}/bin:/usr/bin:/bin"


def test_pinned_commit_passes(tmp_path, env_dir):
    install(env_dir, PINNED)
    code, out = run(tmp_path, on_path(env_dir))
    assert "fake resolver ran" in out
    assert PASSED_CHECK in out and STOPPED not in out


def test_old_commit_stops_before_the_resolver_runs(tmp_path, env_dir):
    install(env_dir, OLD)
    code, out = run(tmp_path, on_path(env_dir))
    assert code == 1 and STOPPED in out
    assert PINNED in out and OLD in out
    assert "--force-reinstall --no-deps" in out
    assert "fake resolver ran" not in out


def test_install_without_a_recorded_commit_stops(tmp_path, env_dir):
    install(env_dir)
    code, out = run(tmp_path, on_path(env_dir))
    assert code == 1 and STOPPED in out and "unknown" in out


def test_resolver_not_on_path_stops(tmp_path):
    code, out = run(tmp_path, "/usr/bin:/bin")
    assert code == 1 and STOPPED in out and "not on PATH" in out


def test_custom_command_is_not_checked(tmp_path, env_dir):
    install(env_dir, OLD)
    code, out = run(tmp_path, on_path(env_dir), VRSIFY_CMD="echo custom-resolver")
    assert "custom-resolver" in out
    assert PASSED_CHECK in out and STOPPED not in out
