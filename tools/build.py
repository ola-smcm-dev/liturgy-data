#!/usr/bin/env python3
"""
Builds the published files from the parsed Panchangam booklets in sources/:

    days/<year>.json   one file per calendar year, one record per date:
                       weekday, season, celebrations (label/notes/readings), feasts, obligation, check
    index.json         which years exist, coverage, booklets used, dates needing a human look
    reports/untranslated-celebrations.txt   celebration names that have no Malayalam yet (a to-do list)

Deterministic: the same inputs always give byte-identical files (so a run that changes nothing makes no commit).

Usage:  python3 tools/build.py            (run from the repo root)
"""
import json, os, re, sys, datetime as dt, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import calendar_rules as CR
import feasts as FE
import validate as VA

SCHEMA = 1
COMMISSION_PAGE = "https://www.syromalabarliturgy.org/liturgical_texts"


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def booklet_sort_key(b):
    return b["id"]            # "2024-2025" < "2025-2026": a later booklet wins where two overlap


def season_for(iso, banner):
    rule = CR.season_of(dt.date.fromisoformat(iso))
    if banner and banner != "annunciation+nativity" and banner in CR.SEASON_NAMES:
        return banner, (None if banner == rule else rule)
    return rule, None


def make_day(iso, raw, feast_map, check_reasons):
    season, rule_season = season_for(iso, raw.get("banner"))
    day = {"weekday": raw["weekday"], "season": season}
    cel = []
    pdf_obligation = False
    for g in raw["groups"]:
        c = {"label": g["label"]}
        if g.get("notes"):
            c["notes"] = g["notes"]
        if g.get("alternate"):
            c["alternate"] = True
        c["readings"] = [{"ref": r["ref"], "title": r["title"]} for r in g["readings"]]
        cel.append(c)
        if re.search(r"obligation", " ".join(g.get("notes", [])) + " " + g["label"], re.I):
            pdf_obligation = True
    day["celebrations"] = cel
    fl = feast_map.get(iso, [])
    if fl:
        # the booklet is the authority on days of obligation (it moves them, e.g. St Peter & Paul when 29 June is a Sunday)
        day["feasts"] = [({"title": f["title"], "obligation": True} if (f["obligation"] and pdf_obligation) else {"title": f["title"]}) for f in fl]
    rule_obligation = any(f["obligation"] for f in fl)
    if pdf_obligation:
        day["obligation"] = True
    if check_reasons:
        day["check"] = True
    return day, season_disagreement(iso, season, rule_season), pdf_obligation, rule_obligation


def season_disagreement(iso, season, rule_season):
    return "%s: printed season %s, calendar rule says %s" % (iso, season, rule_season) if rule_season else None


def build(root=ROOT, today=None, log=print):
    today = today or dt.date.today().isoformat()
    reg = load_json(os.path.join(root, "sources", "booklets.json"))["booklets"]
    reg = sorted(reg, key=booklet_sort_key)
    rules = FE.load_rules(os.path.join(root, "data", "feast-rules.json"))
    gloss = load_json(os.path.join(root, "data", "glossary-ml.json"))
    feast_cache = {}
    merged, origin, review, warnings = {}, {}, collections.OrderedDict(), []
    for b in reg:
        raw = load_json(os.path.join(root, b["parsed"]))
        errors, vwarn, rev = VA.validate({k: v for k, v in raw.items()})
        if errors:
            raise SystemExit("booklet %s fails validation, refusing to build: %s" % (b["id"], errors))
        for iso, d in raw.items():
            y = int(iso[:4])
            if y not in feast_cache:
                feast_cache[y] = FE.feasts_for_year(rules, y)
            day, sd, pdf_ob, rule_ob = make_day(iso, d, feast_cache[y], rev.get(iso))
            merged[iso] = day
            origin[iso] = b["id"]
            for k in [k for k in review if k == iso]:
                del review[k]
            if rev.get(iso):
                review[iso] = rev[iso]
            if sd:
                warnings.append(sd)
            if pdf_ob != rule_ob:
                warnings.append("%s: day of obligation — Panchangam says %s, feast-rules.json says %s" % (iso, pdf_ob, rule_ob))
        warnings.extend("%s: %s" % (b["id"], w) for w in vwarn[:50])
    if not merged:
        raise SystemExit("no booklets registered in sources/booklets.json")
    all_dates = sorted(merged)
    d0, d1 = dt.date.fromisoformat(all_dates[0]), dt.date.fromisoformat(all_dates[-1])
    if (d1 - d0).days + 1 != len(all_dates):
        gaps = [(d0 + dt.timedelta(days=i)).isoformat() for i in range((d1 - d0).days + 1)
                if (d0 + dt.timedelta(days=i)).isoformat() not in merged]
        raise SystemExit("the booklets leave a gap in the calendar (%d day(s), first: %s) - refusing to build" % (len(gaps), gaps[:3]))
    # ---- write the per-year files ----
    out_days = os.path.join(root, "days")
    os.makedirs(out_days, exist_ok=True)
    years = collections.OrderedDict()
    by_year = collections.defaultdict(dict)
    for iso in sorted(merged):
        by_year[int(iso[:4])][iso] = merged[iso]
    changed = False
    for y in sorted(by_year):
        lines = ['{"year":%d,"days":{' % y]
        items = sorted(by_year[y].items())
        for i, (iso, day) in enumerate(items):
            lines.append('%s:%s%s' % (json.dumps(iso), json.dumps(day, ensure_ascii=False, separators=(",", ":")), "," if i < len(items) - 1 else ""))
        lines.append("}}")
        text = "\n".join(lines) + "\n"
        path = os.path.join(out_days, "%d.json" % y)
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if old != text:
            open(path, "w", encoding="utf-8", newline="\n").write(text)
            changed = True
        years[str(y)] = {"file": "days/%d.json" % y, "first": items[0][0], "last": items[-1][0], "days": len(items)}
    for f in os.listdir(out_days):                       # a year that no longer has data
        if f.endswith(".json") and f[:-5].isdigit() and int(f[:-5]) not in by_year:
            os.remove(os.path.join(out_days, f)); changed = True
    # ---- index.json ----
    idx_path = os.path.join(root, "index.json")
    old_idx = load_json(idx_path) if os.path.exists(idx_path) else {}
    index = collections.OrderedDict()
    index["schema"] = SCHEMA
    index["updated"] = old_idx.get("updated", today)
    first, last = min(merged), max(merged)
    index["coverage"] = {"first": first, "last": last}
    index["years"] = years
    index["booklets"] = [{"id": b["id"], "first": min(k for k, v in origin.items() if v == b["id"]) if b["id"] in origin.values() else None,
                          "last": max(k for k, v in origin.items() if v == b["id"]) if b["id"] in origin.values() else None,
                          "source": b.get("source_url", "")} for b in reg]
    index["seasons"] = {k: {"en": n, "ml": gloss["seasons"].get(k, "")} for k, n in CR.SEASONS}
    index["datesToCheck"] = {k: v for k, v in sorted(review.items())}
    index["commissionPage"] = COMMISSION_PAGE
    new_text = json.dumps(index, ensure_ascii=False, indent=1) + "\n"
    cmp_old = json.dumps({**old_idx, "updated": None}, ensure_ascii=False, indent=1) if old_idx else None
    cmp_new = json.dumps({**index, "updated": None}, ensure_ascii=False, indent=1)
    if changed or cmp_old != cmp_new:
        index["updated"] = today
        new_text = json.dumps(index, ensure_ascii=False, indent=1) + "\n"
        open(idx_path, "w", encoding="utf-8", newline="\n").write(new_text)
        changed = True
    # ---- Malayalam to-do list ----
    known = {re.sub(r"[^a-z0-9]", "", k.lower()) for k in gloss["celebrations"]}
    missing = collections.Counter()
    for day in merged.values():
        for c in day["celebrations"]:
            if re.sub(r"[^a-z0-9]", "", c["label"].lower()) not in known and not c.get("alternate"):
                missing[c["label"]] += 1
    os.makedirs(os.path.join(root, "reports"), exist_ok=True)
    rp = os.path.join(root, "reports", "untranslated-celebrations.txt")
    txt = "# Celebration names in the Panchangam with no Malayalam in data/glossary-ml.json yet (name <TAB> days seen)\n" + \
          "".join("%s\t%d\n" % (n, c) for n, c in sorted(missing.items()))
    if not os.path.exists(rp) or open(rp, encoding="utf-8").read() != txt:
        open(rp, "w", encoding="utf-8", newline="\n").write(txt)
        changed = True
    log("built %d days (%s .. %s), %d year file(s); %d date(s) to check; %d warning(s); %d names without Malayalam"
        % (len(merged), first, last, len(years), len(review), len(warnings), len(missing)))
    return dict(changed=changed, days=len(merged), first=first, last=last, review=dict(review), warnings=warnings)


if __name__ == "__main__":
    r = build()
    for w in r["warnings"][:30]:
        print("  warning:", w)
