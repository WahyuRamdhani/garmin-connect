from garmin_sync.transform import (
    activity_to_row,
    extract_detail_fields,
    hr_zones_to_rows,
    merge_detail,
    splits_to_rows,
    training_plan_to_rows,
    workout_detail_to_summary,
    timeseries_to_rows,
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
    "avgStrideLength": 63,  # centimeters, per Garmin's API
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


TIMESERIES_DETAIL = {
    "metricDescriptors": [
        {"metricsIndex": 0, "key": "directTimestamp"},
        {"metricsIndex": 2, "key": "directHeartRate"},
        {"metricsIndex": 1, "key": "sumDistance"},
    ],
    "activityDetailMetrics": [
        {"metrics": [1700000000000, 0.0, 120]},
        {"metrics": [1700000001000, 2.5, 122]},
    ],
}


def test_timeseries_to_rows_orders_columns_by_metrics_index():
    rows = timeseries_to_rows(TIMESERIES_DETAIL)
    assert len(rows) == 2
    # descriptor order is 0,1,2 regardless of the order they appear in the list
    assert rows[0] == {
        "directTimestamp": 1700000000000,
        "sumDistance": 0.0,
        "directHeartRate": 120,
        "elapsed_s": 0.0,
    }
    assert rows[1]["elapsed_s"] == 1.0


def test_timeseries_to_rows_empty_detail_returns_empty():
    assert timeseries_to_rows({}) == []


HR_ZONES_RAW = [
    {"zoneNumber": 1, "secsInZone": 0.0, "zoneLowBoundary": 94},
    {"zoneNumber": 2, "secsInZone": 1596.0, "zoneLowBoundary": 113},
    {"zoneNumber": 3, "secsInZone": 371.0, "zoneLowBoundary": 132},
    {"zoneNumber": 4, "secsInZone": 433.0, "zoneLowBoundary": 150},
    {"zoneNumber": 5, "secsInZone": 0.0, "zoneLowBoundary": 168},
]


def test_hr_zones_to_rows_computes_minutes_and_percent():
    rows = hr_zones_to_rows(HR_ZONES_RAW)
    assert rows[1]["zone"] == 2
    assert rows[1]["duration_min"] == 26.6
    assert rows[1]["percent"] == 66.5  # 1596s / 2400s total


def test_hr_zones_to_rows_empty_returns_empty():
    assert hr_zones_to_rows([]) == []


TRAINING_PLAN_RAW = {
    "trainingPlanWorkoutScheduleDTOS": [
        {
            "planName": "10K Plan with Coach Greg",
            "workoutScheduleSummaries": [
                {
                    "workoutUuid": "stride-uuid",
                    "workoutName": "Stride Repeats",
                    "workoutType": "running",
                    "workoutPhrase": "ANAEROBIC_SPEED",
                    "scheduleDate": "2026-08-26",
                    "estimatedDurationInSecs": 2460,
                    "estimatedDistanceInMeters": 4000,
                    "associatedActivityId": 24117228760,
                },
                {
                    "workoutUuid": "easy-uuid",
                    "workoutName": "Easy Run",
                    "workoutType": "running",
                    "scheduleDate": "2026-08-29",
                    "estimatedDurationInSecs": 2400,
                    "associatedActivityId": None,
                },
            ],
        }
    ]
}


def test_training_plan_to_rows_flattens_and_sorts_schedule():
    rows = training_plan_to_rows(TRAINING_PLAN_RAW)
    assert rows == [
        {
            "date": "2026-08-26",
            "plan_name": "10K Plan with Coach Greg",
            "workout_name": "Stride Repeats",
            "sport": "running",
            "workout_type": "ANAEROBIC_SPEED",
            "estimated_duration_min": 41.0,
            "estimated_distance_km": 4.0,
            "completed": True,
            "activity_id": 24117228760,
            "workout_id": None,
            "workout_uuid": "stride-uuid",
            "is_rest_day": False,
            "is_race_day": False,
        },
        {
            "date": "2026-08-29",
            "plan_name": "10K Plan with Coach Greg",
            "workout_name": "Easy Run",
            "sport": "running",
            "workout_type": None,
            "estimated_duration_min": 40.0,
            "estimated_distance_km": None,
            "completed": False,
            "activity_id": None,
            "workout_id": None,
            "workout_uuid": "easy-uuid",
            "is_rest_day": False,
            "is_race_day": False,
        },
    ]


def test_training_plan_to_rows_handles_empty_payload():
    assert training_plan_to_rows({}) == []


def test_workout_detail_to_summary_extracts_steps_and_targets():
    detail = {
        "workoutId": 99,
        "workoutName": "Progression Run",
        "sportType": {"sportTypeKey": "running"},
        "estimatedDurationInSecs": 2400,
        "workoutSegments": [
            {
                "segmentOrder": 1,
                "sportType": {"sportTypeKey": "running"},
                "workoutSteps": [
                    {
                        "stepOrder": 1,
                        "stepType": {"stepTypeKey": "warmup"},
                        "endCondition": {"conditionTypeKey": "time"},
                        "endConditionValue": 300,
                        "targetType": {"workoutTargetTypeKey": "heart.rate.zone"},
                        "zoneNumber": 3,
                    }
                ],
            }
        ],
    }
    assert workout_detail_to_summary(detail) == {
        "workout_id": 99,
        "name": "Progression Run",
        "sport": "running",
        "estimated_duration_min": 40.0,
        "segments": [
            {
                "order": 1,
                "sport": "running",
                "steps": [
                    {
                        "order": 1,
                        "type": "warmup",
                        "end_condition": "time",
                        "end_condition_value": 300,
                        "target_type": "heart.rate.zone",
                        "target_zone": 3,
                    }
                ],
            }
        ],
    }
