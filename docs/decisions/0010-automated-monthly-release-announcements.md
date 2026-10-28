# 0010 — Automated monthly release announcements

- **Status:** Proposed
- **Date:** 2026-10-28
- **Amends:** [ADR 0004](0004-schema-versioning-and-release-management.md) §7 (the email list and Discussions
  carry the same announcements; this makes the monthly one automatic)

## Context

The email list `clinvar-gkm@broadinstitute.org` (a Google Group) and GitHub Discussions → Announcements are the
two announcement channels (ADR 0004 §7), but nothing posted to them: the 2026-10-24 release went out without a
notice. Weekly releases are too frequent to announce one by one. The official monthly full bundle (ADR 0002) is
the natural checkpoint: it is the full a consumer starts from, and the weekly deltas since the previous monthly
are what turned that one into this one.

Releases run by hand on a maintainer's machine (`run-release.sh`), so an announcement sent from there would
depend on that machine being online and would put mail credentials on it.

## Decision

1. **What is announced.** Each new official monthly, once, with a digest of the weekly deltas after the previous
   monthly's `source_release`, up to and including this monthly's. Applied in order to the previous monthly they
   give this one, and every delta is listed in exactly one announcement. The digest gives each delta's release
   date, its added/updated/deleted record counts (the manifest's `counts`), its size and a direct link, and the
   email points to the Downloads pages, the line's `index.json` and `feed.xml`, and the Changelog.
2. **Where it runs.** `.github/workflows/announce-monthly.yml`, every two hours and on demand. It reads only the
   published root `index.json`, the current line's `index.json` and the delta manifests
   (`src/scripts/announce_monthly.py`), so it announces exactly what consumers can download and needs nothing from
   the release machine. `run-release.sh` is unchanged; a new monthly is announced within about two hours.
3. **Which monthly is due.** The newest official monthly of the current line, when its month is later than
   `ANNOUNCE_AFTER` (`2026-10`: monthlies published before this existed are never announced automatically) and
   later than every month already announced. A republish into a new version line therefore announces nothing.
4. **Both channels, each exactly once.** The email goes over SMTP from a dedicated service mailbox (not a
   person's account), and the same text is posted as a Discussion in Announcements with the workflow's
   `GITHUB_TOKEN`. Each channel is recorded in `announced.json` on the orphan branch `ops/announcements` as soon
   as it succeeds, so a re-run retries only what failed and never sends twice.
5. **Safe to try.** A manual run is a dry run by default: the announcement goes to the job summary and an
   artifact. The repository variable `ANNOUNCE_TO` redirects the email (for a test send to yourself); unset, it
   is the list.

## Setup (once)

1. **Sender.** Create the service mailbox, turn on 2-step verification, and create an app password for SMTP
   (for Gmail or Google Workspace: `smtp.gmail.com`, port 587, STARTTLS).
2. **Let it post.** In the Google Group, add the mailbox as a member (or allow it in *Who can post*) so its
   messages aren't held for moderation.
3. **GitHub.** Settings → Environments → New environment `announce`; limit deployment branches to `main`. Add the
   secrets `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` (the app password) and `ANNOUNCE_FROM` (for
   example `ClinVar-GKM <service-mailbox@example.org>`).
4. **Test.** Set the repository variable `ANNOUNCE_TO` to your own address. Run *Monthly release announcement*
   with `month = 2026-10` and `dry_run` off: check the email, then delete the test Discussion and the `2026-10`
   entry on `ops/announcements` (or the branch). Delete `ANNOUNCE_TO` to send to the list.

## Consequences

- Members hear about every monthly without anyone remembering to write it, and the digest is generated from the
  same index and manifests consumers use, so it can't drift from what is published.
- Weekly releases are still not announced individually; a consumer who wants each one follows `feed.xml`.
- Direct delta links in old announcements break when the deltas move (month rollover into `deltas/YYYY-MM/`,
  year rollover into `archive/YYYY/`, ADR 0009). The email says so and points to `index.json`, which always has
  the current paths.
- Version releases, RFCs, corrections and events are still announced by hand.
- A failed send shows as a failed workflow run; the next scheduled run retries it.
