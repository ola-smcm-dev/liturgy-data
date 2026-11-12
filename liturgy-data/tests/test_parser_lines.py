"""The parser's classification logic, on hand-made lines (no PDF needed)."""
import panchangam_parser as P


def L(text, x0=94, bold=False, italic=False, size=11.0, btext=None, ntext=""):
    return dict(page=1, x0=x0, size=size, bold=bold, italic=italic, text=text, btext=btext if btext is not None else (text if bold else ""), ntext=ntext)


def sample():
    return [
        L("December 2026", x0=200, bold=True, size=14),
        L("27 Sun First Sunday of Annunciation", x0=43, bold=True, btext="27 Sun First Sunday of Annunciation"),
        L("Gen 17:15-22 (17:1-27) Announcement about the birth of Isaac."),
        L("Isa 43:1-7 (42:18-43:13) Salvation for Israel."),
        L("Heb 11:8-12 Faith of Abraham and Sarah."),
        L("Lk 1:5-25 The angel announces the birth of John."),
        L("28 Mon Holy Innocents", x0=43, bold=True, btext="28 Mon Holy Innocents"),
        L("Jer 31:15-17 Rachel weeping for her children."),
        L("Mt 2:13-18 The slaughter of the infants."),
        L("29 Tue First Tuesday", x0=43, bold=True, btext="29 Tue First Tuesday"),
        L("Isa 7:10-17 The sign of Immanuel."),
        L("Lk 1:26-38 The Annunciation."),
        L("Or", bold=True),
        L("Isa 9:1-7 A child is born to us."),
        L("Lk 2:1-7 The birth of Jesus."),
    ]


def test_dates_groups_and_readings():
    days, problems = P.parse_lines(sample())
    assert list(days) == ["2026-12-27", "2026-12-28", "2026-12-29"]
    sun = days["2026-12-27"]["groups"]
    assert sun[0]["label"] == "First Sunday of Annunciation"
    assert [r["ref"] for r in sun[0]["readings"]] == ["Gen 17:15-22 (17:1-27)", "Isa 43:1-7 (42:18-43:13)", "Heb 11:8-12", "Lk 1:5-25"]
    assert sun[0]["readings"][0]["title"] == "Announcement about the birth of Isaac."
    assert days["2026-12-27"]["weekday"] == "Sun"


def test_or_starts_an_alternate_group():
    tue = P.parse_lines(sample())[0]["2026-12-29"]["groups"]
    assert len(tue) == 2 and tue[1].get("alternate") is True and len(tue[1]["readings"]) == 2


def test_wrong_weekday_in_the_pdf_is_reported_and_the_calendar_used():
    lines = [L("December 2026", x0=200, bold=True, size=14),
             L("28 Sat Holy Innocents", x0=43, bold=True, btext="28 Sat Holy Innocents"),
             L("Jer 31:15-17 Rachel."), L("Mt 2:13-18 Infants.")]
    days, problems = P.parse_lines(lines)
    assert days["2026-12-28"]["weekday"] == "Mon" and any("weekday typo" in p for p in problems)


def test_season_banner_is_recorded():
    lines = [L("SEASON OF EPIPHANY (DENHA)", x0=100, bold=True, size=14),
             L("January 2027", x0=200, bold=True, size=14),
             L("6 Wed The Feast of Denha", x0=43, bold=True, btext="6 Wed The Feast of Denha"),
             L("Isa 60:1-6 Arise, shine."), L("Mt 2:1-12 The Magi.")]
    days, _ = P.parse_lines(lines)
    assert days["2027-01-06"]["banner"] == "epiphany"


def test_page_footers_are_ignored():
    lines = sample() + [L("12", x0=300, size=8)]
    days, _ = P.parse_lines(lines)
    assert len(days["2026-12-29"]["groups"][1]["readings"]) == 2
