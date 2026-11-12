"""Checks on the files that apps actually read."""
import json, os, re, datetime as dt
from conftest import ROOT
import calendar_rules as C


def load(rel):
    return json.load(open(os.path.join(ROOT, rel), encoding="utf-8"))


def all_days():
    idx = load("index.json")
    out = {}
    for y, info in idx["years"].items():
        d = load(info["file"])
        assert d["year"] == int(y)
        out.update(d["days"])
    return idx, out


def test_index_matches_files_and_has_no_gaps():
    idx, days = all_days()
    first, last = dt.date.fromisoformat(idx["coverage"]["first"]), dt.date.fromisoformat(idx["coverage"]["last"])
    assert (last - first).days + 1 == len(days)
    assert idx["schema"] == 1


def test_every_day_has_a_season_and_readings():
    _, days = all_days()
    for iso, d in days.items():
        assert d["season"] in C.SEASON_NAMES, iso
        assert d["celebrations"] and any(c["readings"] for c in d["celebrations"]), iso
        assert d["weekday"] == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.date.fromisoformat(iso).weekday()]


def test_every_book_in_every_reading_is_in_the_books_table():
    aliases = {a for b in load("data/books.json")["books"] for a in b["aliases"]}
    _, days = all_days()
    unknown = set()
    for iso, d in days.items():
        for c in d["celebrations"]:
            for r in c["readings"]:
                m = re.match(r"((?:[1-3]\s?)?[A-Za-z]+)", r["ref"])
                if m and re.sub(r"[\s.]", "", m.group(1).lower()) not in aliases:
                    unknown.add(r["ref"])
    assert not unknown, sorted(unknown)[:10]


def test_text_is_plain_text_only():
    """Apps should show these with textContent; make sure nothing that looks like markup got in."""
    _, days = all_days()
    for iso, d in days.items():
        for c in d["celebrations"]:
            for s in [c["label"]] + c.get("notes", []) + [x for r in c["readings"] for x in (r["ref"], r["title"])]:
                assert "<" not in s and ">" not in s, (iso, s)


def test_rebuilding_changes_nothing(repo_copy):
    import build
    before = {f: open(os.path.join(repo_copy, "days", f), "rb").read() for f in os.listdir(os.path.join(repo_copy, "days"))}
    idx_before = open(os.path.join(repo_copy, "index.json"), "rb").read()
    r = build.build(repo_copy, log=lambda *_: None)
    assert r["changed"] is False
    assert {f: open(os.path.join(repo_copy, "days", f), "rb").read() for f in os.listdir(os.path.join(repo_copy, "days"))} == before
    assert open(os.path.join(repo_copy, "index.json"), "rb").read() == idx_before


def test_the_final_checks_pass_on_the_published_files():
    import checks
    assert checks.published_problems(ROOT) == []
