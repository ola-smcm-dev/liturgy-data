"""
Checks on the PUBLISHED files (days/*.json, index.json) - the things apps rely on.
Used by the tests and, right after a rebuild, by tools/update.py: if anything fails there, the new data is rolled back
and people are alerted, so a problem never reaches the website or the TV app.
"""
import datetime as dt, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_BOOK_TOKEN = re.compile(r"(?<![A-Za-z0-9])((?:[1-3] )?[A-Z][a-z]+)(?= \d)")


def published_problems(root, limit=40):
    import calendar_rules as CR
    import refs as RF
    abbrs = {b["abbr"] for b in RF.load_books(os.path.join(root, "data", "books.json"))}
    idx = json.load(open(os.path.join(root, "index.json"), encoding="utf-8"))
    problems, days = [], {}
    for y, info in idx["years"].items():
        d = json.load(open(os.path.join(root, info["file"]), encoding="utf-8"))
        if d.get("year") != int(y):
            problems.append("%s: wrong year inside the file" % info["file"])
        days.update(d["days"])
    if days:
        first, last = dt.date.fromisoformat(min(days)), dt.date.fromisoformat(max(days))
        if (last - first).days + 1 != len(days):
            problems.append("the published days have a gap")
        if idx["coverage"] != {"first": min(days), "last": max(days)}:
            problems.append("index.json coverage does not match the day files")
    unknown_books = set()
    for iso, d in days.items():
        if d.get("season") not in CR.SEASON_NAMES:
            problems.append("%s: unknown season %r" % (iso, d.get("season")))
        if d.get("weekday") != WEEKDAYS[dt.date.fromisoformat(iso).weekday()]:
            problems.append("%s: wrong weekday" % iso)
        if not any(c["readings"] for c in d["celebrations"]):
            problems.append("%s: no readings" % iso)
        for c in d["celebrations"]:
            for s in [c["label"]] + c.get("notes", []):
                if "<" in s or ">" in s:
                    problems.append("%s: markup-like text in %r" % (iso, s[:40]))
            for r in c["readings"]:
                for k in ("ref", "main", "longer", "title"):
                    v = r.get(k, "")
                    if "<" in v or ">" in v:
                        problems.append("%s: markup-like text in %s %r" % (iso, k, v[:40]))
                for k in ("ref", "main", "longer"):
                    v = r.get(k, "")
                    if ": " in v or "  " in v or "( " in v or " )" in v:
                        problems.append("%s: untidy %s %r" % (iso, k, v))
                if r["ref"] != r["main"] + (" (%s)" % r["longer"] if r.get("longer") else ""):
                    problems.append("%s: ref/main/longer do not agree for %r" % (iso, r["ref"]))
                for m in _BOOK_TOKEN.finditer(r["ref"]):
                    if m.group(1) not in abbrs:
                        unknown_books.add(m.group(1))
    for b in sorted(unknown_books):
        problems.append("unknown Bible book %r - add its printed spelling to the 'aliases' of the right book in data/books.json" % b)
    import ml_build as MB
    problems += ["Malayalam layer: " + x for x in MB.ml_problems(root)]
    return problems[:limit]
