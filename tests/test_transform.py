from garmin_sync.transform import (
    activity_to_row,
    extract_detail_fields,
    merge_detail,
    splits_to_rows,
)

ACTIVITY = {
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
}

LAPS = [
    {"distance": 1000.0, "duration": 300.0, "averageHR": 148, "maxHR": 160, "elevationGain": 4.0},
    {"distance": 1000.0, "duration": 295.0, "averageHR": 152, "maxHR": 165, "elevationGain": 5.0},
]


def test_activity_to_row_computes_pace_and_distance():
    row = activity_to_row(ACTIVITY)
    assert row["date"] == "2026-01-06"
    assert row["distance_km"] == 5.0
    assert row["avg_pace_min_per_km"] == 5.0  # 25 min / 5 km


def test_splits_to_rows():
    rows = splits_to_rows(1, LAPS)
    assert len(rows) == 2
    assert rows[0]["split_index"] == 1
    assert rows[0]["pace_min_per_km"] == 5.0


DETAIL = {
    "summaryDTO": {
        "maxSpeed": 2.427,  # m/s -> ~6:52 min/km
        "moderateIntensityMinutes": 32,
        "vigorousIntensityMinutes": 7,
    },
    "avgStrideLength": 0.63,
    "waterEstimated": 239,
}


def test_extract_detail_fields_reads_nested_and_top_level_keys():
    fields = extract_detail_fields(DETAIL)
    assert fields["avg_stride_length_m"] == 0.63
    assert fields["sweat_loss_ml"] == 239
    assert fields["moderate_intensity_min"] == 32
    assert fields["vigorous_intensity_min"] == 7
    assert fields["total_intensity_min"] == 46  # 32 + 2*7, matches Garmin's WHO-style weighting
    assert fields["best_pace_min_per_km"] == round(1000 / (2.427 * 60), 2)


def test_extract_detail_fields_empty_detail_returns_empty():
    assert extract_detail_fields({}) == {}


def test_merge_detail_adds_fields_without_dropping_existing():
    row = {"activity_id": 1, "distance_km": 5.0}
    merged = merge_detail(row, DETAIL)
    assert merged["activity_id"] == 1
    assert merged["distance_km"] == 5.0
    assert merged["avg_stride_length_m"] == 0.63
