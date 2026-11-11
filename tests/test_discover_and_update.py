import copy, json, os
import pytest
import update as U

HTML = """
<table>
<tr><td><a href="/sites/default/files/beef9-2025-2026-panchangam-english-pdf-text-.pdf">English</a></td>
    <td><a href="https://www.syromalabarliturgy.org/files/d7fa5-2025-2026-panchangam-malayalam.pdf">Malayalam</a></td></tr>
<tr><td><a href="/files/aaaaa-2026-2027-panchangam-english-pdf.pdf">English 26-27</a></td></tr>
<tr><td><a href="https://evil.example.com/2027-2028-panchangam-english.pdf">fake</a></td></tr>
<tr><td><a href="/files/lectionary-2026.pdf">other</a></td></tr>
</table>
"""


def test_finds_english_booklets_only_on_the_allowed_host():
    links = U.find_panchangam_links(HTML)
    assert [l[0] for l in links] == ["2026-2027", "2025-2026"]
    assert all(u.startswith("https://www.syromalabarliturgy.org/") for _, u in links)
    assert "malayalam" not in " ".join(u for _, u in links)


def test_hosts_and_redirects_are_restricted():
    assert U.allowed_url("https://www.syromalabarliturgy.org/x.pdf")
    assert not U.allowed_url("http://www.syromalabarliturgy.org/x.pdf")
    assert not U.allowed_url("https://syromalabarliturgy.org.evil.com/x.pdf")
    with pytest.raises(ValueError):
        U.http_get("https://evil.example.com/a.pdf")


def fake_fetch_factory(html, pdf_bytes=b"%PDF" + b"0" * 300_000):
    def fetch(url, limit=0, timeout=0):
        return html.encode() if url == U.LIST_PAGE else pdf_bytes
    return fetch


def test_nothing_new_is_not_an_error(repo_copy):
    html = '<a href="/files/beef9-2025-2026-panchangam-english-pdf.pdf">x</a>'
    r = U.run_update(repo_copy, fetch=fake_fetch_factory(html))
    assert r["status"] == "up-to-date"


def test_unreachable_site_is_an_error(repo_copy):
    def boom(url, limit=0, timeout=0):
        raise OSError("403")
    r = U.run_update(repo_copy, fetch=boom)
    assert r["status"] == "error" and "not reachable" in r["reason"]


def test_a_page_without_any_pdf_links_is_reported_as_a_layout_change(repo_copy):
    r = U.run_update(repo_copy, fetch=fake_fetch_factory("<html>coming soon</html>"))
    assert r["status"] == "error" and "layout" in r["reason"]


def test_download_that_is_not_a_pdf_is_rejected(repo_copy):
    html = '<a href="/files/aaaaa-2026-2027-panchangam-english-pdf.pdf">x</a>'
    r = U.run_update(repo_copy, fetch=fake_fetch_factory(html, pdf_bytes=b"<html>login</html>"))
    assert r["status"] == "error" and "not a PDF" in r["reason"]


def _snapshot(root):
    out = {}
    for d in ("days", "sources"):
        for f in sorted(os.listdir(os.path.join(root, d))):
            out[d + "/" + f] = open(os.path.join(root, d, f), "rb").read()
    out["index.json"] = open(os.path.join(root, "index.json"), "rb").read()
    return out


def test_a_bad_booklet_changes_nothing(repo_copy):
    days = json.load(open(os.path.join(repo_copy, "sources", "2025-2026.json"), encoding="utf-8"))
    for k in list(days)[:60]:
        del days[k]
    before = _snapshot(repo_copy)
    r = U.process_parsed(repo_copy, "2026-2027", days, [], "test")
    assert r["status"] == "error"
    assert _snapshot(repo_copy) == before


def test_a_good_booklet_is_registered_and_built(repo_copy):
    # pretend the 2025-26 data is a new booklet: shift every date forward by exactly one year of 364 days (52 weeks)
    import datetime as dt
    src = json.load(open(os.path.join(repo_copy, "sources", "2025-2026.json"), encoding="utf-8"))
    shifted = {}
    for k, v in src.items():
        nd = dt.date.fromisoformat(k) + dt.timedelta(days=364)
        v = copy.deepcopy(v); v["banner"] = None
        shifted[nd.isoformat()] = v
    # Annunciation 2026 starts on 29 Nov, which is 2025-11-30 + 364
    r = U.process_parsed(repo_copy, "2026-2027", shifted, [], "test")
    assert r["status"] in ("published", "published-review"), r
    idx = json.load(open(os.path.join(repo_copy, "index.json"), encoding="utf-8"))
    assert idx["coverage"]["last"] >= "2027-12-01" and "2027" in idx["years"]


def test_health_alerts_when_the_data_is_about_to_run_out(repo_copy):
    import datetime as dt
    assert U.run_health(repo_copy, today=dt.date(2026, 11, 1))["status"] == "health-ok"
    assert U.run_health(repo_copy, today=dt.date(2026, 12, 5))["status"] == "health-alert"
    assert U.run_health(repo_copy, today=dt.date(2026, 12, 21), require_next_year=True)["status"] == "health-alert"


def test_issue_text_is_written_for_every_alert_kind():
    for res in ({"status": "error", "reason": "x", "errors": ["e"], "title": "t"},
                {"status": "health-alert", "reason": "r", "title": "t"},
                {"status": "published-review", "booklet": "2026-2027", "days": 365, "review": {"2027-02-01": ["odd"]}}):
        assert len(U.issue_markdown(res)) > 40
