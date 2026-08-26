from garmin_sync.client import fetch_training_plan_schedule


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
