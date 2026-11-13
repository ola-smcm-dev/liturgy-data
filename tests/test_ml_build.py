"""The Malayalam layer (days-ml/): same shape as the English files, verses copied exactly, nothing half-translated."""
import json, os, re
from conftest import ROOT
import ml_build as MB


def load(rel):
    return json.load(open(os.path.join(ROOT, rel), encoding="utf-8"))


def test_published_malayalam_layer_passes_its_checks():
    assert MB.ml_problems(ROOT) == []


def test_every_english_day_has_a_malayalam_day_in_the_same_order():
    idx = load("index.json")
    assert set(idx["malayalam"]["years"]) == set(idx["years"])
    for y, info in idx["years"].items():
        en = load(info["file"])["days"]
        ml = load(idx["malayalam"]["years"][y]["file"])["days"]
        assert list(en) == list(ml)
        for iso, d in en.items():
            assert len(ml[iso]["celebrations"]) == len(d["celebrations"])


def test_known_days():
    ml = load("days-ml/2026.json")["days"]
    assert ml["2026-11-12"]["celebrations"][0]["label"] == "പള്ളിക്കൂദാശ രണ്ടാം വ്യാഴം"
    assert [r["ref"] for r in ml["2026-11-12"]["celebrations"][0]["readings"]] == ["2 കോറി 11:1-4", "യോഹ 3:22-30"]
    aug = ml["2026-08-15"]["celebrations"][0]["readings"]
    assert aug[3]["main"] == "യോഹ 2:1-12" and aug[3]["full"] == "യോഹന്നാൻ 2:1-12" and "മത്താ 12:46-50" in aug[3]["longer"]


def test_every_reading_of_the_published_years_has_a_malayalam_reference():
    for y in ("2025", "2026"):
        for iso, d in load("days-ml/%s.json" % y)["days"].items():
            for c in d["celebrations"]:
                for r in c["readings"]:
                    assert r.get("ref"), (iso, "a Bible book has no Malayalam name - add it to data/books.json")


def test_a_label_is_never_half_english():
    latin = re.compile("[A-Za-z]")
    for y in ("2025", "2026"):
        for iso, d in load("days-ml/%s.json" % y)["days"].items():
            for c in d["celebrations"]:
                if "label" in c:
                    assert not latin.search(c["label"]), (iso, c["label"])


def test_the_checker_catches_a_changed_verse(tmp_path):
    import shutil
    root = tmp_path / "r"
    shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".pytest_cache"))
    p = root / "days-ml" / "2026.json"
    t = p.read_text(encoding="utf-8").replace("യോഹ 3:22-30", "യോഹ 3:22-31", 1)
    p.write_text(t, encoding="utf-8")
    assert any("verses differ" in x for x in MB.ml_problems(str(root)))
