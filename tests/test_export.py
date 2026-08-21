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
