#!/usr/bin/env python3
"""
Builds the Malayalam layer  days-ml/<year>.json  from the English day files and data/ (books.json, glossary-ml.json).

No network, no translation by guesswork: every Malayalam string comes from a table a person proofread (books, seasons,
feast names, day-label words).  Anything that cannot be said in Malayalam is simply left out - apps then show the English.

Record for a date (same dates as days/<year>.json; celebrations and readings keep the SAME ORDER as the English day):
    {"season": "...",                       Malayalam season name (also in index.json "seasons")
     "celebrations": [{"label": "...", "partial": true?,        label missing => no Malayalam for it
                       "readings": [{"ref": "യോഹ 3:22-30", "main": "...", "longer": "...", "full": "യോഹന്നാൻ 3:22-30"}]}],
     "feasts": [{"title": "..."}]}          same order as the English "feasts"; a missing title is null
"ref"/"main"/"longer" use the short book names the Syro-Malabar Liturgy Commission prints (യോഹ, ശ്ലീഹ ...); "full" uses
the full names (യോഹന്നാൻ, അപ്പസ്തോലപ്രവർത്തനങ്ങൾ ...).  A reading whose book is not in the table has {} (use English).
The reading TITLES (the one-line headings) are not part of this layer.
"""
import json, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ml as ML


def _dump_year(year, days):
    lines = ['{"year":%d,"days":{' % year]
    items = sorted(days.items())
    for i, (iso, d) in enumerate(items):
        lines.append("%s:%s%s" % (json.dumps(iso), json.dumps(d, ensure_ascii=False, separators=(",", ":")), "," if i < len(items) - 1 else ""))
    lines.append("}}")
    return "\n".join(lines) + "\n"


def ml_day(day, gloss, books):
    out = {"season": gloss["seasons"].get(day["season"])}
    if not out["season"]:
        del out["season"]
    cels = []
    for c in day["celebrations"]:
        label, partial = ML.label_ml(c["label"], gloss)
        o = {}
        if label:
            o["label"] = label
            if partial:
                o["partial"] = True
        reads = []
        for r in c["readings"]:
            x = {}
            short = ML.ref_ml(r["ref"], books)
            if short:
                x["ref"] = short
                x["main"] = ML.ref_ml(r["main"], books)
                if r.get("longer"):
                    x["longer"] = ML.ref_ml(r["longer"], books)
                x["full"] = ML.ref_ml(r["main"], books, abbr=False)
            reads.append(x)
        o["readings"] = reads
        cels.append(o)
    out["celebrations"] = cels
    if day.get("feasts"):
        out["feasts"] = [({"title": ML.feast_ml(f["title"], gloss)} if ML.feast_ml(f["title"], gloss) else {"title": None}) for f in day["feasts"]]
    return out


def build_ml(root, log=print):
    """Writes days-ml/*.json for every year in days/.  Returns (changed, stats)."""
    gloss = json.load(open(os.path.join(root, "data", "glossary-ml.json"), encoding="utf-8"))
    books = json.load(open(os.path.join(root, "data", "books.json"), encoding="utf-8"))
    out_dir = os.path.join(root, "days-ml")
    os.makedirs(out_dir, exist_ok=True)
    changed, years = False, collections.OrderedDict()
    st = collections.Counter()
    for f in sorted(os.listdir(os.path.join(root, "days"))):
        if not (f.endswith(".json") and f[:-5].isdigit()):
            continue
        y = int(f[:-5])
        eng = json.load(open(os.path.join(root, "days", f), encoding="utf-8"))["days"]
        ml_days = {iso: ml_day(d, gloss, books) for iso, d in eng.items()}
        for iso, d in ml_days.items():
            for c in d["celebrations"]:
                st["labels"] += 1
                st["labels_ml"] += "label" in c and not c.get("partial")
                st["labels_partial"] += bool(c.get("partial"))
                for r in c["readings"]:
                    st["readings"] += 1
                    st["readings_ml"] += bool(r)
        text = _dump_year(y, ml_days)
        path = os.path.join(out_dir, "%d.json" % y)
        if not os.path.exists(path) or open(path, encoding="utf-8").read() != text:
            open(path, "w", encoding="utf-8", newline="\n").write(text)
            changed = True
        years[str(y)] = {"file": "days-ml/%d.json" % y, "days": len(ml_days)}
    for f in os.listdir(out_dir):                          # a year that no longer exists
        if f.endswith(".json") and f[:-5].isdigit() and "%s" % f[:-5] not in years:
            os.remove(os.path.join(out_dir, f)); changed = True
    log("Malayalam layer: %d year file(s); readings %d/%d, labels %d/%d (+%d partial)"
        % (len(years), st["readings_ml"], st["readings"], st["labels_ml"], st["labels"], st["labels_partial"]))
    return changed, years, dict(st)


def ml_problems(root, limit=40):
    """Checks on days-ml/*.json used by tools/checks.py: same dates and shape as the English files, verses copied
    exactly, no old-style (ZWJ/ZWNJ) letters, Malayalam strings really contain Malayalam."""
    probs = []
    skel = lambda s: re.sub(r"[^\d:,+\-\u2013()]", "", s)
    mal = re.compile("[\u0d00-\u0d7f]")
    ddir = os.path.join(root, "days-ml")
    if not os.path.isdir(ddir):
        return ["days-ml/ is missing"]
    for f in sorted(os.listdir(os.path.join(root, "days"))):
        if not (f.endswith(".json") and f[:-5].isdigit()):
            continue
        p = os.path.join(ddir, f)
        if not os.path.exists(p):
            probs.append("days-ml/%s is missing" % f); continue
        eng = json.load(open(os.path.join(root, "days", f), encoding="utf-8"))["days"]
        mld = json.load(open(p, encoding="utf-8"))["days"]
        if set(eng) != set(mld):
            probs.append("days-ml/%s: dates differ from days/%s" % (f, f)); continue
        for iso, d in eng.items():
            m = mld[iso]
            if len(m["celebrations"]) != len(d["celebrations"]):
                probs.append("%s: Malayalam has a different number of celebrations" % iso); continue
            for c, mc in zip(d["celebrations"], m["celebrations"]):
                if len(c["readings"]) != len(mc["readings"]):
                    probs.append("%s: Malayalam has a different number of readings" % iso); continue
                if "label" in mc and not mal.search(mc["label"]):
                    probs.append("%s: label without Malayalam letters %r" % (iso, mc["label"][:30]))
                for r, mr in zip(c["readings"], mc["readings"]):
                    for k in ("ref", "main", "longer", "full"):
                        if k in mr:
                            src = r["ref"] if k == "ref" else (r["main"] if k in ("main", "full") else r.get("longer", ""))
                            if skel(mr[k]) != skel(src):
                                probs.append("%s: verses differ in %s %r vs %r" % (iso, k, mr[k], src))
                            if k != "longer" and not mal.search(mr[k]):          # "longer" is just verses (no book name)
                                probs.append("%s: %s without Malayalam letters %r" % (iso, k, mr[k]))
    for f in os.listdir(ddir):
        t = open(os.path.join(ddir, f), encoding="utf-8").read()
        if "\u200d" in t or "\u200c" in t:
            probs.append("days-ml/%s contains old-style (ZWJ/ZWNJ) characters" % f)
    return probs[:limit]


if __name__ == "__main__":
    root = os.path.abspath(os.path.join(HERE, ".."))
    build_ml(root)
    for p in ml_problems(root):
        print("  problem:", p)
