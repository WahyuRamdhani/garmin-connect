#!/usr/bin/env python3
"""Sync your latest Garmin Connect running activity into local export files.

Usage:
    python sync_garmin.py [--output-dir data] [--skip-splits] [--skip-detail]

Reads GARMIN_EMAIL / GARMIN_PASSWORD from the environment (or a .env file).
Fetches only the single most recent running activity and replaces
--output-dir with its full detail: activity.csv, activity_raw.json,
activity_detail_raw.json, splits.csv, and summary.md - ready to upload into
your Claude Project's knowledge base for analysis. Nothing accumulates
between runs; each sync starts from a clean output directory.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from dotenv import load_dotenv

from garmin_sync.client import (
    fetch_activity_detail,
    fetch_latest_running_activity,
    fetch_splits,
    login,
)
from garmin_sync.export import write_csv, write_json, write_run_summary_md
from garmin_sync.transform import activity_to_row, extract_detail_fields, splits_to_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=str, default="data")
    parser.add_argument(
        "--skip-splits",
        action="store_true",
        help="Skip fetching per-lap splits (faster, fewer API calls)",
    )
    parser.add_argument(
        "--skip-detail",
        action="store_true",
        help=(
            "Skip fetching extended detail (best pace, stride length, "
            "intensity minutes, sweat loss) - faster, fewer API calls"
        ),
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    out_dir = Path(args.output_dir)

    print("Logging in to Garmin Connect...")
    garmin = login()

    print("Fetching latest running activity...")
    activity = fetch_latest_running_activity(garmin)
    if not activity:
        print("No running activities found on this account.")
        return

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    row = activity_to_row(activity)
    write_json(out_dir / "activity_raw.json", activity)

    split_rows = []
    if not args.skip_splits:
        laps = fetch_splits(garmin, row["activity_id"])
        split_rows = splits_to_rows(row["activity_id"], laps)
    write_csv(out_dir / "splits.csv", split_rows)

    if not args.skip_detail:
        detail = fetch_activity_detail(garmin, row["activity_id"])
        if detail:
            write_json(out_dir / "activity_detail_raw.json", detail)
            row.update(extract_detail_fields(detail))

    write_csv(out_dir / "activity.csv", [row])
    write_run_summary_md(out_dir / "summary.md", row, split_rows)

    print(f"\nDone. Latest run ({row['date']} - {row['name']}) exported to {out_dir}/")
    print("  - activity.csv, activity_raw.json, activity_detail_raw.json")
    print(f"  - splits.csv ({len(split_rows)} laps)")
    print("  - summary.md")


if __name__ == "__main__":
    main()
