import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import announce_monthly as A  # noqa: E402

L = "v1/1.1"


def monthly(label, source, latest=False):
    name = "clinvar-gkm_00-latest.json.gz" if latest else f"clinvar-gkm_{label}.json.gz"
    return {"name": name, "path": f"{L}/{name}", "size": 4_700_000_000, "sha256": "ab" * 32,
            "release": label, "source_release": source, "latest": latest}


def delta(d, folder=""):
    c = f"{d[:4]}-{d[5:7]}{d[8:10]}"
    base = f"{L}/deltas/{folder}clinvar-gkm-delta_{c}"
    return {"release": d, "month": d[:7], "manifest": base + ".manifest.json",
            "bundle": {"path": base + ".json.gz", "sha256": "cd" * 32, "size": 5_400_000}}


def index(**over):
    i = {"line": L, "base_url": "https://data.clinvar-gkm.org", "schema_version": "1.1.0",
         "datasets": {"monthly": [monthly("2026-09", "2026-08-29"), monthly("2026-10", "2026-09-28"),
                                  monthly("2026-10", "2026-09-28", latest=True)], "weekly": []},
         "deltas": [delta(d, "2026-09/") for d in ("2026-08-29", "2026-09-05", "2026-09-13", "2026-09-28")]
                   + [delta("2026-10-04")],
         "archives": {}}
    i.update(over)
    return i


def months(ms):
    return [m["release"] for m in ms]


def test_newest_monthly_is_due_with_both_channels():
    target, prev, pending = A.choose(index(), {"announced": {}}, after="2026-09")
    assert (target["release"], prev["release"], pending) == ("2026-10", "2026-09", ["email", "discussion"])
    assert target["name"] == "clinvar-gkm_2026-10.json.gz"   # the dated monthly, never the 00-latest copy


def test_nothing_due_at_or_before_after():
    assert A.choose(index(), {"announced": {}}, after="2026-10")[0] is None


def test_only_the_channel_not_yet_done_is_pending():
    state = {"announced": {"2026-10": {"email": "2026-10-05T00:00:00Z"}}}
    assert A.choose(index(), state, after="")[2] == ["discussion"]
    state["announced"]["2026-10"]["discussion"] = "https://github.com/x/y/discussions/1"
    assert A.choose(index(), state, after="")[2] == []


def test_a_republish_into_a_new_line_announces_nothing():
    # A new line holds months already announced; a later month in the state means nothing is due.
    state = {"announced": {"2026-11": {"email": "t", "discussion": "u"}}}
    assert A.choose(index(), state, after="")[0] is None


def test_explicit_month_ignores_after():
    target, prev, _ = A.choose(index(), {"announced": {}}, after="2026-10", month="2026-09")
    assert (target["release"], prev) == ("2026-09", None)


def test_window_is_after_previous_source_through_this_source():
    i = index()
    target, prev, _ = A.choose(i, {"announced": {}}, after="")
    assert [d["release"] for d in A.window(i, prev, target)] == ["2026-09-05", "2026-09-13", "2026-09-28"]
    assert A.window(i, None, target) == []


def test_window_reaches_into_archives_across_a_year_rollover():
    i = index(datasets={"monthly": [monthly("2027-01", "2026-12-27")], "weekly": []},
              deltas=[delta("2027-01-03")],
              archives={"2026": {"monthly": [monthly("2026-12", "2026-11-29")],
                                 "deltas": [delta("2026-12-06"), delta("2026-12-27")]}})
    target, prev, _ = A.choose(i, {"announced": {}}, after="")
    assert prev["release"] == "2026-12"
    assert [d["release"] for d in A.window(i, prev, target)] == ["2026-12-06", "2026-12-27"]


def test_render_lists_each_delta_with_counts_and_links():
    i = index()
    target, prev, _ = A.choose(i, {"announced": {}}, after="")
    rows = A.digest_rows(i, A.window(i, prev, target), lambda url: {"counts": {"A": 1234, "U": 5, "D": 1_546_948}})
    subject, text, md = A.render(i, target, prev, rows)
    assert subject == "ClinVar-GKM 2026-10 monthly release is available"
    assert "https://data.clinvar-gkm.org/v1/1.1/clinvar-gkm_2026-10.json.gz" in text
    assert "these 3 weekly deltas give the 2026-10 monthly" in text
    assert "1,546,948" in text and "1,546,948" in md
    for d in ("2026-0905", "2026-0913", "2026-0928"):
        assert f"deltas/2026-09/clinvar-gkm-delta_{d}.json.gz" in text
    assert "2026-10-04" not in text   # after this monthly's source release: the next announcement's
    assert "clinvar-gkm+unsubscribe@broadinstitute.org" in text


def test_mark_records_a_channel(tmp_path):
    state = tmp_path / "announced.json"
    A.main(["mark", "--state", str(state), "--month", "2026-10", "--channel", "email", "--value", "t"])
    A.main(["mark", "--state", str(state), "--month", "2026-10", "--channel", "discussion", "--value", "u"])
    assert A.load_state(state) == {"announced": {"2026-10": {"email": "t", "discussion": "u"}}}


def test_send_email_uses_starttls_and_the_rendered_message(tmp_path, monkeypatch):
    (tmp_path / "plan.json").write_text('{"month": "2026-10", "pending": ["email"], "subject": "S"}')
    (tmp_path / "email.txt").write_text("body\n")
    calls = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls.append(("connect", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self):
            calls.append(("starttls",))

        def login(self, user, password):
            calls.append(("login", user))

        def send_message(self, msg):
            calls.append(("send", msg["From"], msg["To"], msg["Subject"], msg.get_content()))

    monkeypatch.setattr(A.smtplib, "SMTP", FakeSMTP)
    for k, v in {"SMTP_HOST": "smtp.example.org", "SMTP_PORT": "587", "SMTP_USERNAME": "bot",
                 "SMTP_PASSWORD": "pw", "ANNOUNCE_FROM": "bot@example.org", "ANNOUNCE_TO": "list@example.org"}.items():
        monkeypatch.setenv(k, v)
    A.main(["send-email", "--out", str(tmp_path)])
    assert calls == [("connect", "smtp.example.org", 587), ("starttls",), ("login", "bot"),
                     ("send", "bot@example.org", "list@example.org", "S", "body\n")]
