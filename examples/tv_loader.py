"""
Loader for the Qurbana TV / projector app (or any Python program).  Copy this file into that project.

What it does, in order:
  1. At start-up, ONE fetch of index.json + the year file(s) it needs from GitHub Pages.
  2. Saves them in a local folder (cache_dir) - later start-ups with no internet still work.
  3. If the fetch fails and there is no saved copy, falls back to a "seed" copy that ships with the app
     (copy this repo's index.json, days/ and data/books.json into e.g. app/seed/).
  4. Tells you whether the data actually covers today, so the screen can show "readings out of date"
     instead of a wrong reading.

    data = load(cache_dir="cache", seed_dir="seed")
    day = data.day(date.today())          # None when today is not covered
    data.stale                            # True -> show the small "out of date" note
    data.feasts_between(start, end)       # [(date, title, obligation), ...] for "this week"
    data.reading_text(reading)            # "Genesis 21:9-21"  (full book name; the bracketed longer version is left out)
    data.reading_text(reading, "ml")      # same with the Malayalam book name
    data.ml_day(date.today())             # Malayalam labels / references for that day (see tools/ml_build.py), or None
Everything shown on screen should be treated as plain text (never as HTML).
"""
import datetime as dt
import json
import os
import re
import urllib.request

BASE_URL = "https://ola-smcm-dev.github.io/liturgy-data/"


_BOOK_RE = re.compile(r"(?<![A-Za-z0-9])((?:[1-3]\s?)?[A-Za-z]{2,})\.?\s*(?=\d)")


class Data:
    def __init__(self, index, years, source, books=None, ml_years=None):
        self.index, self.years, self.source = index, years, source          # source: "network" | "cache" | "seed"
        self.ml_years = ml_years or {}                                       # Malayalam layer (days-ml/); may be empty
        self.books = books or []
        self._alias = {}
        for b in self.books:
            self._alias[re.sub(r"[\s.]", "", b["abbr"].lower())] = b
            for a in b["aliases"]:
                self._alias[a] = b

    def reading_text(self, reading, lang="en"):
        """The reading as it is proclaimed, with full book names: {"main": "Gen 21:9-21", ...} -> "Genesis 21:9-21"."""
        def book(m):
            b = self._alias.get(re.sub(r"[\s.]", "", m.group(1).lower()))
            return ((b.get(lang) or b["en"]) + " ") if b else m.group(0)
        return _BOOK_RE.sub(book, reading.get("main") or reading.get("ref", ""))

    def day(self, d):
        y = self.years.get(d.year)
        return (y or {}).get(d.isoformat())

    def ml_day(self, d):
        """The Malayalam layer for a date: {"season", "celebrations": [{"label"?, "readings": [{"ref", "main", "longer"?, "full"}]}],
        "feasts"}, in the SAME order as day(d).  A missing label / empty reading dict means 'show the English'.  None when there is
        no Malayalam data at all.  Reading titles are not part of the Malayalam layer."""
        y = self.ml_years.get(d.year)
        return (y or {}).get(d.isoformat())

    @property
    def stale(self):
        return self.day(dt.date.today()) is None

    def season_name(self, key, lang="en"):
        return self.index["seasons"].get(key, {}).get(lang) or self.index["seasons"].get(key, {}).get("en", key)

    def feasts_between(self, start, end):
        out, d = [], start
        while d <= end:
            rec = self.day(d) or {}
            for f in rec.get("feasts", []):
                out.append((d, f["title"], bool(f.get("obligation"))))
            d += dt.timedelta(days=1)
        return out


def _read(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)                                     # never leaves a half-written file behind


def _get(url, timeout=15):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "ola-tv-app"}), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _years_needed(index, today):
    wanted = {today.year, (today + dt.timedelta(days=14)).year}
    return [y for y in sorted(wanted) if str(y) in index["years"]]


def _load_dir(folder, today):
    index = _read(os.path.join(folder, "index.json"))
    years = {}
    for y in _years_needed(index, today):
        years[y] = _read(os.path.join(folder, "days", "%d.json" % y))["days"]
    books_path = os.path.join(folder, "data", "books.json")
    books = _read(books_path)["books"] if os.path.exists(books_path) else []
    ml_years = {}
    for y in years:
        p = os.path.join(folder, "days-ml", "%d.json" % y)
        if os.path.exists(p):
            try:
                ml_years[y] = _read(p)["days"]
            except Exception:
                pass
    return Data(index, years, "", books, ml_years)


def load(cache_dir, seed_dir=None, base_url=BASE_URL, today=None, fetch=_get):
    today = today or dt.date.today()
    try:                                                      # 1 + 2: the one fetch, then save locally
        index = fetch(base_url + "index.json")
        books_doc = fetch(base_url + "data/books.json")
        years = {}
        for y in _years_needed(index, today):
            years[y] = fetch(base_url + index["years"][str(y)]["file"])["days"]
        ml_years = {}
        try:                                                  # the Malayalam layer is optional: never let it break the English data
            for y in years:
                info = (index.get("malayalam", {}).get("years", {}) or {}).get(str(y))
                if info:
                    ml_years[y] = fetch(base_url + info["file"])["days"]
        except Exception:
            ml_years = {}
        _write(os.path.join(cache_dir, "index.json"), index)
        for y, days in ml_years.items():
            _write(os.path.join(cache_dir, "days-ml", "%d.json" % y), {"year": y, "days": days})
        _write(os.path.join(cache_dir, "data", "books.json"), books_doc)
        for y, days in years.items():
            _write(os.path.join(cache_dir, "days", "%d.json" % y), {"year": y, "days": days})
        return Data(index, years, "network", books_doc["books"], ml_years)
    except Exception:
        pass
    for folder, label in ((cache_dir, "cache"), (seed_dir, "seed")):      # 3: saved copy, then the copy shipped with the app
        if folder and os.path.exists(os.path.join(folder, "index.json")):
            try:
                d = _load_dir(folder, today)
                d.source = label
                return d
            except Exception:
                continue
    raise RuntimeError("no liturgy data available: no network, no saved copy, no seed copy")
