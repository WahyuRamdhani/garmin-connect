from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "garmin-sync.yml"
REQUIREMENTS = Path(__file__).parents[1] / "requirements.txt"


def test_garmin_token_cache_rotates_between_runs() -> None:
    workflow = WORKFLOW.read_text()

    assert "key: garmin-tokenstore-v2-${{ github.run_id }}" in workflow
    assert "restore-keys: |\n            garmin-tokenstore-v2-" in workflow


def test_garminconnect_version_supports_training_plan_graphql() -> None:
    assert "garminconnect>=0.3.2" in REQUIREMENTS.read_text()
