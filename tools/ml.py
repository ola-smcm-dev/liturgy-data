#!/usr/bin/env python3
"""Malayalam helpers built on data/glossary-ml.json and data/books.json.

  day_label(label, glossary)  'Second Thursday of Dedication of the Church' -> 'പള്ളിക്കൂദാശ രണ്ടാം വ്യാഴം'
  ref_ml(ref, books, abbr=True)  'Jn 3:22-30' -> 'യോഹ 3:22-30'

Both return None when they cannot translate with confidence, so the caller falls back to English.
"""
import re

_SEASON_EN = [  # longest first
    ("Elijah-Cross-Moses", "ecm"), ("Dedication of the Church", "dedication"), ("Great Fast", "great-fast"),
    ("Annunciation", "annunciation"), ("Resurrection", "resurrection"), ("Epiphany", "epiphany"), ("Denha", "epiphany"),
    ("Dneha", "epiphany"), ("Nativity", "nativity"), ("Apostles", "apostles"), ("Kaitha", "kaitha"),
    ("Elijah", "elijah"), ("Cross", "cross"), ("Moses", "moses"),
]
_LABEL_RE = re.compile(r"^(?:The )?(\w+) (Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday) of (?:the )?(.+)$")


def day_label(label, glossary):
    """Translate a plain '<ordinal> <weekday> of <season>' label. Anything with extra words (a feast name,
    a bracket) returns None - those names are looked up in glossary['celebrations'] instead."""
    parts = glossary.get("label_parts") or {}
    m = _LABEL_RE.match(label.strip())
    if not m:
        return None
    ordn, wd, rest = m.groups()
    rest = rest.strip()
    key = None
    for en, k in _SEASON_EN:
        if rest == en:
            key = k
            break
    if key is None:
        return None
    sw = parts.get("season_word", {})
    word = sw.get("ecm" if key == "ecm" else key)
    if key == "ecm":
        word = parts.get("ecm_word")
    o, w = parts.get("ordinal", {}).get(ordn), parts.get("weekday", {}).get(wd)
    if not (word and o and w) or ordn in parts.get("unverified_ordinals", []):
        return None
    return "%s %s %s" % (word, o, w)


def _key(s):
    s = re.sub(r"\b(saints?|sts?\.?)(?=\W)", "st", s.lower())
    s = re.sub(r"\b(blessed|bl\.)(?=\W)", "bl", s)
    return re.sub(r"[^a-z0-9]", "", s)


_SEASON_ALT = "|".join(re.escape(en) for en, _ in _SEASON_EN)
_PREFIX_RE = re.compile(r"^(?:The )?(\w+) (Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday) of (?:the )?(%s)(.*)$" % _SEASON_ALT)


def feast_ml(name, glossary):
    """Malayalam for a feast / celebration name from data/glossary-ml.json (spelling-insensitive), or None."""
    k = _key(name)
    for en, m in glossary.get("celebrations", {}).items():
        if _key(en) == k:
            return m
    return None


def label_ml(label, glossary):
    """-> (text, partial).  text is None when nothing can be said in Malayalam (the caller shows English).
    partial=True means a feast name written after the day label could not be translated and was left out."""
    hit = feast_ml(label, glossary)
    if hit:
        return hit, False
    m = _PREFIX_RE.match(label.strip())
    if not m:
        return None, False
    ordn, wd, season, rest = m.groups()
    base = day_label("%s %s of %s" % (ordn, wd, season), glossary)
    if not base:
        return None, False
    tail = rest.strip(" ()-\u2013:,/")
    if not tail:
        return base, False
    # several celebrations written together: "(Unity Octave Ends) X", "A // B": translate each piece or give up the extras
    pieces = [x.strip(" ()-\u2013:,") for x in re.split(r"\s*//\s*", tail) if x.strip(" ()-\u2013:,")]
    done = [feast_ml(x, glossary) for x in pieces]
    if all(done):
        return "%s (%s)" % (base, ", ".join(done)), False
    return base, True


def ref_ml(ref, books, abbr=True):
    """'Jn 3:22-30' -> 'യോഹ 3:22-30'. Only the plain 'Book c:v-v' form is handled (bracket / '+' forms: first book only
    is translated if every book in the string is known, otherwise None)."""
    by = {b["abbr"]: b for b in books["books"]}
    pat = re.compile(r"(?<![A-Za-z0-9])((?:[1-3] )?[A-Z][A-Za-z]+)(?= \d)")
    ok = [True]

    def sub(m):
        b = by.get(m.group(1))
        name = b and ((b.get("ml_abbr") if abbr else None) or b.get("ml"))
        if not name:
            ok[0] = False
            return m.group(0)
        return name
    out = pat.sub(sub, ref)
    return out if ok[0] else None
