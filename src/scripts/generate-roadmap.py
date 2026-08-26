#!/usr/bin/env python3
"""Generate the docs Roadmap backlog table from GitHub Discussions.

Any discussion carrying the ``roadmap authorized`` label is rendered as a row in the
table between the ``<!-- ROADMAP:START -->`` / ``<!-- ROADMAP:END -->`` markers in
``docs/reference/roadmap.md``. Rows are ordered by upvote count (descending), ties broken
by creation date. Status comes from an optional ``status: <x>`` label (default *Proposed*).
The idea's one-line summary is the first non-empty line of the discussion body.

Authorizing an idea = add the label; de-authorizing = remove it. Uses the ``gh`` CLI, which
is authenticated locally and, in CI, via the ``GH_TOKEN`` environment variable.
"""
import json
import pathlib
import re
import subprocess

OWNER, REPO = "clingen-data-model", "clinvar-gkm"
AUTHORIZED_LABEL = "roadmap authorized"
ROADMAP = pathlib.Path(__file__).resolve().parents[2] / "docs" / "reference" / "roadmap.md"
START, END = "<!-- ROADMAP:START -->", "<!-- ROADMAP:END -->"
SUMMARY_MAX = 160

STATUS_MAP = {
    "status: proposed": "Proposed",
    "status: spec'd": "Spec'd",
    "status: in progress": "In progress",
    "status: shipped": "Shipped",
}

QUERY = """
query($owner:String!,$repo:String!,$after:String){
  repository(owner:$owner,name:$repo){
    discussions(first:100, after:$after){
      pageInfo{ hasNextPage endCursor }
      nodes{ number title url upvoteCount createdAt body
        labels(first:20){ nodes{ name } } }
    }
  }
}
"""


def _page(after=None):
    args = ["gh", "api", "graphql", "-f", f"owner={OWNER}", "-f", f"repo={REPO}",
            "-f", f"query={QUERY}"]
    if after:
        args += ["-f", f"after={after}"]
    out = subprocess.run(args, capture_output=True, text=True, check=True).stdout
    return json.loads(out)["data"]["repository"]["discussions"]


def _summary(body: str) -> str:
    for line in (body or "").splitlines():
        line = line.strip()
        if line and not line.startswith(("---", "#", ">", "|")):
            line = re.sub(r"\*\*|`", "", line)          # drop bold/code markers
            line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)  # links -> text
            return (line[:SUMMARY_MAX - 1] + "…") if len(line) > SUMMARY_MAX else line
    return ""


def fetch_items():
    items, after = [], None
    while True:
        page = _page(after)
        for n in page["nodes"]:
            names = [lbl["name"] for lbl in n["labels"]["nodes"]]
            if AUTHORIZED_LABEL not in names:
                continue
            status = next((STATUS_MAP[x] for x in names if x in STATUS_MAP), "Proposed")
            items.append({
                "number": n["number"], "title": n["title"], "url": n["url"],
                "up": n["upvoteCount"], "created": n["createdAt"],
                "status": status, "summary": _summary(n["body"]),
            })
        if page["pageInfo"]["hasNextPage"]:
            after = page["pageInfo"]["endCursor"]
        else:
            break
    items.sort(key=lambda x: (-x["up"], x["created"]))
    return items


def render(items) -> str:
    rows = ["| # | Idea | Status | Upvotes | Discussion |",
            "| --- | --- | --- | --- | --- |"]
    for i, it in enumerate(items, 1):
        title = it["title"].replace("|", "\\|")
        summary = it["summary"].replace("|", "\\|")
        idea = f"**{title}**" + (f" — {summary}" if summary else "")
        rows.append(f'| {i} | {idea} | {it["status"]} | {it["up"]} | '
                    f'[#{it["number"]}]({it["url"]}) |')
    return "\n".join(rows)


def main():
    items = fetch_items()
    table = render(items)
    text = ROADMAP.read_text()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        raise SystemExit(f"markers {START} / {END} not found in {ROADMAP}")
    new = pattern.sub(f"{START}\n{table}\n{END}", text)
    if new != text:
        ROADMAP.write_text(new)
        print(f"roadmap.md updated: {len(items)} authorized items")
    else:
        print(f"roadmap.md unchanged: {len(items)} authorized items")


if __name__ == "__main__":
    main()
