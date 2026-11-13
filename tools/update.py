#!/usr/bin/env python3
"""
The unattended pipeline:  find the newest English Panchangam on the Commission's site -> download -> parse ->
validate -> register in sources/ -> rebuild days/ and index.json.   Nothing is written unless validation passes.

    python3 tools/update.py                         look for a new booklet (what the scheduled run does)
    python3 tools/update.py --pdf FILE --id 2026-2027   use a PDF you downloaded yourself
    python3 tools/update.py --health                check that the data still covers the coming weeks
    python3 tools/update.py --health --require-next-year   (Dec 21: next year's file must exist by now)
    add --dry-run to change nothing

Writes a result for the workflow to $RESULT_DIR (default ./out): result.json, issue.md.
status:  up-to-date | not-yet | published | published-review | error | health-ok | health-alert
"""
import argparse, datetime as dt, json, os, re, sys, tempfile, urllib.parse, urllib.request, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import panchangam_parser as PP
import validate as VA
import calendar_rules as CR
import build as BU
import checks as CK

LIST_PAGE = "https://www.syromalabarliturgy.org/liturgical_texts"
ALLOWED_HOSTS = {"www.syromalabarliturgy.org", "syromalabarliturgy.org"}
MAX_PDF_BYTES = 60 * 1024 * 1024
USER_AGENT = "ola-liturgy-data/1.0 (+https://github.com/ola-smcm-dev/liturgy-data)"


# ---------------------------------------------------------------- discovery
def allowed_url(url):
    p = urllib.parse.urlparse(url)
    return p.scheme == "https" and (p.hostname or "").lower() in ALLOWED_HOSTS


def find_panchangam_links(html, base=LIST_PAGE):
    """[(id '2026-2027', url)] for every English Panchangam PDF linked from the page, newest first."""
    found = {}
    for href in re.findall(r"""href\s*=\s*["']([^"']+)["']""", html, flags=re.I):
        url = urllib.parse.urljoin(base, href.strip())
        name = urllib.parse.unquote(urllib.parse.urlparse(url).path.rsplit("/", 1)[-1]).lower()
        if not name.endswith(".pdf") or "panchangam" not in name or "malayalam" in name:
            continue
        m = re.search(r"(20\d\d)\s*[-_]\s*(20\d\d)", name)
        if not m or int(m.group(2)) != int(m.group(1)) + 1:
            continue
        if not allowed_url(url):
            continue
        bid = "%s-%s" % m.groups()
        if bid not in found or ("english" in name and "english" not in found[bid][1].lower()):
            found[bid] = (bid, url)
    return sorted(found.values(), reverse=True)


class _SameHostRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed_url(newurl):
            raise urllib.error.URLError("redirect to a host that is not allowed: %s" % newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def http_get(url, limit=MAX_PDF_BYTES, timeout=60):
    if not allowed_url(url):
        raise ValueError("refusing to fetch %s (only https on %s)" % (url, sorted(ALLOWED_HOSTS)))
    opener = urllib.request.build_opener(_SameHostRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with opener.open(req, timeout=timeout) as r:
        data = r.read(limit + 1)
    if len(data) > limit:
        raise ValueError("download larger than %d MB, refusing" % (limit // 1024 // 1024))
    return data


# ---------------------------------------------------------------- processing
def booklet_expectations(bid):
    y = int(bid[:4])
    return CR.annunciation_start(y).isoformat(), "%d-12-01" % (y + 1)


def register(root, bid, days, source_url):
    reg_path = os.path.join(root, "sources", "booklets.json")
    reg = json.load(open(reg_path, encoding="utf-8"))
    reg["booklets"] = [b for b in reg["booklets"] if b["id"] != bid] + [
        {"id": bid, "parsed": "sources/%s.json" % bid, "source_url": source_url}]
    reg["booklets"].sort(key=lambda b: b["id"])
    json.dump(days, open(os.path.join(root, "sources", "%s.json" % bid), "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    json.dump(reg, open(reg_path, "w", encoding="utf-8", newline="\n"), indent=1)


def process_parsed(root, bid, days, problems, source_url, dry_run=False):
    """Validate + register + rebuild.  Returns a result dict; never leaves half-written state on failure."""
    first, last = booklet_expectations(bid)
    errors, warnings, review = VA.validate(days, expect_first=first, expect_last=last)
    res = {"booklet": bid, "problems": problems, "warnings": warnings, "review": dict(review)}
    if errors:
        res.update(status="error", title="Liturgy data: the %s Panchangam could not be read safely" % bid,
                   reason="validation failed", errors=errors)
        return res
    if dry_run:
        res.update(status="published", dry_run=True, days=len(days))
        return res
    # snapshot so a failing rebuild leaves the repo as it was
    snap = tempfile.mkdtemp()
    for d in ("sources", "days", "days-ml", "reports"):
        if os.path.isdir(os.path.join(root, d)):
            shutil.copytree(os.path.join(root, d), os.path.join(snap, d))
    shutil.copy(os.path.join(root, "index.json"), os.path.join(snap, "index.json"))
    try:
        register(root, bid, days, source_url)
        r = BU.build(root, log=lambda *_: None)
        bad = CK.published_problems(root)                       # the same checks apps rely on, on the files just written
        if bad:
            raise RuntimeError("the new data failed the final checks: " + " | ".join(bad[:8]))
    except BaseException as e:                                  # includes SystemExit from build
        for d in ("sources", "days", "days-ml", "reports"):
            shutil.rmtree(os.path.join(root, d), ignore_errors=True)
            if os.path.isdir(os.path.join(snap, d)):
                shutil.copytree(os.path.join(snap, d), os.path.join(root, d))
        shutil.copy(os.path.join(snap, "index.json"), os.path.join(root, "index.json"))
        res.update(status="error", title="Liturgy data: building the %s data failed" % bid, reason="build failed", errors=[str(e)])
        return res
    finally:
        shutil.rmtree(snap, ignore_errors=True)
    res.update(status="published-review" if review else "published", days=len(days), changed=r["changed"],
               build_warnings=r["warnings"][:40])
    return res


def run_update(root, pdf=None, bid=None, dry_run=False, fetch=http_get, now=None):
    now = now or dt.date.today()
    known = {b["id"] for b in json.load(open(os.path.join(root, "sources", "booklets.json"), encoding="utf-8"))["booklets"]}
    url = ""
    if pdf is None:
        try:
            html = fetch(LIST_PAGE, limit=5 * 1024 * 1024).decode("utf-8", "replace")
        except Exception as e:
            return {"status": "error", "title": "Liturgy data: the Commission's website could not be reached",
                    "reason": "list page not reachable", "errors": [repr(e)]}
        links = find_panchangam_links(html)
        if not re.search(r"\.pdf", html, re.I):
            return {"status": "error", "title": "Liturgy data: the Commission's page looks different now",
                    "reason": "no PDF links at all on the page - its layout may have changed", "errors": [LIST_PAGE]}
        new = [l for l in links if l[0] not in known and l[0] > max(known)]
        if not new:
            return {"status": "up-to-date",
                    "message": "no newer English Panchangam than %s (%d found on the page)" % (max(known), len(links))}
        bid, url = new[0]
        try:
            data = fetch(url)
        except Exception as e:
            return {"status": "error", "title": "Liturgy data: the %s Panchangam was found but could not be downloaded" % bid,
                    "reason": "download failed", "errors": [url, repr(e)]}
        if not data.startswith(b"%PDF") or len(data) < 200_000:
            return {"status": "error", "title": "Liturgy data: the %s download is not a normal PDF" % bid,
                    "reason": "not a PDF or too small (%d bytes)" % len(data), "errors": [url]}
        tmp = tempfile.mkdtemp()
        pdf = os.path.join(tmp, "panchangam.pdf")
        open(pdf, "wb").write(data)
    elif not bid:
        m = re.search(r"(20\d\d)\s*[-_]\s*(20\d\d)", os.path.basename(pdf))
        if not m:
            raise SystemExit("--id is required (for example --id 2026-2027)")
        bid = "%s-%s" % m.groups()
    try:
        days, problems = PP.parse(pdf)
    except Exception as e:
        return {"status": "error", "title": "Liturgy data: the %s Panchangam could not be parsed" % bid,
                "reason": "parser crashed", "errors": [repr(e)]}
    finally:
        pass
    return process_parsed(root, bid, days, problems, url or "manual", dry_run=dry_run)


# ---------------------------------------------------------------- health
def run_health(root, today=None, require_next_year=False):
    today = today or dt.date.today()
    idx = json.load(open(os.path.join(root, "index.json"), encoding="utf-8"))
    last = dt.date.fromisoformat(idx["coverage"]["last"])
    days_left = (last - today).days
    need = dt.date(today.year + 1, 6, 30) if require_next_year else today + dt.timedelta(days=45)
    if last < need:
        why = ("It is %s and the readings only run until %s" % (today.isoformat(), last.isoformat()))
        return {"status": "health-alert", "days_left": days_left,
                "title": "Liturgy data: next year's readings are still missing" if require_next_year
                         else "Liturgy data: the readings run out in %d days" % max(days_left, 0),
                "reason": why}
    return {"status": "health-ok", "days_left": days_left, "message": "data covers until %s (%d days from today)" % (last, days_left)}


# ---------------------------------------------------------------- issue text
def issue_markdown(res, repo_url="https://github.com/ola-smcm-dev/liturgy-data"):
    st = res["status"]
    L = []
    if st == "error":
        L += ["**What happened:** %s" % res.get("reason", ""), "",
              "**Nothing was published** - the website and the TV app keep showing the data they already have.", ""]
        for e in res.get("errors", [])[:15]:
            L.append("- `%s`" % str(e)[:400])
        L += ["", "**What to do:** open the *Actions* tab, open the failed run, read the log. If the Commission published a new layout, "
                  "the parser may need an update (see HANDOVER.md). Meanwhile the Commission's page has the readings: https://www.syromalabarliturgy.org/liturgical_texts"]
    elif st == "health-alert":
        L += [res.get("reason", ""), "",
              "The Commission usually publishes next year's Panchangam in mid-November to early December. "
              "Check https://www.syromalabarliturgy.org/liturgical_texts - if it is there, run the *Update liturgy data* workflow by hand "
              "(Actions tab -> Run workflow); if the run fails, see HANDOVER.md."]
    elif st in ("published", "published-review"):
        L += ["The **%s** Panchangam was found, checked and published (%s days)." % (res["booklet"], res.get("days", "?")), ""]
        if res.get("review"):
            L.append("**%d date(s) look unusual** - they are published, but apps show a link to the Commission's page for them. A person should look:" % len(res["review"]))
            for d, why in list(res["review"].items())[:30]:
                L.append("- %s - %s" % (d, "; ".join(why)[:300]))
            L.append("")
        if res.get("build_warnings"):
            L.append("Notes:")
            L += ["- %s" % w for w in res["build_warnings"][:15]]
            L.append("")
        L.append("Celebration names without Malayalam yet: see `reports/untranslated-celebrations.txt`.")
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf"); ap.add_argument("--id")
    ap.add_argument("--health", action="store_true"); ap.add_argument("--require-next-year", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--root", default=ROOT)
    a = ap.parse_args(argv)
    res = run_health(a.root, require_next_year=a.require_next_year) if a.health else run_update(a.root, a.pdf, a.id, a.dry_run)
    out = os.environ.get("RESULT_DIR", "out")
    os.makedirs(out, exist_ok=True)
    json.dump(res, open(os.path.join(out, "result.json"), "w"), indent=1, default=str)
    md = issue_markdown(res)
    open(os.path.join(out, "issue.md"), "w", encoding="utf-8").write(md)
    print("status:", res["status"], "-", res.get("message") or res.get("reason") or res.get("title", ""))
    for e in res.get("errors", [])[:10]:
        print("  error:", e)
    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a") as f:
            f.write("status=%s\n" % res["status"])
            f.write("title=%s\n" % res.get("title", "").replace("\n", " "))
    return 1 if res["status"] == "error" else 0


if __name__ == "__main__":
    sys.exit(main())
