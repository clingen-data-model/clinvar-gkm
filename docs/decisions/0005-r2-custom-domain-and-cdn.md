# 0005 — R2 distribution domain, CDN caching, and fee protection

- **Status:** Accepted
- **Date:** 2026-10-13
- **Spec (if any):** —
- **Amended:** 2026-10-20 by [ADR 0009](0009-r2-layout-mirrors-ncbi-clinvar.md): the published paths changed;
  see [Layout change (ADR 0009)](#layout-change-adr-0009).
- **Amended:** 2026-10-21: the [Layout change (ADR 0009)](#layout-change-adr-0009) notes now match the rules in
  `src/scripts/cf-rules.sh` on `1.0` (PR #182): `weekly/` and `README.txt` bypass the cache, and weekly fulls
  are not cached as immutable.

## Context

Public distribution originally pointed consumers at the R2 **development** URL
`https://pub-f0ad0e0dac0345408dcc95bda20beb42.r2.dev`. That endpoint is explicitly dev-only:
Cloudflare rate-limits it (429s under load), throttles bandwidth, and supports **no** CDN caching,
WAF, or rate-limiting rules. We needed a stable, production-grade hostname that consumers can hardcode
long-term, with cache/abuse controls in front of the bucket.

Constraints that shaped the choice:

- **`clinicalgenome.org` is not usable as the host.** Its authoritative DNS is on **AWS Route 53**, and
  ClinGen has **no Cloudflare account**. R2 custom domains must live in a Cloudflare **zone**. The
  supported ways to attach a Cloudflare-served hostname to an externally-hosted parent domain are all
  gated: full setup (move the whole org domain to Cloudflare — not our call), **Partial/CNAME setup**
  (Cloudflare **Business** plan), or **Subdomain setup** (Cloudflare **Enterprise**). None were viable.
- A generic `downloads.clinicalgenome.org` / `data.clinicalgenome.org` would wrongly imply an org-wide
  ClinGen download hub; `clinicalgenome.org` hosts many independent data sources.
- R2's defining property is **$0 egress** — so "download bandwidth" is never a cost. The only
  download-driven cost is Class B (read) operations, which are cheap and collapse to near-zero behind a
  CDN cache.

## Decision

1. **Dedicated domain.** Registered **`clinvar-gkm.org`** via **Cloudflare Registrar** (~$10/yr), which
   creates it as its own **free Cloudflare zone** — no dependency on ClinGen's Route 53 or any admin.
2. **Public host = `data.clinvar-gkm.org`**, attached to the `clinvar-gkm` R2 bucket via **R2 → Connect
   Domain** (auto-creates a proxied record + TLS). `data` (not `downloads`) because consumers also
   **range-read** the Parquet in place (DuckDB/`httpfs`), which isn't a "download". The apex is left free
   for a future landing page.
3. **Scripts default to the custom host, env-overridable.** All uploaders + the index generator set
   `R2_PUBLIC_URL="${R2_PUBLIC_URL:-https://data.clinvar-gkm.org}"`. `generate-r2-index.sh` writes this as
   the `base_url` in `index.json` / the root manifest / `feed.xml` — the canonical consumer URL.
4. **Fee protection is CDN-side** (Cache Rules + one rate-limit rule), plus an optional **`--purge`** path
   in the uploaders for the rare in-place overwrite.

The `pub-…r2.dev` dev URL still resolves (same bucket) and can be disabled in the dashboard once all
consumers have migrated.

## Consequences

Easy: a stable branded URL, free egress, near-zero op costs behind caching, full WAF/cache control.
Harder / must-know for future administrators — the runbook below.

### Key identifiers

| Thing | Value |
|---|---|
| Cloudflare account (R2) | `09208aa33790838db213a21f630c33e7` |
| R2 bucket | `clinvar-gkm` |
| S3 endpoint (writes) | `https://09208aa33790838db213a21f630c33e7.r2.cloudflarestorage.com` (`--profile r2`) |
| Public host (reads) | `https://data.clinvar-gkm.org` (zone `clinvar-gkm.org`) |
| Dev URL (legacy) | `https://pub-f0ad0e0dac0345408dcc95bda20beb42.r2.dev` (still works; retire later) |

### Reproducing the setup (if the domain/zone ever has to be rebuilt)

1. **Register / add the zone:** `clinvar-gkm.org` via Cloudflare Registrar (or add any domain you own and
   point its nameservers at Cloudflare — full setup, free). Must be in the **same** Cloudflare account as
   the bucket.
2. **Connect the bucket:** R2 → `clinvar-gkm` → Settings → Custom Domains → **Connect Domain** →
   `data.clinvar-gkm.org`. Cloudflare creates the proxied record + provisions TLS. Wait for **Active**.
3. **Verify it's proxied** (Cache/WAF rules only act on proxied traffic):
   ```bash
   dig +short data.clinvar-gkm.org      # → Cloudflare anycast IPs (104.x / 172.67.x), not an origin IP
   curl -sI https://data.clinvar-gkm.org/v1/index.json | grep -iE 'server|cf-cache-status'
   #   → "server: cloudflare" + a "cf-cache-status:" header  ⇒ traffic is proxied, rules apply
   ```
   If a rule editor warns *"may not be proxying traffic for (http.host …)"*, this is the check to run —
   R2 custom domains are proxied by design, so once **Active** the warning is a false positive.

### Cache Rules (zone `clinvar-gkm.org` → Caching → Cache Rules)

Object layout splits into **write-once / immutable** vs **rewritten-every-release / mutable**. Note "latest"
appears both as a **directory** (`/00-latest/`) and inside a **filename** (`clinvar-gkm_00-latest.json.gz`), and
there are **two** index files plus a feed — the mutable matcher must catch all of them:

- Immutable (dated, never overwritten): `/v1/deltas/<YYYY-MMDD>/…`, `/v1/datasets/clinvar-gkm_<YYYY-MM>.json.gz`,
  `/v1/datasets/parquet/<YYYY-MM>/…`, `/v1/archives/…`.
- Mutable (rewritten every release): root `/index.json`, `/v1/index.json`, `/v1/feed.xml`,
  `/v1/datasets/clinvar-gkm_00-latest.json.gz`, and everything under any `/00-latest/` tree
  (`/v1/deltas/00-latest/…`, `/v1/datasets/parquet/00-latest/…`).

These are the paths before ADR 0009; the new paths are listed under
[Layout change (ADR 0009)](#layout-change-adr-0009).

Two rules; **last matching rule wins**, so keep the pointer rule *below* the immutable rule:

```
Rule 1 "R2 immutable artifacts"   (FIRST)
  When:  (http.host eq "data.clinvar-gkm.org")
  Then:  Eligible for cache; Edge TTL = Ignore cache-control, 1 month; Browser TTL = 1 day

Rule 2 "R2 mutable pointers"      (SECOND / last)
  When:  (http.host eq "data.clinvar-gkm.org") and (
           http.request.uri.path contains "00-latest"
           or http.request.uri.path contains "index.json"
           or http.request.uri.path contains "feed.xml" )
  Then:  Bypass cache
```

This collapses Class B cost (immutable files serve from edge, never hitting R2) while mutable pointers are
always fetched fresh. The long TTL is safe **only because dated artifacts are write-once** — see overwrite
gotcha below. Two Free-plan constraints shaped this:

- **Max cacheable object = 512 MB** (Free/Pro/Business; Enterprise 5 GB). The multi-GB JSON bundles therefore
  **never cache** — they always report `cf-cache-status: DYNAMIC` and stream straight from R2. That is fine:
  egress is $0 and it's one cheap Class B op per fetch. Caching's real win is the smaller/hot files
  (Parquet sections, manifests, index).
- **Minimum dashboard Edge TTL = 2 hours** on Free. You can't set a short TTL for the pointers that way, so
  Rule 2 uses **Bypass cache** (always fresh) instead of a 1-minute TTL. If brief pointer caching is ever
  wanted, stamp `Cache-Control: max-age=60` on those objects at upload and set Rule 2 Edge TTL to "use
  cache-control header if present" (origin TTLs aren't subject to the 2 h floor).

Verify with real **GET** requests (`curl -I`/HEAD reports `DYNAMIC` even when a GET caches):
```bash
u=https://data.clinvar-gkm.org/v1/deltas/<date>/manifest.json
curl -s -o /dev/null -D - "$u" | grep -i cf-cache-status   # run twice → MISS then HIT (immutable)
curl -s -o /dev/null -D - https://data.clinvar-gkm.org/v1/index.json | grep -i cf-cache-status  # DYNAMIC/BYPASS
```

### Rate-limiting rule (Security → WAF → Rate limiting rules; 1 free IP-keyed rule)

Live rule "R2 abuse backstop" (verified 2026-10-18):

```
When:  (http.host eq "data.clinvar-gkm.org")
Characteristics:  IP (ip.src)
Rate:  250 requests / 10 seconds
Then:  Block for 10 seconds
Order: first; Status: Active
```

The Free plan fixes the counting period and the block duration at **10 seconds**; only the request count is
adjustable. The original intent (300 requests / 1 minute, block 10 minutes) could not be expressed on Free and
was first configured as 50 / 10 s. That blocked ordinary DuckDB queries after ~55 range requests, so on
2026-10-18 the threshold was raised to **250 / 10 s**. A burst of 120 range requests in ~1 s now returns 206
throughout, and remote queries such as a `GROUP BY` over all of `scv.parquet` or a variant's PubMed ids
(an `scv` × `varcond-proposition` join) complete in 10–35 s.

Keep it **generous**: DuckDB/`httpfs` issues many range GETs per query, cached hits still count toward the
limiter, and a client that keeps retrying while blocked re-trips the rule. This is an anti-runaway backstop
only — real exposure is pennies (free egress + $0.36 / million Class B, 10M/month free).

### Costs (order of magnitude)

Storage $0.015/GB-mo (a few $/mo at current size); Class B $0.36/million reads with 10M/mo free;
**egress $0**. Caching + the write-once layout keep origin reads near-zero. There is **no native hard
spend cap**. An account-wide **budget alert at $10/month** is configured (Manage Account → Billing → Billable
Usage → budget alert; email only, it does not pause usage). R2-specific Usage Based Billing alerts
(Alerts → Overview → Add) may need a paid plan.

### Path allowlist rule (Security → WAF → Custom rules)

Added 2026-10-18, active:

```
Name:  PATH ALLOWLIST - block requests outside published data paths
When:  http.host eq "data.clinvar-gkm.org" and not (
         starts_with(path, "/v1/") or starts_with(path, "/archive/") or
         starts_with(path, "/.well-known/") or path in {"/" "/index.json"})
Then:  Block
```

Scanners probe hostnames for paths such as `/wp-config.php`, `/.git/config` and `/actuator/health` (about
1,600 such requests in the first four days). This rule blocks them at the edge with a 403, before they reach
R2, so they cost no Class B operations. Unlike Browser Integrity Check, which is **off** for this zone because
it rejected Python's default `urllib` user agent (HTTP 403, error 1010), it cannot be bypassed by faking a
header. Tested on 2026-10-18:
- index files, bundles, Parquet (including 206 range reads), the archive and CORS preflight are served;
- scanner paths, stray documentation-site paths and the retired flat-root `/datasets/…` return 403.

**When a new top-level path is published, add it to the rule.**

### Spend alert and kill switch

R2 has no hard spend cap and the budget alert only emails, so pausing is manual. What can grow the bill:
Class B reads that miss the cache (mostly range requests on files over 512 MB, which always go to R2), our
own writes (Class A) and storage. Egress is $0.

If the alert fires:

1. **Stop our own writes:** no `run-release.sh`, uploader or backfill runs.
2. **Find the cause:** R2 → clinvar-gkm → Metrics (which operation type jumped); clinvar-gkm.org →
   Security → Events / Analytics (top IPs, ASNs, paths). If it is one client or network, block only that
   with a WAF custom rule on `ip.src` or `ip.geoip.asnum`.
3. **Pause all public reads with one command:**
   ```bash
   ./src/scripts/cdn-kill-switch.sh on       # block every request to data.clinvar-gkm.org at the edge
   ./src/scripts/cdn-kill-switch.sh status   # rule state + a probe of /v1/index.json (403 = blocked)
   ./src/scripts/cdn-kill-switch.sh off      # restore service
   ```
   It flips one WAF custom rule ("KILL SWITCH - block all public data"); cached hits are blocked too, so
   nothing reaches R2. Nothing in R2 changes. It needs `CF_ZONE_ID` and `CF_WAF_TOKEN` in
   `~/.config/clinvar-gkm/cloudflare.env`; the token is scoped to zone `clinvar-gkm.org` with **Zone → Zone
   WAF → Edit** and **Zone → Firewall Services → Edit**. Run `init` once to pre-create the rule disabled.
   The dashboard equivalent is Security → WAF → Custom rules → toggle the rule.
4. **The `r2.dev` URL bypasses all of this.** The public development URL serves the same bucket with no
   cache, WAF or rate limit. Disable it (R2 → clinvar-gkm → Settings → Public Development URL); nothing in
   the repo uses it any more.
5. **Harder stop**, if needed: disconnect the custom domain (R2 → clinvar-gkm → Settings → Custom Domains).
   Reconnecting re-provisions TLS and takes a few minutes.

### Overwrite gotcha + the `--purge` flag

Within the 1-month immutable Edge TTL, Cloudflare serves cached bytes without revalidating against R2, and
the cache is **per-PoP**. So **overwriting an already-cached immutable file in place** (e.g. re-publishing a
release under the same date, or re-running a backfill over an existing month) serves **stale, inconsistent**
content for up to a month. Routine releases are safe — they write new dated keys, and the only paths they
overwrite (`index.json`, `00-latest/*`) are on the 1-minute rule and self-heal.

For the rare in-place overwrite, the uploaders take **`--purge`**, which purges the CDN cache for the
dated path(s) just written:

- `upload-gkm-delta-to-r2.sh … --purge` → purges `…/v1/deltas/<YYYY-MMDD>/`
- `upload-gkm-to-r2.sh … --purge` → purges the dated monthly + dated Parquet set
- `backfill-monthly-to-r2.sh … --purge` → purges `${DEST}` (+ dated Parquet)

`--purge` requires a **zone-scoped** Cloudflare API token with **Cache Purge** permission (the object-scoped
`r2` token cannot purge), plus the zone id:

```bash
export CF_ZONE_ID=<clinvar-gkm.org zone id>
export CF_PURGE_TOKEN=<zone-scoped token with Cache Purge>
./upload-gkm-delta-to-r2.sh 2026-07-06 delta.json.gz manifest.json --purge
```

Without `--purge` nothing changes (routine behavior). With `--purge` but no token, the script **warns and
skips** (non-fatal). Overridable host via `CF_PUBLIC_HOST` (default `data.clinvar-gkm.org`). All purge
methods (URL, prefix, hostname, tag, everything) are available on all plans since 2025-04. Manual
equivalent:
```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/purge_cache" \
  -H "Authorization: Bearer ${CF_PURGE_TOKEN}" -H "Content-Type: application/json" \
  --data '{"prefixes":["data.clinvar-gkm.org/v1/datasets/"]}'   # or {"purge_everything":true}
```

### CORS

Bucket CORS is applied out-of-band (`apply-r2-cors.sh` with an admin token, or the dashboard; policy in
`src/scripts/r2-cors.json`) and is returned at the **bucket** level, so it passes through the custom domain.
The docs download browser (`docs/assets/js/r2-browser.js`) now fetches from `data.clinvar-gkm.org`; ensure
the docs-site origin is allowed in `r2-cors.json`.

### Optional future: a `clinicalgenome.org` entry point

If a ClinGen-branded link is ever wanted, the Route 53 admin can host an **S3 static-website redirect +
Route 53 alias** at e.g. `clinvar-gkm-data.clinicalgenome.org` → `https://data.clinvar-gkm.org`. Purely
additive; not required for anything to work.

### Bucket layout note

Only the `v1/` tree is live. The bucket root holds just the thin `index.json` manifest (ADR 0004) alongside
`v1/`; the pre-`v1/` root `datasets/` and `deltas/` trees plus root `README.txt` were deleted on 2026-10-13.
All uploaders (including `backfill-monthly-to-r2.sh`) and the docs now reference `v1/…` paths.

### Layout change (ADR 0009)

[ADR 0009](0009-r2-layout-mirrors-ncbi-clinvar.md) replaces the `/v1/` layout above with per-line folders
modelled on NCBI's ClinVar FTP: `v1/1.1/` holds the official monthlies and `clinvar-gkm_00-latest.json.gz`,
`weekly/` (the current month's weekly fulls and `clinvar-gkm_00-latest_weekly.json.gz`), `deltas/` (current
month at the top, earlier months in `deltas/YYYY-MM/`), `archive/YYYY/` and one `parquet/` dataset; the 1.0.1
generation becomes the frozen line `v1/1.0/`. What changes here (`src/scripts/cf-rules.sh` holds the exact
rule expressions: `show` compares them with the live rules, `apply` is a user-confirmed step):

- **Immutable rule.** Unchanged; it still matches every path, so in effect it covers everything the later
  rules do not catch: dated monthlies, deltas, delta manifests, `.sha256` sidecars outside `weekly/`,
  `archive/YYYY/`, and frozen line folders' bundles and `MANIFEST.json`. The path list above no longer
  applies.
- **Mutable-pointer rule.** Bypasses the cache for any path containing `00-latest` (which also matches
  `clinvar-gkm_00-latest_weekly.json.gz`), ending in `/index.json`, `/feed.xml` or `/README.txt`, or containing
  `/weekly/`. Weekly fulls and their sidecars are deleted at month rollover, so they are not cached as
  immutable.
- **Latest-Parquet rule.** The "Latest Parquet: cache 1 day" rule (added 2026-10-18; edge 1 day, browser 1 h)
  matched `/v1/datasets/parquet/00-latest/`, which no longer exists. It now matches any path under `/v1/`
  containing `/parquet/`, which includes `parquet/manifest.json`. Without the change the overwritten Parquet
  would fall under the 1-month immutable rule.
- **Purges.** Routine releases now overwrite (the Parquet dataset), move (deltas at month rollover, monthlies
  and deltas at year rollover) and delete (weekly fulls at month rollover; the finished month's newest once
  the new monthly is published) published paths. `r2-rollover.sh` purges every path it moved or deleted, and
  `run-release.sh` purges the `parquet/` prefix after each rebuild; `--purge` above is no longer only for the
  rare in-place overwrite.
- **Path allowlist** (WAF custom rule, documented on PR #173). Every published path stays under `/v1/`, so no
  new prefix is needed. `/archive/` can be removed once `archive/1.0.1/` has moved to `v1/1.0/` and been
  deleted (`cf-rules.sh apply --drop-archive`).
- **Bucket layout note.** The "Only the `v1/` tree is live" note still holds; the old `v1/datasets/`,
  `v1/deltas/` and dated Parquet trees and `archive/1.0.1/` are deleted in the ADR 0009 cleanup.
