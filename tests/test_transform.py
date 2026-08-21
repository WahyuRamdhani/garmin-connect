from garmin_sync.transform import (
    activities_to_rows,
    monthly_trends,
    personal_bests,
    splits_to_rows,
    weekly_trends,
)

ACTIVITIES = [
    {
        "activityId": 1,
        "activityName": "Morning Run",
        "startTimeLocal": "2026-01-06 06:00:00",
        "distance": 5000.0,
        "duration": 1500.0,
        "movingDuration": 1480.0,
        "elevationGain": 20.0,
        "elevationLoss": 18.0,
        "averageHR": 150,
        "maxHR": 172,
        "calories": 320,
        "aerobicTrainingEffect": 3.2,
        "anaerobicTrainingEffect": 1.1,
        "trainingEffectLabel": "TEMPO",
        "vO2MaxValue": 48,
        "averageRunningCadenceInStepsPerMinute": 170,
        "maxRunningCadenceInStepsPerMinute": 185,
    },
    {
        "activityId": 2,
        "activityName": "Long Run",
        "startTimeLocal": "2026-01-20 06:30:00",
        "distance": 15000.0,
        "duration": 5400.0,
        "movingDuration": 5350.0,
        "elevationGain": 80.0,
        "elevationLoss": 75.0,
        "averageHR": 145,
        "maxHR": 165,
        "calories": 950,
        "aerobicTrainingEffect": 3.8,
        "anaerobicTrainingEffect": 0.5,
        "trainingEffectLabel": "AEROBIC_BASE",
        "vO2MaxValue": 48,
        "averageRunningCadenceInStepsPerMinute": 165,
        "maxRunningCadenceInStepsPerMinute": 178,
    },
]

LAPS = [
    {"distance": 1000.0, "duration": 300.0, "averageHR": 148, "maxHR": 160, "elevationGain": 4.0},
    {"distance": 1000.0, "duration": 295.0, "averageHR": 152, "maxHR": 165, "elevationGain": 5.0},
]


def test_activities_to_rows_computes_pace_and_distance():
    rows = activities_to_rows(ACTIVITIES)
    assert rows[0]["date"] == "2026-01-06"
    assert rows[0]["distance_km"] == 5.0
    assert rows[0]["avg_pace_min_per_km"] == 5.0  # 25 min / 5 km


def test_splits_to_rows():
    rows = splits_to_rows(1, LAPS)
    assert len(rows) == 2
    assert rows[0]["split_index"] == 1
    assert rows[0]["pace_min_per_km"] == 5.0


def test_weekly_and_monthly_trends():
    rows = activities_to_rows(ACTIVITIES)
    weekly = weekly_trends(rows)
    monthly = monthly_trends(rows)
    assert len(weekly) == 2
    assert len(monthly) == 1
    assert monthly[0]["distance_km"] == 20.0


def test_personal_bests():
    rows = activities_to_rows(ACTIVITIES)
    bests = personal_bests(rows)
    assert bests["longest_run"]["activity_id"] == 2
    assert bests["fastest_pace"]["activity_id"] == 1
