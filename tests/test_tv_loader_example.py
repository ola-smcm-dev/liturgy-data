import datetime as dt, json, os, shutil, sys
from conftest import ROOT
sys.path.insert(0, os.path.join(ROOT, "examples"))
import tv_loader as T


def fake_fetch_from_repo(url, timeout=0):
    rel = url.replace(T.BASE_URL, "")
    return json.load(open(os.path.join(ROOT, rel), encoding="utf-8"))


def dead_network(url, timeout=0):
    raise OSError("no internet")


def test_one_fetch_then_saved_locally_then_works_offline(tmp_path):
    cache = str(tmp_path / "cache")
    today = dt.date(2026, 11, 20)
    d1 = T.load(cache, today=today, fetch=fake_fetch_from_repo)
    assert d1.source == "network" and d1.day(today)["celebrations"]
    d2 = T.load(cache, today=today, fetch=dead_network)                 # next start-up, no internet
    assert d2.source == "cache" and d2.day(today) == d1.day(today)


def test_seed_copy_is_the_last_resort(tmp_path):
    seed = tmp_path / "seed"
    shutil.copytree(os.path.join(ROOT, "days"), seed / "days")
    shutil.copy(os.path.join(ROOT, "index.json"), seed / "index.json")
    shutil.copytree(os.path.join(ROOT, "data"), seed / "data")
    d = T.load(str(tmp_path / "cache"), seed_dir=str(seed), today=dt.date(2026, 6, 1), fetch=dead_network)
    assert d.source == "seed" and d.day(dt.date(2026, 6, 1))


def test_out_of_date_data_is_reported_not_guessed(tmp_path):
    d = T.load(str(tmp_path / "c"), today=dt.date(2026, 11, 20), fetch=fake_fetch_from_repo)
    assert d.day(dt.date(2028, 1, 1)) is None


def test_nothing_anywhere_raises(tmp_path):
    import pytest
    with pytest.raises(RuntimeError):
        T.load(str(tmp_path / "c"), fetch=dead_network)


def test_readings_come_out_with_full_book_names(tmp_path):
    today = dt.date(2026, 8, 15)
    d = T.load(str(tmp_path / "c"), today=today, fetch=fake_fetch_from_repo)
    texts = [d.reading_text(r) for c in d.day(today)["celebrations"] for r in c["readings"]]
    assert texts == ["Exodus 15:11-18", "Acts of the Apostles 1:6-14", "Romans 16:17-27", "John 2:1-12"], texts
    gospel = {"main": "Mt 25:14-30"}
    assert d.reading_text(gospel) == "Matthew 25:14-30"
    assert d.reading_text(gospel, "ml").startswith("മത്തായി")
    # and the same from the saved copy with no internet
    d2 = T.load(str(tmp_path / "c"), today=today, fetch=dead_network)
    assert d2.source == "cache" and d2.reading_text(gospel) == "Matthew 25:14-30"
