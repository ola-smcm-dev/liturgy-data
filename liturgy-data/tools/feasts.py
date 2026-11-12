"""
Feast days for any year, from data/feast-rules.json  (fixed dates "MM-DD" or a movable rule, see calendar_rules.py).
"""
import json, os, re, datetime as dt
from calendar_rules import resolve_rule, _norm

HERE = os.path.dirname(os.path.abspath(__file__))


def load_rules(path=None):
    path = path or os.path.join(HERE, "..", "data", "feast-rules.json")
    return json.load(open(path, encoding="utf-8"))["rules"]


def feasts_for_year(rules, year):
    """{ 'YYYY-MM-DD': [ {title, type, obligation} ] } - merged like the website does: a Day of Obligation row
    absorbs the major-feast rows of the same date; saints' days that merely share the date stay."""
    by = {}
    for row in rules:
        dates = []
        fixed = row.get("date")
        if fixed:
            m, d = (int(x) for x in fixed.split("-"))
            try:
                dates = [dt.date(year, m, d)]
            except ValueError:
                dates = []                                          # 29 Feb in a normal year
        else:
            r = resolve_rule(row["rule"], row["title"], year)
            dates = [r] if r else []
        for d in dates:
            by.setdefault(d.isoformat(), []).append(row)
    out = {}
    for key in sorted(by):
        lst, kept, seen = by[key], [], set()
        ob = next((r for r in lst if re.search("obligation", r["type"], re.I)), None)
        if ob:
            kept.append(ob); seen.add(_norm(ob["title"]))
            for r in lst:
                n = _norm(r["title"])
                if r is ob or n in seen or re.search(r"our lord|marian|important", r["type"], re.I):
                    continue
                seen.add(n); kept.append(r)
        else:
            for r in lst:
                n = _norm(r["title"])
                if n not in seen:
                    seen.add(n); kept.append(r)
        out[key] = [{"title": re.sub(r"\s+", " ", r["title"]).strip(), "type": r["type"],
                     "obligation": bool(re.search("obligation", r["type"], re.I))} for r in kept]
    return out
