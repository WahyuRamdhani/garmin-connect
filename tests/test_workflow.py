from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "garmin-sync.yml"


def test_garmin_token_cache_rotates_between_runs() -> None:
    workflow = WORKFLOW.read_text()

    assert "key: garmin-tokenstore-v2-${{ github.run_id }}" in workflow
    assert "restore-keys: |\n            garmin-tokenstore-v2-" in workflow
