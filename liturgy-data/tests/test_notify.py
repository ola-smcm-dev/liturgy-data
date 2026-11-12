import notify as N


def test_who_gets_mentioned():
    p = N.plan({"status": "error", "title": "T"}, ["alice", "bob"])
    assert p["label"] == "liturgy-alert" and "@alice @bob" in p["prefix"] and p["close"] is False


def test_success_issue_is_closed_straight_away():
    p = N.plan({"status": "published", "booklet": "2026-2027"}, ["a"])
    assert p["label"] == "liturgy-info" and p["close"] is True


def test_quiet_when_nothing_happened():
    for st in ("up-to-date", "not-yet", "health-ok"):
        assert N.plan({"status": st}, ["a"]) is None
