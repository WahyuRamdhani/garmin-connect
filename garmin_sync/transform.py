"""Turn a raw Garmin Connect activity payload into a flat row."""
from __future__ import annotations

from typing import Any, Iterable


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


# Garmin's per-activity detail endpoint is undocumented and inconsistent about
# whether a field sits at the top level or nested under summaryDTO, so each
# metric lists candidate key names and we take the first one present.
_DETAIL_FIELD_CANDIDATES = {
    "moderate_intensity_min": ("moderateIntensityMinutes",),
    "vigorous_intensity_min": ("vigorousIntensityMinutes",),
    "sweat_loss_ml": ("waterEstimated", "sweatLossInMilliliters", "sweatLoss"),
    "active_calories": ("activeKilocalories", "burnedKilocalories"),
    "resting_calories": ("bmrCalories", "restingCalories"),
}
_MAX_SPEED_KEYS = ("maxSpeed",)
_STRIDE_LENGTH_KEYS = ("avgStrideLength", "strideLength")  # Garmin returns this in centimeters


def _first_present(detail: dict[str, Any], keys: tuple[str, ...]) -> Any:
    summary = detail.get("summaryDTO") or {}
    for key in keys:
        if detail.get(key) is not None:
            return detail[key]
        if summary.get(key) is not None:
            return summary[key]
    return None


def extract_detail_fields(detail: dict[str, Any]) -> dict[str, Any]:
    """Pull the extra Stats-tab metrics (best pace, stride length, intensity
    minutes, sweat loss, calorie breakdown) out of a get_activity() payload.
    Any field Garmin doesn't return comes back as None rather than erroring.
    """
    if not detail:
        return {}

    fields = {name: _first_present(detail, keys) for name, keys in _DETAIL_FIELD_CANDIDATES.items()}

    max_speed = _first_present(detail, _MAX_SPEED_KEYS)
    fields["best_pace_min_per_km"] = round(1000 / (max_speed * 60), 2) if max_speed else None

    stride_length_cm = _first_present(detail, _STRIDE_LENGTH_KEYS)
    fields["avg_stride_length_m"] = round(stride_length_cm / 100, 3) if stride_length_cm else None

    moderate = fields["moderate_intensity_min"]
    vigorous = fields["vigorous_intensity_min"]
    fields["total_intensity_min"] = (
        (moderate or 0) + 2 * (vigorous or 0) if moderate is not None or vigorous is not None else None
    )

    return fields


def merge_detail(row: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
    return {**row, **extract_detail_fields(detail)}


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


def timeseries_to_rows(details: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten a get_activity_details() payload (the Charts tab's raw samples)
    into one row per sample. Column names come straight from Garmin's own
    metricDescriptors, so this works regardless of exactly which metrics a
    given activity type includes. Adds an elapsed_s column (seconds since the
    first sample) when a timestamp-like field is present, for readability.
    """
    descriptors = details.get("metricDescriptors") or []
    ordered_keys = [
        d.get("key") for d in sorted(descriptors, key=lambda d: d.get("metricsIndex", 0))
    ]
    samples = details.get("activityDetailMetrics") or []
    rows = [dict(zip(ordered_keys, sample.get("metrics") or [])) for sample in samples]

    timestamp_key = next((k for k in ordered_keys if k and "timestamp" in k.lower()), None)
    if timestamp_key and rows:
        first_ts = rows[0].get(timestamp_key)
        if isinstance(first_ts, (int, float)):
            for row in rows:
                ts = row.get(timestamp_key)
                row["elapsed_s"] = round((ts - first_ts) / 1000, 1) if isinstance(ts, (int, float)) else None

    return rows


def hr_zones_to_rows(zones: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Turn a get_activity_hr_in_timezones() payload into the Time-in-HR-Zones
    breakdown shown in the app (zone, low bound, minutes, percent of run).
    """
    zones = list(zones)
    if not zones:
        return []
    total_secs = sum(z.get("secsInZone") or 0 for z in zones)
    rows = []
    for z in zones:
        secs = z.get("secsInZone") or 0
        rows.append(
            {
                "zone": z.get("zoneNumber"),
                "low_bpm": z.get("zoneLowBoundary"),
                "duration_min": round(secs / 60, 2),
                "percent": round(100 * secs / total_secs, 1) if total_secs else None,
            }
        )
    return rows
