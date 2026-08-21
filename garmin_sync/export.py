"""Write synced Garmin data to CSV, JSON, and a Markdown summary."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


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


def write_summary_md(
    path: Path,
    rows: list[dict[str, Any]],
    weekly: list[dict[str, Any]],
    monthly: list[dict[str, Any]],
    bests: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Wahyu Running Project - Garmin Sync Summary", ""]

    total_km = sum(r["distance_km"] or 0 for r in rows)
    lines.append(f"Total runs: {len(rows)}")
    lines.append(f"Total distance: {total_km:.1f} km")
    lines.append("")

    if bests:
        lines.append("## Personal bests")
        fastest = bests.get("fastest_pace")
        longest = bests.get("longest_run")
        best_week = bests.get("best_week")
        if fastest:
            lines.append(
                f"- Fastest average pace: {fastest['avg_pace_min_per_km']} min/km "
                f"({fastest['distance_km']} km on {fastest['date']})"
            )
        if longest:
            lines.append(f"- Longest run: {longest['distance_km']} km on {longest['date']}")
        if best_week:
            lines.append(
                f"- Best week: {best_week['distance_km']} km across "
                f"{best_week['runs']} runs ({best_week['period']})"
            )
        lines.append("")

    lines.append("## Monthly trends")
    lines.append("| Month | Runs | Distance (km) | Avg pace (min/km) |")
    lines.append("|---|---|---|---|")
    for m in monthly:
        lines.append(f"| {m['period']} | {m['runs']} | {m['distance_km']} | {m['avg_pace_min_per_km']} |")
    lines.append("")

    lines.append("## Weekly trends (last 12 weeks)")
    lines.append("| Week | Runs | Distance (km) | Avg pace (min/km) |")
    lines.append("|---|---|---|---|")
    for w in weekly[-12:]:
        lines.append(f"| {w['period']} | {w['runs']} | {w['distance_km']} | {w['avg_pace_min_per_km']} |")
    lines.append("")

    path.write_text("\n".join(lines))
