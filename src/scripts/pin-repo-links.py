#!/usr/bin/env python3
"""Point the docs' links to this repository's files at the ref a docs version was built from.

Pages link repository files as `https://github.com/clingen-data-model/clinvar-gkm/blob/main/<path>`
(also `/tree/main/...` and `/raw/main/...`). In a versioned build (ADR 0011) a release's pages
should show that release's files, so build-versioned-docs.sh runs this on the exported source
tree of a release version (never on the tag itself) to rewrite `main` to the release ref.

A link is rewritten only when its path exists at the ref; a link to a path the ref doesn't
have stays on `main` and is listed. Links to issues, pulls, discussions, releases and other
repositories are not touched.

Usage:
    python src/scripts/pin-repo-links.py DOCS_DIR REF [--repo REPO_DIR]

Prints how many links were rewritten and every link left on main. Stdlib only.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

LINK = re.compile(
    r"(https://github\.com/clingen-data-model/clinvar-gk[ms])/(blob|tree|raw)/main"
    r"(/[^\s)\"'#?<>`\]]*)?"
)
TEXT_SUFFIXES = {".md", ".html", ".htm", ".js", ".css", ".json", ".jsonc", ".svg", ".txt", ".yml", ".yaml", ".toml"}


def paths_at(repo, ref):
    commit = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", f"{ref}^{{commit}}"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    files = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "-r", "--name-only", commit],
        check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    known = set(files)
    for f in files:
        parts = f.split("/")
        for i in range(1, len(parts)):
            known.add("/".join(parts[:i]))
    known.add("")
    return known


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("docs", type=Path, help="exported docs/ directory to rewrite in place")
    ap.add_argument("ref", help="git ref the version was built from, e.g. 1.1.0")
    ap.add_argument("--repo", type=Path, default=Path("."), help="git repository holding the ref")
    args = ap.parse_args()

    known = paths_at(args.repo, args.ref)
    rewritten, left, files_changed = 0, [], 0

    def sub(m):
        nonlocal rewritten
        path = unquote(m.group(3) or "").strip("/")
        if path in known:
            rewritten += 1
            return f"{m.group(1)}/{m.group(2)}/{args.ref}{m.group(3) or ''}"
        left.append(m.group(0))
        return m.group(0)

    for f in sorted(args.docs.rglob("*")):
        if not f.is_file() or f.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = LINK.sub(sub, text)
        if new != text:
            f.write_text(new, encoding="utf-8")
            files_changed += 1

    print(f"pin-repo-links: {rewritten} links in {files_changed} files now point at {args.ref}")
    if left:
        print(f"pin-repo-links: {len(left)} links left on main (path not at {args.ref}):")
        for link in sorted(set(left)):
            print(f"  {link}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
