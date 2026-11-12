#!/usr/bin/env python3
"""
Turns the result of tools/update.py into a GitHub Issue - GitHub then emails everyone who is assigned, mentioned
or watching the repository.  No mail server, no passwords, no secrets: only the workflow's own GITHUB_TOKEN.

    python3 tools/notify.py [--dry-run]            reads out/result.json and out/issue.md

 error / health-alert        -> an issue labelled liturgy-alert (a second identical alert becomes a comment, not a new issue)
 published-review            -> an issue labelled liturgy-alert listing the dates a person should look at
 published                   -> a short "published" issue labelled liturgy-info, closed straight away (the e-mail is the point)
 up-to-date / not-yet / health-ok  -> nothing
People to notify: .github/alert-people.txt (one GitHub username per line).
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))


def people(root=ROOT):
    p = os.path.join(root, ".github", "alert-people.txt")
    if not os.path.exists(p):
        return []
    return [l.strip().lstrip("@") for l in open(p, encoding="utf-8") if l.strip() and not l.strip().startswith("#")]


def plan(res, who):
    """-> None, or dict(title, label, close, body_prefix)"""
    st = res["status"]
    cc = ("cc " + " ".join("@" + w for w in who) + "\n\n") if who else \
        "> **No one is listed in `.github/alert-people.txt`**, so only people who *Watch* this repository get an e-mail. Please add at least two GitHub usernames.\n\n"
    if st in ("error", "health-alert"):
        return dict(title=res["title"], label="liturgy-alert", close=False, prefix=cc)
    if st == "published-review":
        return dict(title="Liturgy data %s published - %d date(s) need a look" % (res["booklet"], len(res["review"])),
                    label="liturgy-alert", close=False, prefix=cc)
    if st == "published":
        return dict(title="Liturgy data %s published" % res["booklet"], label="liturgy-info", close=True, prefix=cc)
    return None


def gh(args, dry, input_text=None):
    if dry:
        print("  [dry-run] gh " + " ".join(args))
        return ""
    r = subprocess.run(["gh"] + args, capture_output=True, text=True, input=input_text)
    if r.returncode != 0:
        raise RuntimeError("gh %s failed: %s" % (" ".join(args[:2]), r.stderr.strip()[:300]))
    return r.stdout.strip()


def main(argv=None):
    dry = "--dry-run" in (argv if argv is not None else sys.argv[1:])
    out = os.environ.get("RESULT_DIR", "out")
    rp = os.path.join(out, "result.json")
    if not os.path.exists(rp):
        print("no result file (an earlier step stopped before writing one) - GitHub's own failed-run e-mail covers this")
        return 0
    res = json.load(open(rp))
    body = open(os.path.join(out, "issue.md"), encoding="utf-8").read()
    if res["status"] in ("published", "published-review") and os.environ.get("COMMIT_OUTCOME") in ("failure", "cancelled"):
        # the data was built but could not be saved: do not send a "published" note
        res = {"status": "error", "title": "Liturgy data: new data was built but could not be saved to the repository",
               "reason": "the save (commit) step failed", "errors": ["Probably a branch rule that blocks the robot - see SECURITY.md (rule for main)."]}
        body = "**The new %s data passed all checks but could not be committed**, so nothing changed on the website.\n\n" \
               "Open the Actions tab, open this run, and read the 'Commit new data' step. The usual cause is a branch rule on `main` that " \
               "requires pull requests or blocks the robot (only 'Restrict deletions' and 'Block force pushes' should be on).\n" % res.get("booklet", "")
    who = people()
    p = plan(res, who)
    if not p:
        print("nothing to report (%s)" % res["status"])
        return 0
    run_url = "%s/%s/actions/runs/%s" % (os.environ.get("GITHUB_SERVER_URL", "https://github.com"),
                                         os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GITHUB_RUN_ID", ""))
    text = p["prefix"] + body + ("\n[Workflow run](%s)\n" % run_url if os.environ.get("GITHUB_RUN_ID") else "")
    for lab, colour in (("liturgy-alert", "d93f0b"), ("liturgy-info", "0e8a16")):
        gh(["label", "create", lab, "--color", colour, "--force"], dry)
    if p["label"] == "liturgy-alert":
        found = gh(["issue", "list", "--label", "liturgy-alert", "--state", "open", "--search", p["title"] + " in:title",
                    "--json", "number,title", "--limit", "20"], dry) or "[]"
        for it in json.loads(found):
            if it["title"] == p["title"]:
                gh(["issue", "comment", str(it["number"]), "--body-file", "-"], dry, text)
                print("commented on existing issue #%s" % it["number"])
                return 0
    args = ["issue", "create", "--title", p["title"], "--label", p["label"], "--body-file", "-"]
    try:
        url = gh(args + (["--assignee", ",".join(who)] if who else []), dry, text)
    except RuntimeError as e:
        print("assigning failed (%s) - creating the issue with @mentions only" % e)
        url = gh(args, dry, text)
    print("issue:", url)
    if p["close"] and url and not dry:
        gh(["issue", "close", url], dry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
