from garmin_sync.export import write_csv, write_run_summary_md

ROW = {
    "activity_id": 1,
    "name": "Progression Run",
    "date": "2026-08-20",
    "start_time": "2026-08-20 16:07:39",
    "distance_km": 3.846,
    "duration_min": 40.0,
    "avg_pace_min_per_km": 10.4,
    "best_pace_min_per_km": 6.87,
    "avg_hr": 134,
    "max_hr": 167,
}

SPLITS = [
    {
        "split_index": 1,
        "distance_km": 0.451,
        "duration_min": 5.0,
        "pace_min_per_km": 11.09,
        "avg_hr": 123,
        "max_hr": 135,
        "elevation_gain_m": 5.64,
    }
]


def test_write_run_summary_md_includes_key_fields(tmp_path):
    path = tmp_path / "summary.md"
    write_run_summary_md(path, ROW, SPLITS)
    text = path.read_text()
    assert "Progression Run" in text
    assert "2026-08-20" in text
    assert "Avg pace: 10.4 min/km" in text
    assert "Best pace: 6.87 min/km" in text
    assert "| 1 | 0.451 | 5.0 | 11.09 | 123 | 135 | 5.64 |" in text


def test_write_run_summary_md_skips_missing_fields(tmp_path):
    path = tmp_path / "summary.md"
    write_run_summary_md(path, {"name": "Easy Run", "date": "2026-08-20"}, [])
    text = path.read_text()
    assert "Easy Run" in text
    assert "None" not in text


def test_write_csv_single_row(tmp_path):
    path = tmp_path / "activity.csv"
    write_csv(path, [ROW])
    lines = path.read_text().splitlines()
    assert lines[0].startswith("activity_id,name,date")
    assert len(lines) == 2


HR_ZONES = [
    {"zone": 2, "low_bpm": 113, "duration_min": 26.6, "percent": 66.0},
    {"zone": 4, "low_bpm": 150, "duration_min": 7.22, "percent": 18.0},
]


def test_write_run_summary_md_includes_hr_zones(tmp_path):
    path = tmp_path / "summary.md"
    write_run_summary_md(path, ROW, SPLITS, HR_ZONES)
    text = path.read_text()
    assert "Time in Heart Rate Zones" in text
    assert "| 2 | 113 | 26.6 | 66.0% |" in text


TIMESERIES = [
    {"elapsed_s": 0.0, "directHeartRate": 120, "sumDistance": 0.0},
    {"elapsed_s": 1.0, "directHeartRate": 122, "sumDistance": 2.7},
]


def test_write_run_summary_md_includes_timeseries(tmp_path):
    path = tmp_path / "summary.md"
    write_run_summary_md(path, ROW, SPLITS, HR_ZONES, TIMESERIES)
    text = path.read_text()
    assert "Timeseries (Charts tab data)" in text
    assert "2 samples" in text
    assert "| elapsed_s | directHeartRate | sumDistance |" in text
    assert "| 0.0 | 120 | 0.0 |" in text


def test_write_run_summary_md_is_single_self_contained_file(tmp_path):
    """The whole point: one file with everything, for easy upload."""
    path = tmp_path / "summary.md"
    write_run_summary_md(path, ROW, SPLITS, HR_ZONES, TIMESERIES)
    text = path.read_text()
    for heading in ("## Summary", "## Splits", "## Time in Heart Rate Zones", "## Timeseries"):
        assert heading in text


COACH_SCHEDULE = [
    {
        "date": "2026-08-26",
        "plan_name": "10K Plan with Coach Greg",
        "workout_name": "Stride Repeats",
        "workout_type": "ANAEROBIC_SPEED",
        "estimated_duration_min": 41.0,
        "estimated_distance_km": 4.0,
        "completed": True,
    },
    {
        "date": "2026-08-29",
        "plan_name": "10K Plan with Coach Greg",
        "workout_name": "Easy Run",
        "workout_type": None,
        "estimated_duration_min": 40.0,
        "estimated_distance_km": None,
        "completed": False,
    },
]


def test_write_run_summary_md_includes_coach_schedule(tmp_path):
    path = tmp_path / "summary.md"
    write_run_summary_md(
        path,
        ROW,
        SPLITS,
        coach_schedule=COACH_SCHEDULE,
        schedule_reference_date="2026-08-26",
    )
    text = path.read_text()
    assert "## Garmin Coach schedule" in text
    assert "Week containing: 2026-08-26" in text
    assert "10K Plan with Coach Greg" in text
    assert "| 2026-08-26 | Stride Repeats | ANAEROBIC_SPEED | 41.0 | 4.0 | Completed |" in text
    assert "| 2026-08-29 | Easy Run |  | 40.0 |  | Scheduled |" in text


def test_write_run_summary_md_includes_coach_workout_steps(tmp_path):
    path = tmp_path / "summary.md"
    detail = {
        "workout_id": 99,
        "name": "Progression Run",
        "segments": [
            {"order": 1, "steps": [{"type": "warmup", "end_condition": "time", "end_condition_value": 300}]}
        ],
    }
    write_run_summary_md(path, ROW, SPLITS, coach_workout_details=[detail])
    text = path.read_text()
    assert "## Garmin Coach workout details" in text
    assert "Progression Run (99)" in text
    assert "warmup; time=300" in text
