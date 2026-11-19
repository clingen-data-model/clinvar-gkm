# 0011 — Versioned documentation

- **Status:** Proposed
- **Date:** 2026-11-19
- **Amends:** [ADR 0003](0003-roadmap-from-labeled-discussions.md) (which docs builds regenerate the Roadmap)

## Context

The docs site was one build. Every docs merge to `main` overwrote the whole `gh-pages` branch, so the live site
described `main`: the 1.2.0 profiles were documented before 1.2.0 was released, and a reader of the 1.1.0 data
had no way to see the docs that matched it. A release deploy showed the tag's docs only until the next `main`
run. Data lines already have folders (`v1/1.1/`, `v1/1.2/`, ADR 0009); the docs had nothing to match.

The maintainer set five requirements (2026-11-19), to be in place with the 1.1.0 docs before 1.2.0 ships:
one docs version per minor line; the site root and the default are the latest release; `main` is still
published, as `dev`, with its own colour and notice; existing unversioned links keep working; older releases are
grey and say they aren't current.

## Decision

1. **One docs version per release line**, `1.1`, `1.2`, … — the same `{major}.{minor}` as the data line folder.
   A patch release (`1.2.1`) rebuilds its line's docs in place; patches never get their own version. The line's
   docs are built from its newest tag.
2. **`dev` is `main`**, rebuilt on every docs merge, as today. It is never the default.
3. **Layout on `gh-pages`.** One folder per version (`1.1/`, `dev/`), each a complete Zensical build with
   `site_url` set to `…/clinvar-gkm/<version>/`, so canonical links and `sitemap.xml` are per version. At the
   root, written by `src/scripts/docs-versions.py`:
    - `versions.json` (the format `mike` writes) lists the versions. The **highest release line** carries the
      alias `latest`, so a patch to an older line can't take `latest` from a newer one, and `dev` never has it.
    - `index.html` redirects to the latest release, keeping the query and `#fragment`.
    - `404.html` is what GitHub Pages serves for any missing path. An unversioned link — every URL from before
      this change — goes to the same page in the latest release, or to its home when that page doesn't exist
      there. `…/latest/<page>` goes to that page in the latest release. A missing page inside a version goes to
      that version's home.
    - Anything else at the root is removed on every deploy (the first deploy removes the unversioned site);
      `CNAME` and `.nojekyll` are kept.
4. **The version selector is the theme's.** `[project.extra.version] provider = "mike"` makes Zensical render the
   Material version selector from `versions.json`; switching versions keeps the reader on the same page when it
   exists in the other version. The `mike` tool itself isn't used: the workflow builds each version with
   `zensical build` and writes `versions.json` itself.
5. **Old / dev / latest is decided in the browser.** `docs/assets/js/versions.js` reads `versions.json` on every
   page and compares the page's version to the `latest` alias. On `dev` it colours the header and tabs orange and
   shows a notice that the pages describe unreleased changes and aren't for production use; on an older release
   it colours them grey and shows a notice that this isn't the current version. Both notices link to the same
   page in the latest release, or its home. The latest release keeps the normal indigo. Nothing is baked into a
   build, so an older version turns grey on its own when a newer release ships, without being rebuilt. The
   result is cached for the browser tab so the next page doesn't flash indigo first.
6. **Older tags get the feature by overlay.** `src/scripts/build-versioned-docs.sh <ref> <version> <out>` exports
   the ref's tree (the tag is never changed), copies in the files this feature owns (`docs/overrides/main.html`,
   `partials/header.html`, `partials/source.html`, `404.html`, `versions.js`, `versions.css`) from the checkout
   running the build, sets `site_url`, adds the `[project.extra.version]` table if missing, regenerates the
   Roadmap, and runs `zensical build --clean --strict` and `check-site-links.py`. This is how `1.1` is built from
   the `1.1.0` tag, whose config predates versioning. Content a tag's docs should have but don't is added by a
   patch in `src/scripts/docs-ref-patches/<tag>/`, applied to the exported tree before the build (a patch that
   doesn't apply stops it): the `1.1.0` tag's changelog has no 1.1.0 section, because the notes were written
   after the tag, so `1.1.0/changelog-1.1.0-section.patch` adds that section as it reads on `main`.
7. **Each version shows and links its own ref.** The build sets `[project.extra.source]` to the ref it was built
   from: `main` (labelled with the build commit) for `dev`, the tag for a release. The header's repository widget
   (`partials/source.html`) shows that ref and links `…/tree/<ref>`, instead of the latest GitHub release the theme
   fetches from the GitHub API; the stars and forks counts, which come from the same lookup, are dropped.
   `edit_uri` follows the ref (`edit/main/docs/` for `dev`, `blob/<tag>/docs/` for a release, since a tag can't
   be edited); the edit and view buttons aren't enabled today. For a release, `src/scripts/pin-repo-links.py`
   rewrites the pages' links to this repository's files on `main` (`/blob/main/…`, `/tree/main/…`,
   `/raw/main/…`) in the exported tree to the tag, so a `1.1` page links the `1.1.0` files; a path the tag
   doesn't have stays on `main` and is listed in the build log. Links to issues, discussions, pull requests and
   releases stay as written: they are live, not versioned.
8. **When each version is deployed** (`.github/workflows/deploy-docs.yml`):

    | Trigger | Builds |
    | --- | --- |
    | `push` to `main` touching the docs paths | `dev` |
    | `release: published` for tag `X.Y.Z` (not a prerelease) | `X.Y` from the tag; `versions.json` and `latest` updated |
    | daily `schedule` and `discussion` events | `dev`, and the latest release from its newest tag |
    | `workflow_dispatch`, no inputs (on `main`) | `dev` |
    | `workflow_dispatch` with `ref` and `version` | that ref as that version, e.g. `1.1.0` as `1.1` |

    The latest release is rebuilt on the Roadmap triggers because the Roadmap is a live page (ADR 0003) and the
    latest release is the version most readers see. Older releases keep the Roadmap they had.
9. **Publishing keeps the other versions.** A run builds only its versions, then checks out `gh-pages`, replaces
   those folders, rewrites the root files and pushes; if another run pushed first, it starts again from the new
   tip. Runs are serialized per version (`concurrency: deploy-docs-<version>`), so a main merge can't cancel a
   release deploy.

## Consequences

- Readers land on the docs for the data they can download today; unreleased changes are visible but marked.
  Every existing link and bookmark keeps working through the redirect.
- A new release needs no docs step: publishing the GitHub release for `X.Y.0` builds `X.Y`, makes it `latest`, and
  turns the previous line grey.
- **The `release` event runs the workflow file at the tag.** A tag whose tree has the old whole-site
  `deploy-docs.yml` would overwrite every version with one unversioned build. Before publishing a release from
  a branch that predates this ADR — the `1.0` branch today — bring this workflow and its scripts
  (`build-versioned-docs.sh`, `docs-versions.py`, `pin-repo-links.py`) onto that branch, or remove its `release`
  trigger.
- The overlay files must keep building against the oldest published docs version. A change to them is checked
  by building `1.1` from its tag (`build-versioned-docs.sh 1.1.0 1.1 <out>`).
- Search is per version; results come from the version being read.
- `gh-pages` gains one commit per deploy, as before.
- One-time bootstrap after merge: the merge's own deploy publishes `dev` and removes the unversioned site (the
  root redirects to `dev` until a release exists); then dispatch the workflow with `ref = 1.1.0`,
  `version = 1.1` to publish `1.1` as `latest`.
