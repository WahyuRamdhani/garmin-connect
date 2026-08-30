#!/usr/bin/env python3
"""Sync the two most recent Garmin Connect running activities into local export files.

Usage:
    python sync_garmin.py [--output-dir data] [--skip-splits] [--skip-detail] [--skip-charts]

Reads GARMIN_EMAIL / GARMIN_PASSWORD from the environment (or a .env file).
Fetches the two most recent running activities and replaces --output-dir with
full detail for both, including the app's Charts-tab data.
summary.md is a single self-contained report (stats, splits, HR zones,
full chart-data samples) meant to be the one file you upload into your
Claude Project; activity.csv/splits.csv/timeseries.csv/hr_zones.csv and
the raw JSON payloads are also written alongside it for anyone who wants
the pieces separately. Nothing accumulates between runs; each sync starts
from a clean output directory.
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from garmin_sync.client import (
    fetch_activity_detail,
    fetch_activity_timeseries,
    fetch_hr_zones,
    fetch_recent_running_activities,
    fetch_scheduled_workout_detail,
    fetch_training_plan_detail,
    fetch_splits,
    fetch_training_plan_schedule,
    login,
)
from garmin_sync.export import write_csv, write_json, write_run_summary_md
from garmin_sync.transform import (
    activity_to_row,
    extract_detail_fields,
    hr_zones_to_rows,
    splits_to_rows,
    training_plan_to_rows,
    timeseries_to_rows,
    workout_detail_to_summary,
)


def sync_training_plan(
    garmin: Any, out_dir: Path, reference_date: str
) -> list[dict[str, Any]]:
    """Fetch and export the Garmin Coach week containing ``reference_date``."""
    plan_data = fetch_training_plan_schedule(garmin, reference_date)
    rows = training_plan_to_rows(plan_data)
    write_json(out_dir / "coach_schedule_raw.json", plan_data)
    write_csv(out_dir / "coach_schedule.csv", rows)
    return rows


def sync_training_plan_details(
    garmin: Any,
    out_dir: Path,
    schedule_rows: list[dict[str, Any]],
    reference_date: str,
) -> list[dict[str, Any]]:
    """Fetch step definitions for unrevealed workouts on/after the reference date."""
    raw_details: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    schedule_path = out_dir / "coach_schedule_raw.json"
    schedule_payload = json.loads(schedule_path.read_text()) if schedule_path.exists() else {}
    plan_ids = {
        plan.get("trainingPlanId")
        for plan in schedule_payload.get("trainingPlanWorkoutScheduleDTOS") or []
        if plan.get("trainingPlanId") is not None
    }
    for plan_id in sorted(plan_ids):
        detail = fetch_training_plan_detail(garmin, plan_id)
        if detail:
            raw_details.append(detail)
            summary = workout_detail_to_summary(detail)
            if summary.get("segments"):
                summaries.append(summary)

    # Some non-adaptive plans expose individual workout definitions instead of
    # embedding them in the plan detail; use those as a fallback.
    if not raw_details:
        for item in schedule_rows:
            if item.get("completed") or (item.get("date") or "") < reference_date:
                continue
            workout_id = item.get("workout_id")
            if workout_id is None:
                continue
            detail = fetch_scheduled_workout_detail(garmin, workout_id)
            if detail:
                raw_details.append(detail)
                summaries.append(workout_detail_to_summary(detail))
    write_json(out_dir / "coach_workout_details.json", raw_details)
    write_json(out_dir / "coach_training_plan_details.json", raw_details)
    return summaries


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
    parser.add_argument(
        "--skip-charts",
        action="store_true",
        help=(
            "Skip fetching Charts-tab data (second-by-second pace/HR/elevation "
            "samples and HR zone breakdown) - faster, fewer API calls, smaller export"
        ),
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    out_dir = Path(args.output_dir)

    print("Logging in to Garmin Connect...")
    garmin = login()

    print("Fetching the two most recent running activities...")
    activities = fetch_recent_running_activities(garmin, limit=2)
    if not activities:
        print("No running activities found on this account.")
        return

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    rows = []
    reports = []
    for activity in activities:
        row = activity_to_row(activity)
        activity_id = row["activity_id"]
        prefix = f"activity_{activity_id}"
        write_json(out_dir / f"{prefix}_raw.json", activity)

        split_rows = []
        if not args.skip_splits:
            split_rows = splits_to_rows(activity_id, fetch_splits(garmin, activity_id))
        write_csv(out_dir / f"{prefix}_splits.csv", split_rows)

        if not args.skip_detail:
            detail = fetch_activity_detail(garmin, activity_id)
            if detail:
                write_json(out_dir / f"{prefix}_detail_raw.json", detail)
                row.update(extract_detail_fields(detail))

        timeseries_rows = []
        hr_zone_rows = []
        if not args.skip_charts:
            timeseries_rows = timeseries_to_rows(fetch_activity_timeseries(garmin, activity_id))
            hr_zone_rows = hr_zones_to_rows(fetch_hr_zones(garmin, activity_id))
        write_csv(out_dir / f"{prefix}_timeseries.csv", timeseries_rows)
        write_csv(out_dir / f"{prefix}_hr_zones.csv", hr_zone_rows)
        write_run_summary_md(
            out_dir / f"{prefix}_summary.md", row, split_rows, hr_zone_rows, timeseries_rows
        )
        rows.append(row)
        reports.append((row, split_rows, hr_zone_rows, timeseries_rows))

    # Keep the historical filenames as aliases for the newest activity while
    # activity.csv now contains both runs and every run has its own files.
    latest_row, latest_splits, latest_zones, latest_timeseries = reports[0]
    write_json(out_dir / "activity_raw.json", activities[0])
    latest_detail_path = out_dir / f"activity_{latest_row['activity_id']}_detail_raw.json"
    if latest_detail_path.exists():
        shutil.copyfile(latest_detail_path, out_dir / "activity_detail_raw.json")
    write_csv(out_dir / "splits.csv", latest_splits)
    write_csv(out_dir / "timeseries.csv", latest_timeseries)
    write_csv(out_dir / "hr_zones.csv", latest_zones)

    schedule_reference_date = datetime.now(ZoneInfo("Asia/Jakarta")).date().isoformat()
    print(f"Fetching Garmin Coach schedule for the week containing {schedule_reference_date}...")
    coach_schedule_rows = sync_training_plan(garmin, out_dir, schedule_reference_date)
    coach_workout_details = sync_training_plan_details(
        garmin, out_dir, coach_schedule_rows, schedule_reference_date
    )

    write_csv(out_dir / "activity.csv", rows)
    write_run_summary_md(
        out_dir / "summary.md",
        latest_row,
        latest_splits,
        latest_zones,
        latest_timeseries,
        coach_schedule_rows,
        schedule_reference_date,
        coach_workout_details,
    )

    print(f"\nDone. {len(rows)} latest runs exported to {out_dir}/")
    print("  - summary.md  <- upload just this one file to your Claude Project")
    print("  - activity.csv, activity_raw.json, activity_detail_raw.json")
    print(f"  - splits.csv ({len(latest_splits)} laps)")
    print(f"  - timeseries.csv ({len(latest_timeseries)} samples), hr_zones.csv")
    print(f"  - coach_schedule.csv ({len(coach_schedule_rows)} workouts), coach_schedule_raw.json")
    print(f"  - coach_workout_details.json ({len(coach_workout_details)} workouts with steps)")


if __name__ == "__main__":
    main()
