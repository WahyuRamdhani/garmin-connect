# garmin-connect

Syncs your **latest** Garmin Connect running activity into local CSV/JSON/
Markdown exports, so you can feed it into your **Wahyu Running Project** (a
Claude Project) for analysis.

Each sync fetches only the single most recent run and replaces `data/` with
it — nothing accumulates between syncs, so the repo stays small. No trend
history or personal bests are tracked; if you want those back later, say so.

> Note: there's no API for writing directly into a Claude Project's knowledge
> base, so this tool exports clean files instead. Upload `data/summary.md`
> (and `data/activity.csv` / `data/splits.csv` if you want raw detail) into
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
python sync_garmin.py --skip-splits   # faster: skip per-lap detail
python sync_garmin.py --skip-detail   # faster: skip best pace/stride/intensity minutes
```

Three API calls total (activity lookup, splits, extended detail) — light
enough to run as often as you like.

## Manual sync from your phone

A GitHub Actions workflow (`.github/workflows/garmin-sync.yml`) runs this
on demand and commits the updated `data/` files back to the repo — no
laptop needed. One-time setup, from any browser (phone is fine):

1. In this repo, go to **Settings → Secrets and variables → Actions** and
   add two repository secrets: `GARMIN_EMAIL` and `GARMIN_PASSWORD`.
2. That's it. To sync after a run, open the **Actions** tab (in the GitHub
   mobile app or in a browser) → "Sync Garmin running data" →
   **Run workflow**.

There's no schedule — it only runs when you trigger it.

## Output (`data/`)

- `activity.csv` — one row for your latest run: date, distance, duration,
  avg/best pace, elevation, HR, calories (total/active/resting), training
  effect, VO2max, cadence, stride length, moderate/vigorous/total intensity
  minutes, sweat loss estimate — everything Garmin Connect's Stats tab shows.
- `splits.csv` — per-lap breakdown (pace/HR per split) for that run.
- `activity_raw.json` — the raw Garmin Connect list-view payload for the run.
- `activity_detail_raw.json` — the raw per-activity detail payload, for
  anything not already pulled into the CSV.
- `summary.md` — a human-readable digest of the above, meant to be pasted or
  uploaded straight into your Claude Project.

Not included: the second-by-second pace/HR/elevation chart data behind the
**Charts** tab in the app, and the Time-in-HR-Zones breakdown. Those come
from a separate, heavier endpoint — ask if you want either added.

## Notes

- Garmin Connect has no official public API for personal use; this uses the
  community-maintained [`garminconnect`](https://github.com/cyberjunky/python-garminconnect)
  library, which can break if Garmin changes their internal endpoints. If a
  sync fails or fields look empty, check `data/activity_raw.json` /
  `data/activity_detail_raw.json` for the actual field names Garmin is
  returning and adjust `garmin_sync/transform.py` if needed.
- Re-running the sync replaces everything in `data/` with your latest run
  (safe and idempotent) — it does not append or keep history.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests cover the transform/export logic (CSV rows, pace math, Markdown
summary rendering) using fixture data — they don't hit the live Garmin API.
