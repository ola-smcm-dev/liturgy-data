"""
Date rules of the Syro-Malabar liturgical year: Easter, the eight seasons and the movable feasts.
Pure functions, no network, no PDF - this is the part that keeps working in a year whose
Panchangam could not be read.  (Ported from the church website's FEAST DAYS code in js/main.js
and checked against it in tests/test_feasts.py.)
"""
import datetime as dt
import re

D = dt.date
ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7}
DOW = {"sunday": 6, "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5}   # python weekday()
OFFSET = {"sunday": 0, "monday": 1, "tuesday": 2, "wednesday": 3, "thursday": 4, "friday": 5, "saturday": 6}   # days after a Sunday


def easter(y):
    """Western Easter Sunday (anonymous Gregorian algorithm)."""
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return D(y, month, day)


def on_or_after(y, month, day, weekday):
    d = D(y, month, day)
    while d.weekday() != weekday:
        d += dt.timedelta(days=1)
    return d


def add(d, n):
    return d + dt.timedelta(days=n)


def annunciation_start(y):
    """First Sunday of the Annunciation (Suvara) season: the Sunday on or after 27 November of year y."""
    return on_or_after(y, 11, 27, 6)


# ---- seasons --------------------------------------------------------------------------------
SEASONS = [   # key, English name
    ("annunciation", "Annunciation (Suvara)"),
    ("nativity", "Nativity (Yalda)"),
    ("epiphany", "Epiphany (Denha)"),
    ("great-fast", "Great Fast (Sauma Ramba)"),
    ("resurrection", "Resurrection (Qyamtha)"),
    ("apostles", "Apostles (Sleehe)"),
    ("kaitha", "Summer (Kaitha)"),
    ("elijah-cross-moses", "Elijah-Cross-Moses"),
    ("dedication", "Dedication of the Church (Qudash Edtha)"),
]
SEASON_NAMES = dict(SEASONS)


def season_starts(y):
    """[(start_date, key)] for the liturgical year whose Easter falls in year y, plus the Annunciation / Nativity
    seasons at its two ends (the Annunciation of y-1 and of y)."""
    e = easter(y)
    return [
        (annunciation_start(y - 1), "annunciation"),
        (D(y - 1, 12, 25), "nativity"),
        (D(y, 1, 6), "epiphany"),
        (add(e, -49), "great-fast"),            # starts on Pethrutha Sunday (checked against the 2024-25 and 2025-26 booklets)
        (e, "resurrection"),
        (add(e, 49), "apostles"),               # Pentecost
        (add(e, 98), "kaitha"),
        (add(e, 147), "elijah-cross-moses"),     # NOTE: the booklets sometimes start it a week earlier (2025: 7 Sep, not 14 Sep) - the printed banner wins, see build.py
        (add(annunciation_start(y), -28), "dedication"),
    ]


def season_of(d):
    """Season key for a date."""
    for y in (d.year, d.year + 1):          # Dec dates belong to the next year's list
        starts = season_starts(y)
        if starts[0][0] <= d < add(annunciation_start(y), 0):
            key = None
            for s, k in starts:
                if s <= d:
                    key = k
            return key
    raise ValueError("no season for %s" % d)


# ---- feast rules ("Sixth Thursday after Easter", "Third Friday of Apostles", ...) ---------------
def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def resolve_rule(rule, title, year):
    """Turn a movable-feast rule into a date for `year`; None when the rule is not understood."""
    r = re.sub(r"\s+", " ", rule or "").strip()
    r = re.split(r"\s+or\s+", r, flags=re.I)[0]
    r = re.sub(r"[:;,.\s]+$", "", r)
    low = r.lower()
    e = easter(year)
    if low == "changes every year":
        t = _norm(title)
        if t in ("easter", "eastersunday", "resurrection"):
            return e
        if t == "palmsunday":
            return add(e, -7)
        if t in ("pesahathursday", "maundythursday"):
            return add(e, -3)
        if t in ("passionfriday", "goodfriday"):
            return add(e, -2)
        return None
    if low == "fifty days after easter":
        return add(e, 49)
    m = re.match(r"^(first|second|third|fourth|fifth|sixth|seventh) (sunday|monday|tuesday|wednesday|thursday|friday|saturday) after easter$", low)
    if m:
        return add(e, 7 * (ORD[m.group(1)] - 1) + (OFFSET[m.group(2)] or 7))
    m = re.match(r"^(sunday|monday|tuesday|wednesday|thursday|friday|saturday) after pentecost$", low)
    if m:
        return add(e, 49 + (OFFSET[m.group(1)] or 7))
    m = re.match(r"^last friday of (?:the )?(denha|nativity)$", low)
    if m:
        if m.group(1) == "denha":
            return add(e, -49 - 2)
        d = D(year, 1, 5)
        while d.weekday() != 4:
            d = add(d, -1)
        return d
    m = re.match(r"^(first|second|third|fourth|fifth|sixth|seventh) (sunday|monday|tuesday|wednesday|thursday|friday|saturday) of (?:the )?"
                 r"(denha|resurrection|apostles|kaitha|nativity|dedication of the church)$", low)
    if m:
        n, dow, season = ORD[m.group(1)], m.group(2), m.group(3)
        if season == "denha":
            if dow != "friday":
                return None
            return add(on_or_after(year, 1, 6, 4), 7 * (n - 1))
        if season == "resurrection":
            start = e
        elif season == "apostles":
            start = add(e, 49)
        elif season == "kaitha":
            start = add(e, 98)
        elif season == "nativity":
            start = on_or_after(year, 12, 26, 6)
        else:
            start = add(on_or_after(year, 11, 27, 6), -28)
        return add(start, 7 * (n - 1) + OFFSET[dow])
    return None
