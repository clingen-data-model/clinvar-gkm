# 0013 — Serve the documentation at clinvar-gkm.org

- **Status:** Accepted
- **Date:** 2026-11-24
- **Decided:** 2026-11-24 (maintainer; the owner of `dataexchange.clinicalgenome.org` agreed)

## Context

The project owns `clinvar-gkm.org` (ADR 0005). Its `data.` host serves the bundles and Parquet from R2, and the
bare domain was left free for a future landing page. Today the bare domain only redirects, so a reader who types
it never sees it in the address bar:

```text
https://clinvar-gkm.org/                                 301  Cloudflare redirect rule (zone clinvar-gkm.org)
→ https://clingen-data-model.github.io/clinvar-gkm/       301  GitHub Pages: the repo has no custom domain, so it
                                                               lives under the org site's domain
→ https://dataexchange.clinicalgenome.org/clinvar-gkm/    200  index.html (docs-versions.py) sends the reader on
→ https://dataexchange.clinicalgenome.org/clinvar-gkm/1.2/
```

The redirect rule was set in the Cloudflare dashboard; nothing in this repository records it. The docs are a
GitHub Pages project site of `clingen-data-model/clinvar-gkm` (branch `gh-pages`, versioned per ADR 0011). The
organization's user site has the custom domain `dataexchange.clinicalgenome.org`, so every project site in the
organization is served under it at `/<repo>/`.

A URL in the address bar can only stay on `clinvar-gkm.org` if that host serves the pages. A redirect always
shows its target.

## Decision

1. **`clinvar-gkm.org` is the docs site's own domain.** It is set as the GitHub Pages custom domain of
   `clingen-data-model/clinvar-gkm`. The site moves from the path `/clinvar-gkm/` to the root of the domain:
   `https://clinvar-gkm.org/1.2/…`. `site_url` in `zensical.toml` becomes `https://clinvar-gkm.org/`.
2. **Old URLs keep working through redirects.** With a custom domain set, GitHub Pages redirects the project's
   old addresses (checked at the cutover, Phase 2 step 6), `dataexchange.clinicalgenome.org/clinvar-gkm/…` and `clingen-data-model.github.io/clinvar-gkm/…`,
   to the same path on `clinvar-gkm.org`. Links already sent out (announcement emails, the R2 `README`, the
   `data_use` link in published `index.json` files, CITATION.cff in released tags, papers and slides) need no
   change. As a fallback, the root `404.html` also sends a path that still starts with `/clinvar-gkm/` to the
   same page without that prefix.
3. **DNS is served by Cloudflare, but not proxied.** The bare domain gets GitHub Pages' A and AAAA records and
   `www` a CNAME to `clingen-data-model.github.io`, all **DNS only** (grey cloud), so GitHub can issue and renew
   the HTTPS certificate. The domain is verified for the `clingen-data-model` organization (a
   `_github-pages-challenge-clingen-data-model` TXT record), so no other GitHub account can claim it. The
   Cloudflare redirect rule is deleted. `data.clinvar-gkm.org` (R2 behind the CDN, ADR 0005) and the mail records
   (Email Routing MX and SPF, Resend DKIM, ADR 0010) are not changed.
4. **The docs no longer assume the `/clinvar-gkm/` path.** Code that finds the docs version in the page URL
   (the release browser `r2-browser.js` and the live console `duckdb-console.html`) accepts the version as the
   first path segment, with or without a `/clinvar-gkm/` prefix. Both are overlay files (ADR 0011), so every
   version, including frozen 1.1, gets the change on its next build. `versions.js`, `docs-versions.py` and
   `check-site-links.py` already read the base path from `site_url` and need no change.
5. **The owner of `dataexchange.clinicalgenome.org` (ClinGen) agreed** to the docs leaving that domain
   (2026-11-24).

## Plan

### Phase 1: make the site path-independent (one PR into `1.0`, forward-merged to `main`; #291)

This is safe to merge before the move: with the site still at `/clinvar-gkm/`, nothing changes for readers.

1. `docs/assets/js/r2-browser.js` and `docs/assets/duckdb-console.html`: `docsVersion()` and
   `latestDocsHref()` match the version as the first path segment, `^/(?:clinvar-gkm/)?(\d+\.\d+)(?:/|$)`.
   `LATEST_DOCS` is derived from the page's own URL (the path before the version segment), not a hard-coded
   `dataexchange` URL.
2. `src/scripts/docs-versions.py`: in the generated `404.html`, when the base path is `/`, strip a leading
   `/clinvar-gkm/` before the existing version lookup. Add cases for base path `/` to
   `src/scripts/tests/test_docs_versions.py`.
3. Build both ways and check: `build-versioned-docs.sh HEAD 1.2` with the current `site_url`, and with
   `site_url = "https://clinvar-gkm.org/"`. In both, `check-site-links.py` reports 0 broken links, and the console
   and release browser show the 1.2 line when the built site is served locally.

### Phase 2: cutover (one sitting, about an hour; steps 1, 2 and 4 are dashboard work by an admin)

1. **GitHub → organization `clingen-data-model` → Settings → Pages → Verified domains:** add
   `clinvar-gkm.org` and create the TXT record it asks for in Cloudflare. Wait until it shows as verified.
2. **Cloudflare → zone `clinvar-gkm.org`:**
    - Rules: delete the redirect rule for the bare domain.
    - DNS: replace the bare domain's proxied records with four **DNS-only** A records (`185.199.108.153`,
      `185.199.109.153`, `185.199.110.153`, `185.199.111.153`) and four AAAA records
      (`2606:50c0:8000::153`, `2606:50c0:8001::153`, `2606:50c0:8002::153`, `2606:50c0:8003::153`). Add
      `www` as a **DNS-only** CNAME to `clingen-data-model.github.io`.
    - Leave the `data` record, the MX and SPF records, and the Resend DKIM records as they are.
3. **PR into `1.0`, forward-merged to `main`:** `site_url = "https://clinvar-gkm.org/"` in `zensical.toml`.
   `build-versioned-docs.sh` reads `site_url` from the checkout that runs the deploy (`main`), so no
   `docs-line-sources.txt` change is needed and frozen 1.1 needs no branch change.
4. **GitHub → repo `clingen-data-model/clinvar-gkm` → Settings → Pages:** set the custom domain to
   `clinvar-gkm.org`. GitHub writes a `CNAME` file on `gh-pages`; `docs-versions.py` keeps it on every deploy
   (ADR 0011). Wait for the certificate, then turn on **Enforce HTTPS**.
5. **Rebuild both versions:** dispatch `deploy-docs.yml` with no inputs (1.2) and with
   `-f ref=1.1.0 -f version=1.1`. Each run rewrites the root `index.html`, `404.html` and `versions.json` for the
   new base path.
6. **Verify:**
    - `https://clinvar-gkm.org/` opens `https://clinvar-gkm.org/1.2/` and the address bar stays on
      `clinvar-gkm.org`; `https://www.clinvar-gkm.org/` and `http://clinvar-gkm.org/` end there too.
    - `https://dataexchange.clinicalgenome.org/clinvar-gkm/1.2/data-access/download/` and
      `https://clingen-data-model.github.io/clinvar-gkm/1.1/` redirect to the same page on `clinvar-gkm.org`.
    - An old unversioned link, `…/clinvar-gkm/reference/changelog/`, ends on `/1.2/reference/changelog/`.
    - The version selector switches between 1.2 and 1.1 on the same page.
    - The release browser and the console show each version's own line, and a console query runs.
    - The certificate is valid, and both deploy logs show `check-site-links.py` with 0 broken links.
    - `data.clinvar-gkm.org/index.json` still loads (the data host is untouched).
7. **Rollback**, if a check fails: remove the custom domain in the repo's Pages settings, revert the `site_url`
   PR, dispatch both versions again, and restore the Cloudflare redirect rule. The data host is never involved.

### Phase 3: update links that name the old address (one PR, any time after the cutover)

They all keep working through redirects, so this is tidying, not a fix:

- `README.md` (3 links), `CITATION.cff` (`url`), and the docs pages with absolute links: `parquet/previous-releases.md`,
  `parquet/build-your-own.md`, `start/what-you-can-do.md`, `reference/versioning.md`,
  `data-access/weekly-deltas.md`, `data-access/keep-current.md`, `build/track-change.md`.
- `docs/assets/presentations/clinvar-gkm-primer.html` and `clinvar-gkm-unlocks.html` (about 35 links),
  `docs/assets/scripts/keep-current.py` and `track-history.py` (docstrings), and the comment in
  `docs/assets/column-sets/clinvar-gkm-1.1.0.columns.yaml`.
- Release tooling that writes the docs address into published files: `src/scripts/announce_monthly.py`
  (`DOCS`), `src/scripts/r2_layout.py` (`data_use` and the changelog line), `src/scripts/r2-readme.txt` and
  `src/scripts/republish-v1.sh`. Files already on R2 are immutable (ADR 0008) and keep the old address, which
  redirects. New files carry the new one from the next release.
- Contributor notes: `.claude/rules/docs.md` and `.claude/skills/write-docs/SKILL.md` (the `/clinvar-gkm/`
  prefix), and the examples in the docstrings of `check-site-links.py` and `docs-versions.py`.
- Upstream: the ClinVar-GKM link in GA4GH `va-spec` (`docs/source/appendices/implementations.rst`), by PR to
  that repository.
- ADR 0005: note that the bare domain now serves the docs.

## Consequences

- Readers see and share one short address the project controls, for both the docs (`clinvar-gkm.org`) and the
  data (`data.clinvar-gkm.org`).
- The docs no longer depend on how the organization's user site is configured.
- The docs leave the `clinicalgenome.org` domain, with ClinGen's agreement (Decision 5).
- The docs are not behind Cloudflare's CDN: GitHub Pages serves them over its own CDN, which is free, so there is
  no fee exposure to protect (unlike R2, ADR 0005). Proxying through Cloudflare would block GitHub's certificate.
- The domain's renewal (Cloudflare Registrar, auto-renew) now matters for the docs as well as the data.
- Old links rely on GitHub's redirect for project sites with a custom domain. Step 6 checks it, and the
  `404.html` fallback covers a path that arrives with the old prefix.
- Search engines see 301s and move their index to the new address; for a while results may show both.
