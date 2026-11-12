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


def test_a_failed_commit_turns_the_success_note_into_an_alert(tmp_path, monkeypatch):
    import json
    (tmp_path / "result.json").write_text(json.dumps({"status": "published", "booklet": "2026-2027", "days": 365, "review": {}}))
    (tmp_path / "issue.md").write_text("ok")
    monkeypatch.setenv("RESULT_DIR", str(tmp_path))
    monkeypatch.setenv("COMMIT_OUTCOME", "failure")
    seen = []
    monkeypatch.setattr(N, "gh", lambda args, dry, input_text=None: seen.append((args, input_text)) or "")
    N.main([])
    create = [a for a, _ in seen if a[:2] == ["issue", "create"]][0]
    assert "could not be saved" in create[create.index("--title") + 1] and "liturgy-alert" in create
