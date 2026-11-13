# liturgy-data — day-by-day liturgical data for Our Lady of Assumption Syro-Malabar Mission

One public source of "what day is it in the Church year" for the **church website** and the **Qurbana TV/projector app**:
the season, the readings (reference + title), the celebrations and feast days, days of obligation — for every date, in English,
with Malayalam book names and season names ready for the Malayalam mode.

* Nothing personal is ever stored here (no names, intentions, birthdays, announcements). Public data only.
* No Bible text and no PDF copies. Readings are references + the Commission's one-line titles. See `NOTICE.md`.
* A GitHub Action picks up each new Panchangam **by itself**, checks it, and publishes it — or e-mails people if anything is wrong.

## What the apps read

Published through GitHub Pages at `https://ola-smcm-dev.github.io/liturgy-data/` :

| File | What it is |
|---|---|
| `index.json` | which years exist, first/last date covered, season names (English + Malayalam), dates a person should look at |
| `days/<year>.json` | one record per date of that calendar year |
| `days-ml/<year>.json` | the Malayalam layer for the same dates: season, day label, reading references (short and full book names), feast names. Built from the proofread tables in `data/` - no reading titles. Anything missing = show the English |
| `data/books.json` | each Bible book: standard abbreviation, full English name, Malayalam name (draft), and the spellings printed in the Panchangam |
| `data/glossary-ml.json` | Malayalam names for seasons and the main feasts (draft) |
| `data/feast-rules.json` | the feast-day list: fixed dates and movable rules ("Sixth Thursday after Easter") |

A day record:

```json
"2026-05-14": {
  "weekday": "Thu", "season": "resurrection", "obligation": true,
  "celebrations": [ { "label": "Sixth Thursday of Resurrection Ascension of the Lord",
                      "notes": ["Important feast day and a day of obligation."],
                      "readings": [ { "ref": "Acts 1:1-11", "main": "Acts 1:1-11", "title": "…" }, … ] } ],
  "feasts": [ { "title": "Ascension of our Lord", "obligation": true } ]
}
```

* A reading has: `main` = the passage as proclaimed (**show this one** — e.g. `Gen 21:9-21`); `longer` = the bracketed longer version the booklet
  prints for some readings (e.g. `21:1-21`; may be a combination such as `Gal 5:1-6 + Phil 2:5-11`); `ref` = `main` + ` (longer)`; `title` = the Commission's
  one-line title. Spacing and book abbreviations are standardised by the repo (the booklet prints `Gen 21: 9-21`, `1Cor`, `Is.11`, `Duet` …).
  Verse numbers are never changed. For full book names use `data/books.json` (`abbr` → `en` / `ml`; the four Gospels are Matthew, Mark, Luke, John).
  `examples/tv_loader.py` → `reading_text()` does this: `Gen 21:9-21` → `Genesis 21:9-21`.
* `season` is one of: annunciation, nativity, epiphany, great-fast, resurrection, apostles, kaitha, elijah-cross-moses, dedication.
* `check: true` on a day means the Panchangam page for that day looked unusual to the parser. The readings are there, but show a link to
  https://www.syromalabarliturgy.org/liturgical_texts next to them.
* `celebrations[].alternate: true` is an "Or" set of readings.
* If a date is **not in the file** (data has run out), apps must say so ("readings not available") — never guess.
* **Always show text with `textContent`** (or escape it). Never put it into `innerHTML` raw.

Examples for the two apps: `examples/tv_loader.py` (one fetch at start-up → saved locally → bundled seed copy → "out of date" flag)
and `examples/website-loader.js`.

## How new years arrive (automatic)

`.github/workflows/update.yml`:

| When (UTC) | What |
|---|---|
| every day 15 Nov – 20 Dec | looks at the Commission's page for a newer English Panchangam → downloads → reads it → checks it → publishes |
| 21 Dec | if next year's readings are still missing → alert e-mail |
| 1st of each month | health check ("do the readings cover the next 45 days?") + keeps the schedule from being switched off by GitHub |

Nothing is published unless the checks pass (every date present, enough days, readings on practically every day, the right start/end dates).
When something is odd, the previous data stays live and the people in `.github/alert-people.txt` get an e-mail.

### E-mail alerts (no passwords or mail servers)

The workflow opens a GitHub **Issue**; GitHub e-mails the people who are assigned / @mentioned / watching.
Edit `.github/alert-people.txt` and list **two or more** GitHub usernames (each needs write access to the repo). Also ask each of them to
click **Watch → Custom → Issues, Actions** on the repo page. You get e-mails for:

* the Commission's site cannot be reached / the file is not a normal PDF / the page layout changed / the parser fails / the checks fail
* the readings will run out within 45 days, or next year's file is missing on 21 Dec
* a new year was published (short "published" note) — and, if some dates look unusual, which ones
* GitHub itself also e-mails the person who last edited the schedule when a scheduled run crashes outright

## One-time setup (about 15 minutes, all on github.com)

1. **Create the repo.** github.com → organization *ola-smcm-dev* → New repository → name `liturgy-data` → **Public** → leave "Add a README" **unticked** → Create.
2. **Upload the files.** On the new repo page choose *uploading an existing file*; drag in **everything inside this folder**
   (including the hidden-looking `.github` folder). GitHub takes up to 100 files per upload — this folder is about 50. Commit to `main`.
   *If the `.github` folder did not upload:* Add file → Create new file → type `.github/workflows/update.yml/` … (the name box accepts
   slashes) and paste each of the files in `.github/` by hand (`workflows/update.yml`, `workflows/tests.yml`, `alert-people.txt`, `dependabot.yml`).
3. **Alert people.** Open `.github/alert-people.txt` → pencil icon → add two or more real GitHub usernames → Commit.
4. **Turn on the website for the data.** Settings → Pages → *Build and deployment* → Source **Deploy from a branch** → Branch `main`, folder `/ (root)` → Save.
   After a minute `https://ola-smcm-dev.github.io/liturgy-data/index.json` shows the data. (If you use a custom domain for the church site,
   this still works from any website because GitHub Pages allows cross-site reads.)
5. **Check the Action works.** Actions tab → *Tests* should be green. Then *Update liturgy data* → *Run workflow* → mode **update** → Run.
   Expected result today (before the new booklet exists): green, log says "no newer English Panchangam than 2025-2026".
   **If it turns red with "could not be reached"**, the Commission's website refuses GitHub's servers — that is an alert, not a bug in the data;
   see HANDOVER.md → "If the Commission's site blocks the robot".
6. **Test the e-mail.** Create a test issue by hand (Issues → New issue, title "test", mention both people with @username). If both
   get the e-mail, the alert path works — the robot's alerts are ordinary issues created the same way. Then delete the test issue.
7. **Security settings** — see `SECURITY.md` (two-factor sign-in for everyone, at least two owners, protect `main`).

## Local use (Windows or any computer)

```
pip install -r requirements.txt
python -m pytest -q                      # all checks
python tools/update.py --pdf "Panchangam.pdf" --id 2026-2027     # use a PDF you downloaded yourself
python tools/build.py                    # rebuild days/ and index.json from sources/
```

## Layout

```
index.json, days/            published data (written by the robot — do not edit by hand)
data/                        books, Malayalam glossary, feast-rules  (edit these by hand when needed)
sources/                     the parsed Panchangams (the robot adds one file per year)
reports/                     to-do list: celebration names that still need a Malayalam name
tools/                       reader of the Panchangam, checks, builder, robot, e-mail alerts
tests/                       automatic tests
examples/                    how the two apps read the data
.github/workflows/           the schedules
```
