#!/usr/bin/env python3
"""
Checks a parsed Panchangam (JSON from panchangam_parser.py) before anything is published.
Returns (errors, warnings, review_dates):
  errors        -> something is structurally wrong; do NOT publish the file
  review_dates  -> dates that look suspicious; publish everything else and show a link-out for these
  warnings      -> informational (PDF typos, Good Friday style alternates ...)
"""
import re, sys, json, datetime, collections, os

HERE = os.path.dirname(os.path.abspath(__file__))
KNOWN = set(open(os.path.join(HERE, "known_books.txt")).read().split())
BOOK_TOKEN = re.compile(r"(?:^|\+\s?|\(\s?)((?:[1-3]\s?)?[A-Z][A-Za-z]{0,11})\.?\s?\d")


def book_key(tok):
    return re.sub(r"[\s.]", "", tok.lower())


def validate(days, expect_first=None, expect_last=None):
    errors, warnings, review = [], [], collections.OrderedDict()

    def flag(d, why):
        review.setdefault(d, []).append(why)

    dates = sorted(days)
    if not dates:
        return ["no days parsed"], warnings, review
    # 1. continuity
    d0, d1 = datetime.date.fromisoformat(dates[0]), datetime.date.fromisoformat(dates[-1])
    n_expected = (d1 - d0).days + 1
    if n_expected != len(dates):
        missing = [(d0 + datetime.timedelta(days=i)).isoformat() for i in range(n_expected)
                   if (d0 + datetime.timedelta(days=i)).isoformat() not in days]
        errors.append("%d date(s) missing between %s and %s: %s" % (len(missing), dates[0], dates[-1], missing[:10]))
    if expect_first and dates[0] > expect_first:
        errors.append("first date %s is later than expected %s" % (dates[0], expect_first))
    if expect_last and dates[-1] < expect_last:
        errors.append("last date %s is earlier than expected %s" % (dates[-1], expect_last))
    with_readings = sum(1 for d in dates if any(g["readings"] for g in days[d]["groups"]))
    if with_readings < 0.97 * len(dates):
        errors.append("only %d of %d days have any reading - the layout probably changed" % (with_readings, len(dates)))
    if len(dates) < 330:
        errors.append("only %d days found (a liturgical year has about 365)" % len(dates))

    for d in dates:
        e = days[d]
        groups = e["groups"]
        if not groups:
            flag(d, "no celebration found"); continue
        wd = datetime.date.fromisoformat(d).weekday()      # 6 = Sunday
        for gi, g in enumerate(groups):
            rd = g["readings"]
            label = g["label"]
            n = len(rd)
            if not label.strip():
                flag(d, "group %d has no label" % (gi + 1))
            if n == 0:
                flag(d, "group %r has no readings" % label[:40]); continue
            same_as = bool(re.search(r"\bsame\b.{0,20}\bEaster\b", " ".join(g.get("notes", []))))
            if n % 2 == 1 and not (g.get("alternate") or any(x.get("alternate") for x in groups)) \
                    and not re.search(r"Passion Friday", label) and not same_as:
                flag(d, "odd number of readings (%d) in %r" % (n, label[:40]))
            if n > 8:
                flag(d, "too many readings (%d) in %r" % (n, label[:40]))
            if gi == 0 and wd == 6 and n not in (4,):
                flag(d, "Sunday with %d readings" % n)
            for r in rd:
                ref, title = r["ref"], r["title"]
                if not title.strip():
                    flag(d, "reading %r has no title" % ref)
                if len(title) > 160:
                    flag(d, "very long title (%d chars) for %r" % (len(title), ref))
                if re.match(r"^[\d\-–+,;(]", title):
                    flag(d, "title starts oddly for %r: %r" % (ref, title[:30]))
                if re.search(r"\d+\s?:\s?\d+", title):
                    flag(d, "scripture-like text inside the title of %r: %r" % (ref, title[:60]))
                m = re.match(r"((?:[1-3]\s?)?[A-Z][A-Za-z]{0,11})\.?\s?\d", ref)
                if not m or book_key(m.group(1)) not in KNOWN:
                    warnings.append("%s: unknown book abbreviation in %r (shown as printed)" % (d, ref))
                for tok in BOOK_TOKEN.findall(ref)[1:]:
                    if book_key(tok) not in KNOWN:
                        warnings.append("%s: unknown book %r inside %r (shown as printed)" % (d, tok, ref))
    # 2. reading refs repeated across very different days is normal; nothing to check.
    return errors, warnings, review


if __name__ == "__main__":
    days = json.load(open(sys.argv[1], encoding="utf-8"))
    errors, warnings, review = validate(days)
    print("errors:", errors)
    print("dates to review: %d" % len(review))
    for d, why in review.items():
        print(" ", d, "|", "; ".join(why))
