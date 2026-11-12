"""
Bible references as printed in the Panchangam -> tidy, consistent text.

The booklet prints the same thing in many ways:  "Gen 21: 9-21 (21: 1-21)", "1Cor 15:39-49", "Is.11:1-12", "Acts1:12-14(1:1-14)", "Duet 9:1-6" ...
    tidy(ref)           "Gen 21: 9-21 (21: 1-21)"  ->  "Gen 21:9-21 (21:1-21)"      spacing fixed, book abbreviation standardised
    split(ref)          -> ("Gen 21:9-21", "21:1-21")   main reading, and the bracketed LONGER version (or "")
    expand(ref, books)  "Gen 21:9-21"  ->  "Genesis 21:9-21"   (any book name inside the text, also after a "+")
Nothing here ever invents or removes a verse number: only spaces, punctuation, and the spelling of the book name change.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
_BOOKS = None


def load_books(path=None):
    path = path or os.path.join(HERE, "..", "data", "books.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)["books"]


def _tables(books=None):
    global _BOOKS
    if books is None:
        if _BOOKS is None:
            _BOOKS = load_books()
        books = _BOOKS
    alias = {}
    for b in books:
        alias[re.sub(r"[\s.]", "", b["abbr"].lower())] = b
        for a in b["aliases"]:
            alias[a] = b
    return alias


# a book name: optional leading 1/2/3, letters, optional dot, then (optional space and) the first chapter/verse digit
_BOOK_RE = re.compile(r"(?<![A-Za-z0-9])((?:[1-3]\s?)?[A-Za-z]{2,})\.?\s*(?=\d)")


def tidy(ref, books=None):
    alias = _tables(books)
    s = re.sub(r"\s+", " ", ref or "").strip()
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\s*:\s*", ":", s)                         # 21: 9  ->  21:9
    s = re.sub(r"\s*-\s*", "-", s)                         # 3:1- 21 -> 3:1-21
    s = re.sub(r"\s*,\s*", ", ", s)
    s = re.sub(r"\s*;\s*", "; ", s)
    s = re.sub(r"\s*\+\s*", " + ", s)
    s = re.sub(r"\s*\(\s*", " (", s)
    s = re.sub(r"\s*\)", ")", s)
    s = re.sub(r"\)(?=\S)", ") ", s)

    def book(m):
        b = alias.get(re.sub(r"[\s.]", "", m.group(1).lower()))
        return (b["abbr"] if b else re.sub(r"\s+", " ", m.group(1))) + " "
    s = _BOOK_RE.sub(book, s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.replace("( ", "(")


def split(ref):
    """tidy ref -> (main, longer). 'Gen 21:9-21 (21:1-21)' -> ('Gen 21:9-21', '21:1-21'); no bracket -> (ref, '')"""
    i = ref.find(" (")
    if i < 0 or not ref.endswith(")"):
        return ref, ""
    return ref[:i].strip(), ref[i + 2:-1].strip()


def expand(ref, books=None, lang="en"):
    alias = _tables(books)

    def book(m):
        b = alias.get(re.sub(r"[\s.]", "", m.group(1).lower()))
        return (b[lang] or b["en"]) + " " if b else m.group(0)
    return _BOOK_RE.sub(book, ref)
