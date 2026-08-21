# garmin-connect

Syncs your running activities from Garmin Connect into local CSV/JSON/Markdown
exports, so you can feed them into your **Wahyu Running Project** (a Claude
Project) for analysis.

> Note: there's no API for writing directly into a Claude Project's knowledge
> base, so this tool exports clean files instead. Upload `data/summary.md`
> (and `data/activities.csv` / `data/splits.csv` if you want raw detail) into
> your Claude Project, or paste `summary.md` into a chat with the project
> active.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and fill in GARMIN_EMAIL / GARMIN_PASSWORD
```

Credentials are read from environment variables (or `.env`, which is
gitignored) — never hardcode them in code and never commit `.env`. On first
run you log in with your password; the session token is then cached locally
(default `~/.garminconnect`, override with `GARMIN_TOKENSTORE`) so subsequent
runs don't need your password again. If your account has 2FA enabled, you'll
be prompted for the MFA code (or set `GARMIN_MFA_CODE` for non-interactive
use).

## Run a sync

```bash
python sync_garmin.py
```

By default this pulls your entire running history. Narrow it with:

```bash
python sync_garmin.py --start-date 2025-01-01 --end-date 2026-08-21
python sync_garmin.py --skip-splits   # faster: skip per-lap detail
```

## Automatic sync (no laptop needed)

A GitHub Actions workflow (`.github/workflows/garmin-sync.yml`) runs this on
a schedule (twice daily by default) and commits the updated `data/` files
back to the repo automatically — nothing to open on your phone or laptop
after a run. One-time setup, from any browser (phone is fine):

1. In this repo, go to **Settings → Secrets and variables → Actions** and
   add two repository secrets: `GARMIN_EMAIL` and `GARMIN_PASSWORD`.
2. Merge this branch into your default branch — GitHub only fires
   `schedule` triggers for workflows that live on the default branch.
3. That's it. It'll sync automatically going forward. If you want a sync
   right now, open the **Actions** tab → "Sync Garmin running data" →
   **Run workflow** (works from the GitHub mobile app too).

Adjust the cadence by editing the `cron` line in the workflow file — it's
UTC, and the minimum practical interval is about every 15-30 minutes if you
want it closer to real-time.

## Output (`data/`)

- `activities.csv` — one row per run: date, distance, duration, pace,
  elevation, HR, calories, training effect, VO2max, cadence.
- `splits.csv` — per-lap breakdown (pace/HR per split) for every run.
- `activities_raw.json` — the raw Garmin Connect payload, for anything not
  captured in the CSV.
- `trends.json` — weekly/monthly mileage and pace aggregates, plus personal
  bests (fastest pace, longest run, best week).
- `summary.md` — a human-readable digest of the above, meant to be pasted or
  uploaded straight into your Claude Project.

## Notes

- Garmin Connect has no official public API for personal use; this uses the
  community-maintained [`garminconnect`](https://github.com/cyberjunky/python-garminconnect)
  library, which can break if Garmin changes their internal endpoints. If a
  sync fails or fields look empty, check `data/activities_raw.json` for the
  actual field names Garmin is returning and adjust `garmin_sync/transform.py`
  if needed.
- Re-running the sync overwrites the files in `data/` with your latest full
  history (safe and idempotent).

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests cover the transform/export logic (CSV rows, pace math, weekly/monthly
aggregation, personal bests) using fixture data — they don't hit the live
Garmin API.
