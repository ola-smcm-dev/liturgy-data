#!/usr/bin/env python3
"""
Syro-Malabar Liturgical Calendar (Panchangam, English PDF) -> structured daily readings.

Reads the PDF with pdfplumber and classifies every line by FONT and POSITION (not by guessing
from words), which is what makes it stable from year to year:
  * bold, left margin, "<day> <Mon..Sun> <label>"   -> a new date (first celebration of that day)
  * bold, large (size >= 14)                          -> month heading ("December 2025") / season banner
  * bold, indented                                    -> a further celebration on the same day (saint's feast ...)
  * italic, indented                                  -> note (anniversary, fasting notice ...)
  * regular, indented, starting with a Bible ref      -> a reading (ref + title); other regular lines continue the title
  * anything left of the indent that is not a day line (the season essays), page footers (small) -> ignored

Usage:  python3 panchangam_parser.py INPUT.pdf OUTPUT.json
"""
import re, sys, json, datetime, collections
import pdfplumber

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
PUA_RE = re.compile(r"[-​﻿]")
DAY_RE = re.compile(r"^(\d{1,2})\s+(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b\s*(.*)$")
MONTH_RE = re.compile(r"^(%s)\s*[-–]?\s*(\d{4})$" % "|".join(MONTHS))
INDENT_X = 80          # text indented further than this belongs to a day's entry
FOOTER_SIZE = 10       # smaller than this = page header/footer

# ---- Bible reference grammar -------------------------------------------------------------
_BOOK = r"(?:[1-3]\s?)?[A-Z][A-Za-z]{0,11}\.?"
_NUM = r"\d{1,3}"
_CV = r"%s\s?[:.]\s?%s[a-z]?" % (_NUM, _NUM)                       # 17:1
_PIECE = r"(?:%s|%s[a-z]?)" % (_CV, _NUM)                           # 17:1 | 5
_RANGE = r"%s(?:\s?[-–]\s?%s)?" % (_PIECE, _PIECE)                  # 17:1-5 | 7:28-8:3
_LIST = r"%s(?:\s?[,;]\s?%s)*" % (_RANGE, _RANGE)                   # 17:1-5, 15-19
_REF1 = r"%s\s?%s" % (_BOOK, _LIST)                                 # Gen 17:1-5, 15-19
_PAREN = r"\s?\([^()]*\)"                                           # (24:1-34)  (Mt 1:1-17 + Lk 1:46-55)
_PLUS = r"\s?\+\s?(?:%s\s?)?%s" % (_BOOK, _LIST)                    # + 2:16-18  | + Lk 2:21
REF_RE = re.compile(r"^(%s(?:%s)*(?:%s)*(?:%s)*)" % (_REF1, _PLUS, _PAREN, _PLUS))
REF_START_RE = re.compile(r"^(?:[1-3]\s?)?[A-Z][A-Za-z]{0,11}\.?\s?(?:\d{1,3}\s)?\d{1,3}\s?[:.]\s?\d")
DUP_CHAPTER_RE = re.compile(r"^((?:[1-3]\s?)?[A-Z][A-Za-z]{0,11}\.?)\s(\d{1,3})\s\2(\s?[:.])")


import os
_HERE = os.path.dirname(os.path.abspath(__file__))
KNOWN_BOOKS = set(open(os.path.join(_HERE, "known_books.txt")).read().split()) | {"pro", "duet"}   # + typos seen in the booklets


def book_key(tok):
    return re.sub(r"[\s.]", "", tok.lower())


# single-chapter books are printed without a chapter: "Jude 8-13"
SHORT_REF_RE = re.compile(r"^((?:[1-3]\s?)?[A-Z][a-z]{1,10}\.?)\s(\d{1,3}(?:\s?[-–]\s?\d{1,3})?[a-z]?)(?=\s|$)")
# a second reading that starts in the middle of a printed line:  "... promised land. Rom 1:16-25 (1:1-25)"
MIDLINE_REF_RE = re.compile(r"(?<=[.!?])\s+((?:[1-3]\s?)?[A-Z][A-Za-z]{0,11}\.?\s\d{1,3}\s?[:.]\s?\d.*)$")


SEASON_KEYWORDS = [   # (regex on the printed banner, season key) - order matters
    (r"annunciation.*nativity|suvara.*yalda", "annunciation+nativity"),
    (r"annunciation|suvara", "annunciation"),
    (r"nativity|yalda", "nativity"),
    (r"epiphany|denha", "epiphany"),
    (r"great fast|sauma", "great-fast"),
    (r"resurrection|qyamtha", "resurrection"),
    (r"apostles|sleehe|šleehe", "apostles"),
    (r"summer|kaitha", "kaitha"),
    (r"elijah|sleeva|musae|mu[sš]ae", "elijah-cross-moses"),
    (r"dedication|qud[ao]sh? edtha|qudas edtha", "dedication"),
]
BANNER_RE = re.compile(r"^seasons? of\b", re.I)


def season_key(text):
    t = text.lower()
    for rx, key in SEASON_KEYWORDS:
        if re.search(rx, t):
            return key
    return None


def clean(s):
    return re.sub(r"\s+", " ", PUA_RE.sub("", s)).strip()


def is_bold(fonts):
    tot = sum(fonts.values()) or 1
    return sum(v for k, v in fonts.items() if "Bold" in k) / tot > 0.5


def is_italic(fonts):
    tot = sum(fonts.values()) or 1
    return sum(v for k, v in fonts.items() if "Italic" in k and "Bold" not in k) / tot > 0.5


def read_lines(pdf_path, first_page=None, last_page=None):
    """Return a flat list of classified lines: dict(page, x0, size, bold, italic, text)."""
    out = []
    with pdfplumber.open(pdf_path) as pdf:
        n = len(pdf.pages)
        for pn in range((first_page or 1) - 1, last_page or n):
            for l in pdf.pages[pn].extract_text_lines(return_chars=True):
                chars = [c for c in l["chars"] if c["text"].strip()]
                if not chars:
                    continue
                fonts = collections.Counter(c["fontname"].split("+")[-1] for c in chars)
                bparts, nparts, last, prev = [], [], "B", None
                for c in l["chars"]:
                    if c["text"].strip():
                        last = "B" if "Bold" in c["fontname"] else "N"
                    gap = prev is not None and (c["x0"] - prev["x1"]) > 0.18 * c["size"]
                    piece = (" " if gap or not c["text"].strip() else "") + c["text"].strip()
                    (bparts if last == "B" else nparts).append(piece)
                    (nparts if last == "B" else bparts).append(" " if piece.strip() == "" or gap else "")
                    prev = c
                btxt, ntxt = clean("".join(bparts)), clean("".join(nparts))
                out.append(dict(page=pn + 1, x0=round(l["x0"]), size=round(max(c["size"] for c in chars), 1),
                                bold=is_bold(fonts), italic=is_italic(fonts), text=clean(l["text"]),
                                btext=btxt, ntext=ntxt))
    return out


def find_daily_range(pdf_path):
    """Page range of the day-by-day section: from the first page with a 'Month YYYY' heading
    followed by day lines, to the page before 'Appendix I'."""
    first = last = None
    with pdfplumber.open(pdf_path) as pdf:
        n = len(pdf.pages)
        for pn in range(n):
            t = pdf.pages[pn].extract_text() or ""
            lines = [clean(x) for x in t.split("\n")]
            if first is None:
                if any(MONTH_RE.match(x) for x in lines) and any(DAY_RE.match(x) for x in lines):
                    first = pn + 1
            elif lines and lines[0].lower().startswith("appendix"):
                last = pn
                break
    return first, (last or n)


def split_ref_title(text):
    """'Sir 24:1-14 (24:1-34) The greatness of wisdom.' -> ('Sir 24:1-14 (24:1-34)', 'The greatness of wisdom.')"""
    text = DUP_CHAPTER_RE.sub(lambda m: m.group(1) + " " + m.group(2) + m.group(3), text)   # "Ez 45 45:18-25" (typo in the booklet)
    m = REF_RE.match(text)
    if not m:
        sm = SHORT_REF_RE.match(text)
        if sm and book_key(sm.group(1)) in KNOWN_BOOKS:
            return (sm.group(1) + " " + sm.group(2)).strip(), text[sm.end():].strip()
        return None, text
    ref = m.group(1).strip()
    return ref, text[m.end():].strip()


STOP_WORDS = {"the", "of", "a", "an", "to", "and", "in", "for", "with", "by", "on", "from", "as", "is", "who", "that",
              "his", "her", "their", "our", "at", "or", "are", "be", "not", "it", "us", "we", "you", "your", "my", "me"}


def expected_readings(group):
    """Sundays and the feasts printed in bold carry 4 readings; weekdays and ordinary (plain-print) feasts 2."""
    return 4 if group.get("kind") in ("sunday", "bold") else 2


def is_plain(ln):
    return (not ln["bold"]) and (not ln["italic"]) and ln["x0"] >= INDENT_X


def starts_reading(text):
    if REF_START_RE.match(text):
        return True
    m = SHORT_REF_RE.match(text)
    return bool(m) and book_key(m.group(1)) in KNOWN_BOOKS and not re.match(r"[a-z]", text[m.end():].strip()[:1] or "A")


def is_ref_line(ln):
    return is_plain(ln) and starts_reading(ln["text"])


def parse(pdf_path, first_page=None, last_page=None):
    if first_page is None:
        first_page, last_page = find_daily_range(pdf_path)
    return parse_lines(read_lines(pdf_path, first_page, last_page))


def parse_lines(lines):
    """lines: the classified lines from read_lines().  Split out so the logic can be tested without a PDF."""
    lines = [l for l in lines if l["text"] and l["size"] >= FOOTER_SIZE]
    # a parenthesis that is still open at the end of a plain line continues on the next line
    k = 0
    while k < len(lines) - 1:
        cur, nxt = lines[k], lines[k + 1]
        if is_plain(cur) and cur["text"].count("(") > cur["text"].count(")") and is_plain(nxt) and nxt["x0"] == cur["x0"]:
            cur["text"] = clean(cur["text"] + " " + nxt["text"]); del lines[k + 1]
        else:
            k += 1
    days = collections.OrderedDict()
    problems = []
    year = month = None
    cur_date = None
    group = None          # current group dict
    reading = None        # current reading dict (title may still grow)
    seen_reading = False  # group already has readings
    skip = set()
    banner = None         # season printed on the most recent banner (cross-check for the rule-based season)

    def new_group(label, kind):
        nonlocal group, reading, seen_reading
        group = {"label": label, "kind": kind, "notes": [], "readings": []}
        days[cur_date]["groups"].append(group)
        reading = None
        seen_reading = False

    for i, ln in enumerate(lines):
        if i in skip:
            continue
        t = ln["text"]
        # month heading: big bold "December 2025" (size 14-16 depending on the page); season banners are the same size
        if ln["size"] >= 13.5 and ln["bold"]:
            mm = MONTH_RE.match(t)
            if mm:
                month, year = MONTHS.index(mm.group(1)) + 1, int(mm.group(2))
            sk = season_key(t)
            if sk:
                banner = sk         # (anything else that big is a season banner)
            continue
        if ln["bold"] and ln["x0"] < INDENT_X and BANNER_RE.match(t) and not DAY_RE.match(t):
            banner = season_key(t) or banner      # smaller banners, e.g. "Season of the Dedication of the Church"
            continue
        dm = DAY_RE.match(t) if (ln["bold"] and ln["x0"] < INDENT_X) else None
        if dm:
            if year is None:
                problems.append("day line before any month heading: %s (page %d)" % (t, ln["page"]))
                continue
            try:
                d = datetime.date(year, month, int(dm.group(1)))
            except ValueError:
                problems.append("impossible date %s-%s-%s (page %d)" % (year, month, dm.group(1), ln["page"]))
                continue
            iso = d.isoformat()
            if iso in days:
                problems.append("duplicate date %s (page %d)" % (iso, ln["page"]))
            cur_date = iso
            days[iso] = {"weekday": WEEKDAYS[d.weekday()], "banner": banner, "groups": []}
            if WEEKDAYS[d.weekday()] != dm.group(2):
                problems.append("weekday typo in PDF %s: printed %s, calendar says %s (calendar used)" % (iso, dm.group(2), WEEKDAYS[d.weekday()]))
            label = clean(re.sub(r"^\d{1,2}\s+(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b", "", ln["btext"]))
            new_group(label or dm.group(3).strip(), "sunday" if WEEKDAYS[d.weekday()] == "Sun" else "ferial")
            extra = clean(re.sub(r"^\d{1,2}\s*(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)?", "", ln["ntext"]))
            if extra and label:
                group["notes"].append(extra)
            continue
        if cur_date is None or ln["x0"] < INDENT_X:
            continue                # season essays, front matter
        if ln["bold"]:
            if re.fullmatch(r"(?i)or", t):
                new_group("Or", "bold")
                group["alternate"] = True
                continue
            if seen_reading:
                new_group(t, "bold")
            elif group["label"]:
                # a second bold line before any reading: wrapped label
                group["label"] = (group["label"] + " " + t).strip()
            else:
                group["label"] = t
            continue
        if ln["italic"]:
            group["notes"].append(t)
            reading = None
            continue
        # ---- plain print: a reading, a title continuation, an ordinary feast's name, or a plain note ----
        mid = MIDLINE_REF_RE.search(t) if (reading is not None and seen_reading) else None
        if mid and book_key(re.match(r"((?:[1-3]\s?)?[A-Z][A-Za-z]{0,11})", mid.group(1)).group(1)) in KNOWN_BOOKS:
            reading["title"] = (reading["title"] + " " + t[:mid.start()]).strip()
            t = mid.group(1)
        if starts_reading(t):
            ref, title = split_ref_title(t)
            if ref:
                reading = {"ref": ref, "title": title}
                group["readings"].append(reading)
                seen_reading = True
                continue
        if not seen_reading:
            group["notes"].append(t)          # plain-font note before the readings
            continue
        if reading is not None and not reading["title"] and re.match(r"[-–+,;]\s?[\dA-Z]|\d", t) and (re.match(r"[-–+,;]", t) or re.match(r"\d", t)):
            ref, title = split_ref_title(reading["ref"] + t)      # a long reference that wrapped onto the next line
            if ref:
                reading["ref"], reading["title"] = ref, title
                continue
        if reading is None:
            # after an 'Or' or a note, plain text with no ref: treat as a note
            group["notes"].append(t)
            continue
        # plain, no ref, after a reading: title continuation  -or-  name of an ordinary feast (new group)
        prev_words = reading["title"].lower().rstrip(" ,;:").split(" ")[-1:] or [""]
        dangling = reading["title"].rstrip().endswith((",", ";", ":")) or prev_words[0] in STOP_WORDS
        short_tail = t.endswith(".") and len(t.split()) <= 4 and not re.search(r"\b(St|Bl|Mar|Fr|Dr|Sr)\.$", t) \
            and not reading["title"].rstrip().endswith((".", "!", "?", ")"))
        complete = (len(group["readings"]) >= expected_readings(group) and reading["title"].strip() != ""
                    and not re.match(r"[a-z0-9(\[,;:.\-]", t)
                    and not dangling and not short_tail)
        run = [i]
        j = i + 1
        while j < len(lines) and is_plain(lines[j]) and not starts_reading(lines[j]["text"]):
            run.append(j); j += 1
        while j < len(lines) and lines[j]["italic"] and lines[j]["x0"] >= INDENT_X:
            j += 1                          # a note may sit between the feast's name and its readings
        followed_by_ref = j < len(lines) and is_ref_line(lines[j])
        if complete and followed_by_ref:
            if len(run) == 1 or reading["title"].rstrip().endswith("."):
                label_lines, cont_lines = run, []
            else:
                label_lines, cont_lines = run[1:], run[:1]
            for k in cont_lines:
                reading["title"] = (reading["title"] + " " + lines[k]["text"]).strip()
            new_group(" ".join(lines[k]["text"] for k in label_lines), "ordinary")
            skip.update(run)
        else:
            reading["title"] = (reading["title"] + " " + t).strip()
    for iso, d in days.items():
        keep = []
        for g in d["groups"]:
            if not g["readings"] and not g.get("alternate") and keep:
                keep[-1]["notes"].append(g["label"])      # e.g. "Independence Day of India", "(Ēliya-Sleeva-Mušae)"
                keep[-1]["notes"].extend(g["notes"])
            else:
                keep.append(g)
        d["groups"] = keep
        for g in d["groups"]:
            g.pop("kind", None)
    return days, problems


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    days, problems = parse(src)
    json.dump(days, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("%d days, %d problems" % (len(days), len(problems)))
    for p in problems[:40]:
        print(" -", p)
