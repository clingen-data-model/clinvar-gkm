#!/usr/bin/env python3
"""Announce a new official monthly full bundle to the email list and GitHub Discussions (ADR 0010).

Reads only what is published (the root index.json, the current line's index.json and the delta manifests on
data.clinvar-gkm.org), so the announcement describes exactly what a consumer can download. Run by
.github/workflows/announce-monthly.yml; standard library only.

  render      decide whether a monthly is due and write the announcement into --out:
                plan.json      {"month", "pending": [channels still to do], "subject"}; pending is empty when
                               there is nothing to announce
                email.txt      the plain-text email
                discussion.md  the Markdown post for Discussions -> Announcements
  send-email  send --out's email over SMTP. Env: SMTP_HOST, SMTP_PORT (465 = TLS, otherwise STARTTLS),
              SMTP_USERNAME, SMTP_PASSWORD, ANNOUNCE_FROM, ANNOUNCE_TO
  mark        record that a channel is done for a month in the state file

Which monthly is due: the newest official monthly of the current version line, when its month is later than
--after and than every month already in the state file. A republish into a new line therefore announces
nothing: its monthlies are months already announced. --month names one explicitly (a re-run, or a test).

The digest lists the weekly deltas after the previous monthly's source release, up to and including this
monthly's (ADR 0002). Applied in order to the previous monthly they give this one, and each delta is listed
in exactly one announcement.

State file: {"announced": {"YYYY-MM": {"email": "<UTC time>", "discussion": "<url>"}}}.
"""
import argparse
import json
import os
import smtplib
import sys
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r2_layout import _monthly_pool  # noqa: E402

ROOT_INDEX_URL = "https://data.clinvar-gkm.org/index.json"
DOCS = "https://dataexchange.clinicalgenome.org/clinvar-gkm"
REPO = "https://github.com/clingen-data-model/clinvar-gkm"
LIST = "clinvar-gkm@broadinstitute.org"
CHANNELS = ("email", "discussion")


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": f"clinvar-gkm-announce (+{REPO})"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def human_size(n):
    for unit, div in (("GB", 1e9), ("MB", 1e6), ("KB", 1e3)):
        if n >= div:
            return f"{n / div:.1f} {unit}"
    return f"{n} B"


def current_line(root):
    """The line entry ({line, index, ...}) the root manifest names as current."""
    versions = list((root.get("versions") or {}).values())
    line = next((v for v in versions if v.get("line") == root.get("current")), None)
    line = line or next((v for v in versions if v.get("status") == "current"), None)
    if not line:
        raise SystemExit("ERROR: the root index names no current version line")
    return line


def all_deltas(index):
    pool = list(index.get("deltas") or [])
    pool += [d for y in (index.get("archives") or {}).values() for d in y.get("deltas", [])]
    return sorted(pool, key=lambda d: d["release"])


def choose(index, state, after, month=None):
    """(target monthly, previous monthly or None, pending channels). target is None when nothing is due."""
    monthlies = sorted(_monthly_pool(index), key=lambda m: m["release"])
    if not monthlies:
        return None, None, []
    done = (state.get("announced") or {})
    if month:
        target = next((m for m in monthlies if m["release"] == month), None)
        if not target:
            raise SystemExit(f"ERROR: no official monthly {month} in {index.get('line')}")
    else:
        target = monthlies[-1]
        if (after and target["release"] <= after) or any(m > target["release"] for m in done):
            return None, None, []
    earlier = [m for m in monthlies if m["release"] < target["release"]]
    pending = [c for c in CHANNELS if c not in done.get(target["release"], {})]
    return target, (earlier[-1] if earlier else None), pending


def window(index, prev, target):
    """The deltas after prev's source release, up to and including target's."""
    if not prev:
        return []
    lo, hi = prev["source_release"], target["source_release"]
    return [d for d in all_deltas(index) if lo < d["release"] <= hi]


def digest_rows(index, deltas, fetch):
    base = index["base_url"].rstrip("/")
    rows = []
    for d in deltas:
        counts = fetch(f"{base}/{d['manifest']}").get("counts") or {}
        rows.append({"release": d["release"], "added": counts.get("A", 0), "updated": counts.get("U", 0),
                     "deleted": counts.get("D", 0), "size": d["bundle"]["size"],
                     "url": f"{base}/{d['bundle']['path']}"})
    return rows


def render(index, target, prev, rows):
    """(subject, email text, discussion Markdown)."""
    base = index["base_url"].rstrip("/")
    line = index["line"]
    month, src = target["release"], target["source_release"]
    url = f"{base}/{target['path']}"
    subject = f"ClinVar-GKM {month} monthly release is available"
    intro = (f"The ClinVar-GKM monthly full bundle for {month} is now available. It was built from the {src} "
             f"weekly release, the last ClinVar-GKM build before ClinVar's own {month} monthly release.")
    if prev:
        about = (f"The {prev['release']} monthly was built from the {prev['source_release']} release. Applied in "
                 f"order to it, these {len(rows)} weekly deltas give the {month} monthly. Counts are records "
                 f"added, updated and deleted, across all sections.")
        later = f"Deltas released after {src} will be listed with the next monthly."
    links = [("Downloads", f"{DOCS}/data-access/download/"),
             ("Monthly full bundles", f"{DOCS}/data-access/monthly-full/"),
             ("Applying weekly deltas", f"{DOCS}/data-access/weekly-deltas/"),
             ("Release index (JSON)", f"{base}/{line}/index.json"),
             ("Atom feed", f"{base}/{line}/feed.xml"),
             ("Changelog", f"{DOCS}/reference/changelog/")]
    moved = ("Every file's current path is in the release index. Deltas from earlier months move into dated "
             "folders as months and years roll over, so if a link here stops working, look the file up there.")

    t = [intro, "", "MONTHLY FULL BUNDLE", "",
         f"  {target['name']}   {human_size(target['size'])}   schema {index.get('schema_version', '')}",
         f"  {url}", f"  sha256 {target.get('sha256', '')}", ""]
    if prev:
        t += [f"WEEKLY DELTAS SINCE THE {prev['release']} MONTHLY", "", about, ""]
        t += [f"  {'Release':<12}{'Added':>12}{'Updated':>12}{'Deleted':>12}{'Size':>11}"]
        t += [f"  {r['release']:<12}{r['added']:>12,}{r['updated']:>12,}{r['deleted']:>12,}{human_size(r['size']):>11}"
              for r in rows]
        t += [""] + [f"  {r['release']}  {r['url']}" for r in rows] + ["", later, ""]
    t += ["WHERE TO FIND EVERYTHING", ""] + [f"  {k:<24}{v}" for k, v in links] + ["", moved, "",
          "--", f"ClinVar-GKM  {REPO}", f"You are receiving this because you joined {LIST}.",
          f"To leave, email {LIST.replace('@', '+unsubscribe@')}."]

    m = [intro, "", "## Monthly full bundle", "",
         "| File | Size | Schema | sha256 |", "| --- | --- | --- | --- |",
         f"| [`{target['name']}`]({url}) | {human_size(target['size'])} | {index.get('schema_version', '')} "
         f"| `{target.get('sha256', '')}` |", ""]
    if prev:
        m += [f"## Weekly deltas since the {prev['release']} monthly", "", about, "",
              "| Release | Added | Updated | Deleted | Size |", "| --- | ---: | ---: | ---: | ---: |"]
        m += [f"| [{r['release']}]({r['url']}) | {r['added']:,} | {r['updated']:,} | {r['deleted']:,} "
              f"| {human_size(r['size'])} |" for r in rows]
        m += ["", later, ""]
    m += ["## Where to find everything", ""] + [f"- [{k}]({v})" for k, v in links] + ["", moved, "",
          f"Get these announcements by email: join [{LIST}]({DOCS}/stay-informed/)."]
    return subject, "\n".join(t) + "\n", "\n".join(m) + "\n"


def load_state(path):
    p = Path(path)
    return json.loads(p.read_text()) if p.is_file() else {"announced": {}}


def cmd_render(a):
    index = fetch_json(f"{ROOT_INDEX_URL.rsplit('/', 1)[0]}/{current_line(fetch_json(ROOT_INDEX_URL))['index']}")
    target, prev, pending = choose(index, load_state(a.state), a.after, a.month)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if not target or not pending:
        what = f"{target['release']} is already announced" if target else "no new monthly to announce"
        print(f"Nothing to do: {what}.")
        (out / "plan.json").write_text(json.dumps({"month": target and target["release"], "pending": []}))
        return
    subject, text, md = render(index, target, prev, digest_rows(index, window(index, prev, target), fetch_json))
    (out / "email.txt").write_text(text)
    (out / "discussion.md").write_text(md)
    (out / "plan.json").write_text(json.dumps({"month": target["release"], "pending": pending, "subject": subject}))
    print(f"Due: {target['release']} (pending: {', '.join(pending)})")


def cmd_send_email(a):
    out = Path(a.out)
    plan = json.loads((out / "plan.json").read_text())
    env = {k: os.environ.get(k, "") for k in ("SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD",
                                               "ANNOUNCE_FROM", "ANNOUNCE_TO")}
    missing = [k for k, v in env.items() if not v]
    if missing:
        raise SystemExit(f"ERROR: missing {', '.join(missing)}")
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = env["ANNOUNCE_FROM"], env["ANNOUNCE_TO"], plan["subject"]
    msg["Date"] = formatdate(localtime=False)
    msg["Message-ID"] = make_msgid(domain=env["ANNOUNCE_FROM"].rsplit("@", 1)[-1].strip(">"))
    msg.set_content((out / "email.txt").read_text())
    port = int(env["SMTP_PORT"])
    smtp = smtplib.SMTP_SSL(env["SMTP_HOST"], port, timeout=60) if port == 465 else smtplib.SMTP(
        env["SMTP_HOST"], port, timeout=60)
    with smtp:
        if port != 465:
            smtp.starttls()
        smtp.login(env["SMTP_USERNAME"], env["SMTP_PASSWORD"])
        smtp.send_message(msg)
    print(f"Sent '{plan['subject']}' to {env['ANNOUNCE_TO']}")


def cmd_mark(a):
    state = load_state(a.state)
    value = a.value or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state.setdefault("announced", {}).setdefault(a.month, {})[a.channel] = value
    Path(a.state).write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--state", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--after", default="", help="announce only monthlies later than this YYYY-MM")
    r.add_argument("--month", default="", help="announce this YYYY-MM instead of the newest")
    s = sub.add_parser("send-email")
    s.add_argument("--out", required=True)
    k = sub.add_parser("mark")
    k.add_argument("--state", required=True)
    k.add_argument("--month", required=True)
    k.add_argument("--channel", required=True, choices=CHANNELS)
    k.add_argument("--value", default="")
    a = p.parse_args(argv)
    {"render": cmd_render, "send-email": cmd_send_email, "mark": cmd_mark}[a.cmd](a)


if __name__ == "__main__":
    main()
