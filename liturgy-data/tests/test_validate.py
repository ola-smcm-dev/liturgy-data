import copy, json, os
import validate as V
from conftest import ROOT


def booklet():
    return json.load(open(os.path.join(ROOT, "sources", "2025-2026.json"), encoding="utf-8"))


def test_the_real_booklet_passes():
    errors, warnings, review = V.validate(booklet(), expect_first="2025-12-01", expect_last="2026-12-01")
    assert errors == []


def test_a_missing_day_is_an_error():
    d = booklet()
    del d["2026-03-10"]
    assert any("missing" in e for e in V.validate(d)[0])


def test_too_short_is_an_error():
    d = booklet()
    for k in list(d)[:100]:
        del d[k]
    assert V.validate(d)[0]


def test_empty_readings_everywhere_is_an_error():
    d = booklet()
    for v in d.values():
        for g in v["groups"]:
            g["readings"] = []
    assert V.validate(d)[0]


def test_a_broken_day_is_flagged_for_review_not_fatal():
    d = booklet()
    d["2026-03-10"]["groups"][0]["readings"] = d["2026-03-10"]["groups"][0]["readings"][:1]
    errors, warnings, review = V.validate(d)
    assert errors == [] and "2026-03-10" in review
