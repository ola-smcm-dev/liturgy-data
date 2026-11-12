# Handover — for whoever looks after this next

This system is built to run for years with no attention. This file is for the days when it asks for help.

## What normally happens
Every year in mid-November to early December the Syro-Malabar Liturgy Commission publishes the next Panchangam (a PDF) at
https://www.syromalabarliturgy.org/liturgical_texts . The robot (GitHub Action "Update liturgy data") notices it, reads it,
checks it and publishes `days/<year>.json`. The website and the TV app pick it up. Nobody has to do anything.

## You got an e-mail. What now?
Open the issue linked in the e-mail; it says what happened and nothing wrong has been published. Find your case:

| Issue title says | Meaning | What to do |
|---|---|---|
| "…could not be reached" | The Commission's website refused or is down | Wait a day (it retries daily until 20 Dec). If it keeps failing see "If the Commission's site blocks the robot" |
| "…looks different now" / "could not be parsed" / "could not be read safely" | The new PDF's layout changed, or the file has a mistake | Download the PDF yourself, run `python tools/update.py --pdf file.pdf --id 2026-2027` on a computer; read the error. If it is a new layout, the parser (`tools/panchangam_parser.py`) must be adapted — ask a developer, share this repo and the PDF. Until then the apps show "readings not available" after the old data ends, with the link to the Commission's page. |
| "…next year's readings are still missing" (21 Dec) | Nothing new found by 21 Dec | Check the Commission's page by hand. If the PDF is there → run the workflow by hand / use `--pdf`. If it is not published yet, use the Commission's site for daily readings and re-run the workflow when it appears (it also runs on the 1st of every month). |
| "…failed the final checks" (e.g. *unknown Bible book 'Zec'*) | The new year was read, but something in it would confuse the apps; it was rolled back | If it names an unknown book spelling: open `data/books.json`, add that spelling to the `aliases` of the right book, then run the workflow again. Other messages: read the log, or ask a developer. |
| "…built but could not be saved" | The data passed, but GitHub refused the save | A branch rule on `main` blocks the robot. Only "Restrict deletions" and "Block force pushes" should be on (see SECURITY.md). Fix the rule, run the workflow again. |
| "…published — N date(s) need a look" | Published, but N days had an odd layout | Optional: compare those dates with the PDF. Apps show a link to the Commission's page for them. Fix by editing `sources/<year>.json` for that date, then run `python tools/build.py` and commit. |
| "Liturgy data … published" | Success note | Nothing. (Optionally fill in Malayalam names listed in `reports/untranslated-celebrations.txt`.) |

## If the Commission's site blocks the robot
GitHub's servers are shared; a website may refuse them. If the first test run (and every later one) fails to reach the page:
1. Someone downloads the PDF each year and runs `python tools/update.py --pdf file.pdf --id YYYY-YYYY`, then commits `sources/`, `days/`, `index.json`; **or**
2. add the PDF to the repo temporarily (never leave it there; `*.pdf` is in `.gitignore`) and run the same command in the Action; **or**
3. ask the Commission office for an e-mail contact for the English Panchangam.

## Things you may need to edit by hand
* **Feast days:** `data/feast-rules.json`. Fixed feasts: `"date": "MM-DD"`. Movable feasts: `"rule"` such as "Third Friday of Apostles" or "Sixth Thursday after Easter".
  Run `python -m pytest` after editing: it checks every rule resolves for the next 15 years. The website's old SyroMalabarDates sheet is no longer needed once the website reads this repo.
* **Malayalam:** `data/books.json` (Bible book names), `data/glossary-ml.json` (seasons and feast names). Must be proofread by a Malayalam reader.
* **Who gets e-mailed:** `.github/alert-people.txt`.
* **Season dates:** the printed banners in the Panchangam win; `tools/calendar_rules.py` is the fallback. The build prints a warning (in the issue) when they disagree.

## Why the parser can fail, and what is checked
The PDF has no machine-readable structure, so `tools/panchangam_parser.py` reads fonts and positions (bold left-margin line = new date, indented bold = another celebration,
italic = note, plain = reading). It supports the 2024-25 and 2025-26 print layout (and so, hopefully, 2026-27). Older booklets (before 2024) use a different layout and are not supported.
`tools/validate.py` stops anything bad from going live (and `tools/checks.py` re-checks the finished files — tidy references, known books, seasons, no gaps — and rolls everything back if one fails): every date present, ≥ 330 days, readings on ≥ 97 % of days, first/last dates right, 4 readings on Sundays, titles that look like titles.

## Where the pieces are
`tools/update.py` (the robot) → `tools/panchangam_parser.py` → `tools/validate.py` → `tools/build.py` → `days/`, `index.json`.
`tools/notify.py` turns a result into the e-mail (GitHub issue). `tests/` has ~40 tests; they run on every change and before every robot run.

## Cost
Free. Public repository: GitHub Actions minutes, Pages hosting and e-mail notifications cost nothing. A run takes about a minute.
