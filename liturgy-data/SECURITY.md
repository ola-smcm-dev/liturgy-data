# Security checklist

The data is public and the robot can change the repository, so the controls are about **who can change it** and **what the robot is allowed to do**.

## Built into the repo
- [x] **No secrets anywhere.** The robot uses only GitHub's per-run token; no passwords, API keys, or mail credentials exist. Nothing to leak or expire.
- [x] **Least privilege.** Each workflow lists its permissions explicitly (`contents: write`, `issues: write`, `actions: write` for the update workflow; `contents: read` for tests). Everything else is denied.
- [x] **Fixed download source.** `tools/update.py` only fetches `https://` URLs on `www.syromalabarliturgy.org` (including redirects), caps the size (60 MB), requires a real PDF, and never runs anything it downloads.
- [x] **Validate before publish.** A new year is committed only if every check passes; otherwise nothing changes and people are alerted. A failed rebuild restores the previous files.
- [x] **Data is text only.** Apps must display it with `textContent`/escaping. A test fails if any reading text contains `<` or `>`.
- [x] **No PDFs stored** (`*.pdf` is git-ignored) — nothing re-hosted.
- [x] **No personal data** in the repo, by design.
- [x] **Fork-safe.** The workflow only runs for the `ola-smcm-dev` organization.
- [x] **Dependencies pinned/limited** (`pdfplumber==0.11.10`, pytest <9); Dependabot opens monthly pull requests for GitHub Actions and Python packages (review and merge them — tests run on each).

## Settings for the owners to switch on (github.com, one time)
- [ ] **Two-factor authentication** for every person in the organization (Organization → Settings → Authentication security → *Require two-factor authentication*). This is the single most important control.
- [ ] **At least two organization owners / repo admins**, so the repo is not lost if one person leaves.
- [ ] **Only trusted people have write access** (Settings → Collaborators). Outside people can still open issues and pull requests, which need approval.
- [ ] **Protect `main`** (Settings → Rules → Rulesets → New branch ruleset → target `main`): block force-pushes and deletion. *Do not* require pull requests for it, or the robot cannot commit; if you want reviews on human changes, add "bypass: GitHub Actions" for the robot.
- [ ] **Actions → General:** *Allow actions created by GitHub and verified creators* (the workflows use only `actions/checkout` and `actions/setup-python`); *Require approval for pull requests from outside collaborators*.
- [ ] **Settings → Security:** enable *Dependabot alerts* and *Secret scanning* (both free for public repositories).
- [ ] Keep at least one person's e-mail on `.github/alert-people.txt` who actually reads it.

## Honest limits
- The Commission's website is trusted as the source. If it were hacked and published a bad PDF, the checks would catch a broken file but not a wrong-but-well-formed reading. The one-line titles are shown to children and parishioners; the website should keep the "Commission's page" link next to them.
- GitHub Pages is public; anyone can read the data (that is the point).
- Scheduled workflows are switched off by GitHub after 60 days without repository activity. The monthly health run re-enables the schedule itself and the Dec 21 / 45-day alerts cover the failure case. A yearly look at the Actions tab each November is still recommended.
