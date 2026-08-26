import json

from sync_garmin import sync_training_plan


class FakeGarmin:
    def query_garmin_graphql(self, query):
        return {
            "data": {
                "trainingPlanScalar": {
                    "trainingPlanWorkoutScheduleDTOS": [
                        {
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


def test_sync_training_plan_writes_raw_json_and_csv(tmp_path):
    rows = sync_training_plan(FakeGarmin(), tmp_path, "2026-08-26")

    assert rows[0]["plan_name"] == "10K Plan with Coach Greg"
    assert rows[0]["workout_name"] == "Easy Run"
    assert (tmp_path / "coach_schedule.csv").exists()
    raw = json.loads((tmp_path / "coach_schedule_raw.json").read_text())
    assert raw["trainingPlanWorkoutScheduleDTOS"][0]["planName"] == (
        "10K Plan with Coach Greg"
    )
