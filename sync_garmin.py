#!/usr/bin/env python3
"""Sync running activities from Garmin Connect into local export files.

Usage:
    python sync_garmin.py [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD]
                           [--output-dir data] [--skip-splits]

Reads GARMIN_EMAIL / GARMIN_PASSWORD from the environment (or a .env file).
Writes activities.csv, activities_raw.json, splits.csv, trends.json, and
summary.md into --output-dir, ready to upload into your Claude Project's
knowledge base for analysis.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

from garmin_sync.client import fetch_running_activities, fetch_splits, login
from garmin_sync.export import write_csv, write_json, write_summary_md
from garmin_sync.transform import (
    activities_to_rows,
    monthly_trends,
    personal_bests,
    splits_to_rows,
    weekly_trends,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", type=str, default="2000-01-01")
    parser.add_argument("--end-date", type=str, default=date.today().isoformat())
    parser.add_argument("--output-dir", type=str, default="data")
    parser.add_argument(
        "--skip-splits",
        action="store_true",
        help="Skip fetching per-lap splits (faster, fewer API calls)",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
    out_dir = Path(args.output_dir)

    print("Logging in to Garmin Connect...")
    garmin = login()

    print(f"Fetching running activities from {start_date} to {end_date}...")
    activities = fetch_running_activities(garmin, start_date, end_date)
    print(f"Found {len(activities)} running activities.")

    rows = activities_to_rows(activities)
    write_csv(out_dir / "activities.csv", rows)
    write_json(out_dir / "activities_raw.json", activities)

    split_rows = []
    if not args.skip_splits:
        print("Fetching splits for each activity...")
        for row in rows:
            laps = fetch_splits(garmin, row["activity_id"])
            split_rows.extend(splits_to_rows(row["activity_id"], laps))
    write_csv(out_dir / "splits.csv", split_rows)

    weekly = weekly_trends(rows)
    monthly = monthly_trends(rows)
    bests = personal_bests(rows)
    write_json(out_dir / "trends.json", {"weekly": weekly, "monthly": monthly, "personal_bests": bests})
    write_summary_md(out_dir / "summary.md", rows, weekly, monthly, bests)

    print(f"\nDone. Exports written to {out_dir}/")
    print(f"  - activities.csv, activities_raw.json ({len(rows)} runs)")
    print(f"  - splits.csv ({len(split_rows)} laps)")
    print("  - trends.json, summary.md")


if __name__ == "__main__":
    main()
