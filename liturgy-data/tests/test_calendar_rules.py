import datetime as dt
import calendar_rules as C


def test_easter_known_dates():
    assert C.easter(2024) == dt.date(2024, 3, 31)
    assert C.easter(2025) == dt.date(2025, 4, 20)
    assert C.easter(2026) == dt.date(2026, 4, 5)
    assert C.easter(2027) == dt.date(2027, 3, 28)
    assert C.easter(2038) == dt.date(2038, 4, 25)


def test_rules_against_the_2026_booklet():
    assert C.resolve_rule("Sixth Thursday after Easter", "Ascension", 2026) == dt.date(2026, 5, 14)
    assert C.resolve_rule("Fifty Days after Easter", "Pentecost", 2026) == dt.date(2026, 5, 24)
    assert C.resolve_rule("Changes Every Year", "Palm Sunday", 2026) == dt.date(2026, 3, 29)
    assert C.resolve_rule("Changes Every Year", "Passion Friday", 2026) == dt.date(2026, 4, 3)
    assert C.resolve_rule("Fourth Sunday of Dedication of the Church", "Christ the King", 2026) == dt.date(2026, 11, 22)


def test_unknown_rule_is_none_not_a_crash():
    assert C.resolve_rule("Whenever the bishop says", "x", 2026) is None


def test_seasons_follow_the_printed_booklet():
    # dates taken from the printed banners of the 2025-26 booklet
    assert C.season_of(dt.date(2026, 2, 15)) == "great-fast"
    assert C.season_of(dt.date(2026, 2, 14)) == "epiphany"
    assert C.season_of(dt.date(2026, 4, 5)) == "resurrection"
    assert C.season_of(dt.date(2026, 5, 24)) == "apostles"
    assert C.season_of(dt.date(2026, 7, 12)) == "kaitha"
    assert C.season_of(dt.date(2026, 8, 30)) == "elijah-cross-moses"
    assert C.season_of(dt.date(2026, 11, 1)) == "dedication"
    assert C.season_of(dt.date(2026, 11, 29)) == "annunciation"
    assert C.season_of(dt.date(2026, 12, 25)) == "nativity"
    assert C.season_of(dt.date(2027, 1, 6)) == "epiphany"


def test_every_day_of_many_years_has_a_season():
    d = dt.date(2024, 1, 1)
    while d < dt.date(2040, 1, 1):
        assert C.season_of(d) in C.SEASON_NAMES
        d += dt.timedelta(days=1)
