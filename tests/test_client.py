from garmin_sync.client import fetch_scheduled_workout_detail, fetch_training_plan_schedule


class FakeGarmin:
    def __init__(self):
        self.query = None

    def query_garmin_graphql(self, query):
        self.query = query
        return {
            "data": {
                "trainingPlanScalar": {
                    "trainingPlanWorkoutScheduleDTOS": [
                        {"planName": "10K Plan with Coach Greg"}
                    ]
                }
            }
        }

    def get_workout_by_id(self, workout_id):
        return {"workoutId": int(workout_id), "workoutName": "Progression Run"}


def test_fetch_training_plan_schedule_queries_week_for_reference_date():
    garmin = FakeGarmin()
    result = fetch_training_plan_schedule(garmin, "2026-08-26")

    assert result["trainingPlanWorkoutScheduleDTOS"][0]["planName"] == (
        "10K Plan with Coach Greg"
    )
    assert garmin.query == {
        "query": (
            'query{trainingPlanScalar(calendarDate:"2026-08-26", '
            'lang:"en-US", firstDayOfWeek:"monday")}'
        )
    }


def test_fetch_scheduled_workout_detail_uses_workout_id():
    detail = fetch_scheduled_workout_detail(FakeGarmin(), 1672866335)
    assert detail == {"workoutId": 1672866335, "workoutName": "Progression Run"}
