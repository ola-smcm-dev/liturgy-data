"""
Loader for the Qurbana TV / projector app (or any Python program).  Copy this file into that project.

What it does, in order:
  1. At start-up, ONE fetch of index.json + the year file(s) it needs from GitHub Pages.
  2. Saves them in a local folder (cache_dir) - later start-ups with no internet still work.
  3. If the fetch fails and there is no saved copy, falls back to a "seed" copy that ships with the app
     (copy this repo's index.json and days/ into e.g. app/seed/).
  4. Tells you whether the data actually covers today, so the screen can show "readings out of date"
     instead of a wrong reading.

    data = load(cache_dir="cache", seed_dir="seed")
    day = data.day(date.today())          # None when today is not covered
    data.stale                            # True -> show the small "out of date" note
    data.feasts_between(start, end)       # [(date, title, obligation), ...] for "this week"
Everything shown on screen should be treated as plain text (never as HTML).
"""
import datetime as dt
import json
import os
import urllib.request

BASE_URL = "https://ola-smcm-dev.github.io/liturgy-data/"


class Data:
    def __init__(self, index, years, source):
        self.index, self.years, self.source = index, years, source          # source: "network" | "cache" | "seed"

    def day(self, d):
        y = self.years.get(d.year)
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
    return Data(index, years, "")


def load(cache_dir, seed_dir=None, base_url=BASE_URL, today=None, fetch=_get):
    today = today or dt.date.today()
    try:                                                      # 1 + 2: the one fetch, then save locally
        index = fetch(base_url + "index.json")
        years = {}
        for y in _years_needed(index, today):
            years[y] = fetch(base_url + index["years"][str(y)]["file"])["days"]
        _write(os.path.join(cache_dir, "index.json"), index)
        for y, days in years.items():
            _write(os.path.join(cache_dir, "days", "%d.json" % y), {"year": y, "days": days})
        return Data(index, years, "network")
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
