import json

from sync_garmin import sync_training_plan


class FakeGarmin:
    def query_garmin_graphql(self, query):
        return {
            "data": {
                "trainingPlanScalar": {
                    "trainingPlanWorkoutScheduleDTOS": [
                        {
                            "trainingPlanId": 1784472036,
                            "planName": "10K Plan with Coach Greg",
                            "workoutScheduleSummaries": [
                                {
                                    "workoutUuid": "easy-uuid",
                                    "workoutName": "Easy Run",
                                    "workoutType": "running",
                                    "scheduleDate": "2026-08-29",
                                    "estimatedDurationInSecs": 2400,
                                }
                            ],
                        }
                    ]
                }
            }
        }

    def get_workout_by_id(self, workout_id):
        return {"workoutId": int(workout_id), "workoutName": "Progression Run", "workoutSegments": []}

    def get_training_plan_by_id(self, plan_id):
        return {
            "trainingPlanId": int(plan_id),
            "workoutName": "Progression Run",
            "workoutSegments": [{"segmentOrder": 1, "workoutSteps": []}],
        }


def test_sync_training_plan_writes_raw_json_and_csv(tmp_path):
    rows = sync_training_plan(FakeGarmin(), tmp_path, "2026-08-26")

    assert rows[0]["plan_name"] == "10K Plan with Coach Greg"
    assert rows[0]["workout_name"] == "Easy Run"
    assert (tmp_path / "coach_schedule.csv").exists()
    raw = json.loads((tmp_path / "coach_schedule_raw.json").read_text())
    assert raw["trainingPlanWorkoutScheduleDTOS"][0]["planName"] == (
        "10K Plan with Coach Greg"
    )


def test_sync_training_plan_details_writes_future_workout_definitions(tmp_path):
    from sync_garmin import sync_training_plan_details

    rows = [{
        "date": "2026-08-30",
        "workout_name": "Progression Run",
        "workout_id": 1672866335,
        "completed": False,
    }]
    details = sync_training_plan_details(FakeGarmin(), tmp_path, rows, "2026-08-29")

    assert details[0]["workout_id"] == 1672866335
    raw = json.loads((tmp_path / "coach_workout_details.json").read_text())
    assert raw[0]["workoutId"] == 1672866335
