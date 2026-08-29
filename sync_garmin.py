#!/usr/bin/env python3
"""Sync your latest Garmin Connect running activity into local export files.

Usage:
    python sync_garmin.py [--output-dir data] [--skip-splits] [--skip-detail] [--skip-charts]

Reads GARMIN_EMAIL / GARMIN_PASSWORD from the environment (or a .env file).
Fetches only the single most recent running activity and replaces
--output-dir with its full detail, including the app's Charts-tab data.
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
    fetch_latest_running_activity,
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

    timeseries_rows = []
    hr_zone_rows = []
    if not args.skip_charts:
        timeseries = fetch_activity_timeseries(garmin, row["activity_id"])
        timeseries_rows = timeseries_to_rows(timeseries)
        write_csv(out_dir / "timeseries.csv", timeseries_rows)

        hr_zones = fetch_hr_zones(garmin, row["activity_id"])
        hr_zone_rows = hr_zones_to_rows(hr_zones)
        write_csv(out_dir / "hr_zones.csv", hr_zone_rows)

    schedule_reference_date = datetime.now(ZoneInfo("Asia/Jakarta")).date().isoformat()
    print(f"Fetching Garmin Coach schedule for the week containing {schedule_reference_date}...")
    coach_schedule_rows = sync_training_plan(garmin, out_dir, schedule_reference_date)
    coach_workout_details = sync_training_plan_details(
        garmin, out_dir, coach_schedule_rows, schedule_reference_date
    )

    write_csv(out_dir / "activity.csv", [row])
    write_run_summary_md(
        out_dir / "summary.md",
        row,
        split_rows,
        hr_zone_rows,
        timeseries_rows,
        coach_schedule_rows,
        schedule_reference_date,
        coach_workout_details,
    )

    print(f"\nDone. Latest run ({row['date']} - {row['name']}) exported to {out_dir}/")
    print("  - summary.md  <- upload just this one file to your Claude Project")
    print("  - activity.csv, activity_raw.json, activity_detail_raw.json")
    print(f"  - splits.csv ({len(split_rows)} laps)")
    print(f"  - timeseries.csv ({len(timeseries_rows)} samples), hr_zones.csv")
    print(f"  - coach_schedule.csv ({len(coach_schedule_rows)} workouts), coach_schedule_raw.json")
    print(f"  - coach_workout_details.json ({len(coach_workout_details)} workouts with steps)")


if __name__ == "__main__":
    main()
