"""Write a synced run's data to CSV, JSON, and a Markdown summary."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

# (label, row key, unit) for the fields shown in the Markdown summary, in display order.
_SUMMARY_FIELDS: list[tuple[str, str, str]] = [
    ("Distance", "distance_km", "km"),
    ("Duration", "duration_min", "min"),
    ("Moving duration", "moving_duration_min", "min"),
    ("Avg pace", "avg_pace_min_per_km", "min/km"),
    ("Best pace", "best_pace_min_per_km", "min/km"),
    ("Elevation gain", "elevation_gain_m", "m"),
    ("Elevation loss", "elevation_loss_m", "m"),
    ("Avg HR", "avg_hr", "bpm"),
    ("Max HR", "max_hr", "bpm"),
    ("Calories", "calories", "kcal"),
    ("Active calories", "active_calories", "kcal"),
    ("Resting calories", "resting_calories", "kcal"),
    ("Training effect", "training_effect_label", ""),
    ("Aerobic training effect", "aerobic_training_effect", ""),
    ("Anaerobic training effect", "anaerobic_training_effect", ""),
    ("VO2max", "vo2max", ""),
    ("Avg cadence", "avg_cadence_spm", "spm"),
    ("Max cadence", "max_cadence_spm", "spm"),
    ("Avg stride length", "avg_stride_length_m", "m"),
    ("Moderate intensity", "moderate_intensity_min", "min"),
    ("Vigorous intensity", "vigorous_intensity_min", "min"),
    ("Total intensity", "total_intensity_min", "min"),
    ("Sweat loss", "sweat_loss_ml", "mL"),
]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))


def write_run_summary_md(
    path: Path,
    row: dict[str, Any],
    splits: list[dict[str, Any]],
    hr_zones: list[dict[str, Any]] | None = None,
) -> None:
    """Write a human-readable digest of the latest run, meant to be pasted or
    uploaded straight into a Claude Project."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# Latest run - {row.get('name') or 'Run'}", ""]
    start_time = row.get("start_time")
    date_line = f"Date: {row.get('date')}"
    if start_time:
        date_line += f" ({start_time})"
    lines.append(date_line)
    lines.append("")

    lines.append("## Summary")
    for label, key, unit in _SUMMARY_FIELDS:
        value = row.get(key)
        if value is None:
            continue
        lines.append(f"- {label}: {value}{(' ' + unit) if unit else ''}")
    lines.append("")

    if splits:
        lines.append("## Splits")
        lines.append("| # | Distance (km) | Duration (min) | Pace (min/km) | Avg HR | Max HR | Elev gain (m) |")
        lines.append("|---|---|---|---|---|---|---|")
        for s in splits:
            lines.append(
                f"| {s['split_index']} | {s['distance_km']} | {s['duration_min']} | "
                f"{s['pace_min_per_km']} | {s['avg_hr']} | {s['max_hr']} | {s['elevation_gain_m']} |"
            )
        lines.append("")

    if hr_zones:
        lines.append("## Time in Heart Rate Zones")
        lines.append("| Zone | Low bound (bpm) | Duration (min) | % of run |")
        lines.append("|---|---|---|---|")
        for z in hr_zones:
            lines.append(f"| {z['zone']} | {z['low_bpm']} | {z['duration_min']} | {z['percent']}% |")
        lines.append("")

    path.write_text("\n".join(lines))
