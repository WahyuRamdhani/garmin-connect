"""Turn raw Garmin Connect activity payloads into flat rows and trend summaries."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Iterable


def _meters_to_km(value: float | None) -> float | None:
    return round(value / 1000, 3) if value else value


def _seconds_to_min(value: float | None) -> float | None:
    return round(value / 60, 2) if value else value


def _pace_min_per_km(duration_s: float | None, distance_m: float | None) -> float | None:
    if not duration_s or not distance_m:
        return None
    return round((duration_s / 60) / (distance_m / 1000), 2)


def activity_to_row(activity: dict[str, Any]) -> dict[str, Any]:
    distance_m = activity.get("distance")
    duration_s = activity.get("duration")
    start = activity.get("startTimeLocal", "") or ""

    return {
        "activity_id": activity.get("activityId"),
        "date": start.split(" ")[0] if start else None,
        "start_time": start,
        "name": activity.get("activityName"),
        "distance_km": _meters_to_km(distance_m),
        "duration_min": _seconds_to_min(duration_s),
        "moving_duration_min": _seconds_to_min(activity.get("movingDuration")),
        "avg_pace_min_per_km": _pace_min_per_km(duration_s, distance_m),
        "elevation_gain_m": activity.get("elevationGain"),
        "elevation_loss_m": activity.get("elevationLoss"),
        "avg_hr": activity.get("averageHR"),
        "max_hr": activity.get("maxHR"),
        "calories": activity.get("calories"),
        "aerobic_training_effect": activity.get("aerobicTrainingEffect"),
        "anaerobic_training_effect": activity.get("anaerobicTrainingEffect"),
        "training_effect_label": activity.get("trainingEffectLabel"),
        "vo2max": activity.get("vO2MaxValue"),
        "avg_cadence_spm": activity.get("averageRunningCadenceInStepsPerMinute"),
        "max_cadence_spm": activity.get("maxRunningCadenceInStepsPerMinute"),
    }


def activities_to_rows(activities: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [activity_to_row(a) for a in activities]
    rows.sort(key=lambda r: r["date"] or "")
    return rows


def split_to_row(activity_id: int, index: int, lap: dict[str, Any]) -> dict[str, Any]:
    distance_m = lap.get("distance")
    duration_s = lap.get("duration")
    return {
        "activity_id": activity_id,
        "split_index": index,
        "distance_km": _meters_to_km(distance_m),
        "duration_min": _seconds_to_min(duration_s),
        "pace_min_per_km": _pace_min_per_km(duration_s, distance_m),
        "avg_hr": lap.get("averageHR"),
        "max_hr": lap.get("maxHR"),
        "elevation_gain_m": lap.get("elevationGain"),
    }


def splits_to_rows(activity_id: int, laps: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [split_to_row(activity_id, i + 1, lap) for i, lap in enumerate(laps)]


def _week_key(iso_date: str) -> str:
    d = datetime.strptime(iso_date, "%Y-%m-%d").date()
    year, week, _ = d.isocalendar()
    return f"{year}-W{week:02d}"


def _month_key(iso_date: str) -> str:
    return iso_date[:7]


def _aggregate(rows: list[dict[str, Any]], key_fn: Callable[[str], str]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if not row["date"]:
            continue
        buckets[key_fn(row["date"])].append(row)

    result = []
    for key in sorted(buckets):
        group = buckets[key]
        total_km = sum(r["distance_km"] or 0 for r in group)
        total_min = sum(r["duration_min"] or 0 for r in group)
        result.append(
            {
                "period": key,
                "runs": len(group),
                "distance_km": round(total_km, 2),
                "duration_min": round(total_min, 1),
                "avg_pace_min_per_km": round(total_min / total_km, 2) if total_km else None,
            }
        )
    return result


def weekly_trends(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _aggregate(rows, _week_key)


def monthly_trends(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _aggregate(rows, _month_key)


def personal_bests(rows: list[dict[str, Any]]) -> dict[str, Any]:
    timed = [r for r in rows if r["distance_km"] and r["avg_pace_min_per_km"]]
    if not timed:
        return {}

    fastest = min(timed, key=lambda r: r["avg_pace_min_per_km"])
    longest = max(rows, key=lambda r: r["distance_km"] or 0)
    weekly = weekly_trends(rows)
    best_week = max(weekly, key=lambda w: w["distance_km"]) if weekly else None

    return {
        "fastest_pace": fastest,
        "longest_run": longest,
        "best_week": best_week,
    }
