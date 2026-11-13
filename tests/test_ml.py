import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import ml  # noqa: E402

GL = json.load(open(os.path.join(ROOT, "data", "glossary-ml.json"), encoding="utf-8"))
BK = json.load(open(os.path.join(ROOT, "data", "books.json"), encoding="utf-8"))

# pairs copied from the Commission's own Malayalam daily-readings page (2026), chillu letters in atomic form
COMMISSION = {
    "Second Thursday of Dedication of the Church": "പള്ളിക്കൂദാശ രണ്ടാം വ്യാഴം",
    "First Wednesday of Denha": "ദനഹാ ഒന്നാം ബുധൻ",
    "Second Tuesday of the Great Fast": "നോമ്പ് രണ്ടാം ചൊവ്വ",
    "Third Monday of the Great Fast": "നോമ്പ് മൂന്നാം തിങ്കൾ",
    "Fourth Sunday of Resurrection": None,
    "Third Sunday of Resurrection": "ഉയിർപ്പ് മൂന്നാം ഞായർ",
    "First Monday of the Apostles": "ശ്ലീഹാ ഒന്നാം തിങ്കൾ",
    "Seventh Thursday of the Apostles": "ശ്ലീഹാ ഏഴാം വ്യാഴം",
    "First Saturday of Kaitha": "കൈത്താ ഒന്നാം ശനി",
    "Third Wednesday of Elijah": "ഏലിയാ മൂന്നാം ബുധൻ",
    "Second Thursday of Cross": "സ്ലീവാ രണ്ടാം വ്യാഴം",
    "Third Saturday of Moses": "മൂശെ മൂന്നാം ശനി",
    "Second Sunday of Annunciation": "മംഗളവാർത്ത രണ്ടാം ഞായർ",
    "Second Sunday of Nativity": "പിറവി രണ്ടാം ഞായർ",
    "Fifth Friday of Kaitha": "കൈത്താ അഞ്ചാം വെള്ളി",
}


def test_day_labels_match_the_commission_wording():
    for en, want in COMMISSION.items():
        got = ml.day_label(en, GL)
        if want is None:
            continue
        assert got == want, (en, got, want)


def test_day_label_declines_when_unsure():
    assert ml.day_label("Fifth Friday of Denha (The Greek Fathers)", GL) is None
    assert ml.day_label("Easter", GL) is None
    assert ml.day_label("Eighth Sunday of Epiphany", GL) is None      # unverified ordinal


def test_reference_names():
    assert ml.ref_ml("Jn 3:22-30", BK) == "യോഹ 3:22-30"
    assert ml.ref_ml("2 Cor 11:1-4", BK) == "2 കോറി 11:1-4"
    assert ml.ref_ml("Ps 23:1-6", BK, abbr=True) is not None          # falls back to the full name
    assert ml.ref_ml("Zzz 1:1", BK) is None


def test_no_old_style_chillu_left():
    import re
    for path in ("books.json", "glossary-ml.json"):
        t = open(os.path.join(ROOT, "data", path), encoding="utf-8").read()
        assert "‍" not in t and "‌" not in t, path
