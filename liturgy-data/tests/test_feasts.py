import feasts as F
import calendar_rules as C


def test_every_rule_resolves_in_every_year():
    rules = F.load_rules()
    for y in range(2024, 2041):
        out = F.feasts_for_year(rules, y)
        titles = {f["title"] for lst in out.values() for f in lst}
        for r in rules:
            if r.get("rule"):
                assert C.resolve_rule(r["rule"], r["title"], y) is not None, (y, r)
        assert "Christmas - Nativity of Our Lord" in titles


def test_christmas_is_an_obligation_and_absorbs_the_duplicate_row():
    out = F.feasts_for_year(F.load_rules(), 2026)["2026-12-25"]
    assert len(out) == 1 and out[0]["obligation"] is True


def test_ascension_moves_with_easter():
    r = F.load_rules()
    assert any(f["title"].startswith("Ascension") for f in F.feasts_for_year(r, 2026)["2026-05-14"])
    assert any(f["title"].startswith("Ascension") for f in F.feasts_for_year(r, 2027)["2027-05-06"])
