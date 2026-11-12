import json, os, re
import refs as R
from conftest import ROOT


def test_the_examples_from_the_booklet():
    assert R.tidy("Gen 21: 9-21 (21: 1-21)") == "Gen 21:9-21 (21:1-21)"
    assert R.tidy("1Cor 15:39-49 (15:34-57)") == "1 Cor 15:39-49 (15:34-57)"
    assert R.tidy("Is.11:1-12") == "Isa 11:1-12"
    assert R.tidy("Acts1:12-14(1:1-14)") == "Acts 1:12-14 (1:1-14)"
    assert R.tidy("Duet 9:1-6 (9:1-8)") == "Deut 9:1-6 (9:1-8)"
    assert R.tidy("Mt1:1-16, 18-25") == "Mt 1:1-16, 18-25"
    assert R.tidy("Lk 22:63-23:12+Mt 27:19+Lk22:13-23") == "Lk 22:63-23:12 + Mt 27:19 + Lk 22:13-23"


def test_main_and_longer():
    assert R.split("Gen 21:9-21 (21:1-21)") == ("Gen 21:9-21", "21:1-21")
    assert R.split("Phil 2:5-11 (Gal 5:1-6 + Phil 2:5-11)") == ("Phil 2:5-11", "Gal 5:1-6 + Phil 2:5-11")
    assert R.split("Mt 1:18-25 + Lk 2:21") == ("Mt 1:18-25 + Lk 2:21", "")


def test_expand_gives_full_names_including_the_gospels():
    assert R.expand("Gen 21:9-21") == "Genesis 21:9-21"
    assert R.expand("Mt 25:14-30") == "Matthew 25:14-30"
    assert R.expand("Jn 2:1-12 + Mt 12:46-50") == "John 2:1-12 + Matthew 12:46-50"
    assert R.expand("1 Cor 15:39-49") == "1 Corinthians 15:39-49"
    assert R.expand("Mt 25:14-30", lang="ml").startswith("മത്തായി")


def test_the_gospels_have_full_english_names_in_books_json():
    names = {b["abbr"]: b["en"] for b in R.load_books()}
    assert (names["Mt"], names["Mk"], names["Lk"], names["Jn"]) == ("Matthew", "Mark", "Luke", "John")


def test_tidying_never_changes_a_verse_number():
    """Only spaces, punctuation and the spelling of the book name may change: the digits stay identical."""
    raw = {}
    for f in ("2024-2025", "2025-2026"):
        for d in json.load(open(os.path.join(ROOT, "sources", f + ".json"), encoding="utf-8")).values():
            for g in d["groups"]:
                for r in g["readings"]:
                    raw[r["ref"]] = R.tidy(r["ref"])
    assert len(raw) > 1000
    for a, b in raw.items():
        assert re.sub(r"\D", "", a) == re.sub(r"\D", "", b), (a, b)


def test_every_published_reference_is_tidy_and_every_book_is_known():
    books = {b["abbr"] for b in R.load_books()}
    n = 0
    for y in os.listdir(os.path.join(ROOT, "days")):
        for iso, d in json.load(open(os.path.join(ROOT, "days", y), encoding="utf-8"))["days"].items():
            for c in d["celebrations"]:
                for r in c["readings"]:
                    n += 1
                    for k in ("ref", "main", "longer"):
                        v = r.get(k, "")
                        assert ": " not in v and "  " not in v and "( " not in v and " )" not in v, (iso, k, v)
                    assert r["ref"] == r["main"] + (" (%s)" % r["longer"] if r.get("longer") else ""), (iso, r)
                    # every book name written in the reference is a standard abbreviation
                    for m in re.finditer(r"(?<![A-Za-z0-9])((?:[1-3] )?[A-Z][a-z]+)(?= \d)", r["ref"]):
                        assert m.group(1) in books, (iso, r["ref"], m.group(1))
    assert n > 2000
