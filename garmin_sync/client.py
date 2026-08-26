"""Authentication and data fetching against Garmin Connect."""
from __future__ import annotations

import os
from typing import Any

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)


def _tokenstore() -> str:
    return os.path.expanduser(os.getenv("GARMIN_TOKENSTORE", "~/.garminconnect"))


def _prompt_mfa() -> str:
    return os.environ.get("GARMIN_MFA_CODE") or input("Garmin MFA code: ").strip()


def login() -> Garmin:
    """Log in to Garmin Connect, reusing a cached session token when possible.

    Garmin.login() tries the tokenstore first and only falls back to
    GARMIN_EMAIL/GARMIN_PASSWORD if no valid cached session exists, so your
    password isn't sent on every run. Successful credential logins persist
    fresh tokens back to the tokenstore automatically.
    """
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")
    is_cn = os.getenv("GARMIN_IS_CN", "false").lower() == "true"

    garmin = Garmin(email=email, password=password, is_cn=is_cn, prompt_mfa=_prompt_mfa)
    try:
        garmin.login(_tokenstore())
    except GarminConnectAuthenticationError as e:
        if not email or not password:
            raise RuntimeError(
                "No cached Garmin session found and GARMIN_EMAIL/GARMIN_PASSWORD "
                "are not set. Copy .env.example to .env and fill in your credentials."
            ) from e
        raise
    return garmin


def fetch_latest_running_activity(garmin: Garmin) -> dict[str, Any] | None:
    """Fetch only the single most recent running activity, or None if there are none."""
    activities = garmin.get_activities(0, 1, activitytype="running")
    return activities[0] if activities else None


def fetch_splits(garmin: Garmin, activity_id: int) -> list[dict[str, Any]]:
    """Fetch per-lap splits for a single activity. Returns [] on failure."""
    try:
        data = garmin.get_activity_splits(str(activity_id))
    except (GarminConnectConnectionError, GarminConnectTooManyRequestsError):
        return []
    return data.get("lapDTOs", []) if isinstance(data, dict) else []


def fetch_activity_detail(garmin: Garmin, activity_id: int) -> dict[str, Any]:
    """Fetch the full per-activity detail payload (richer than the list view) -
    this is where best pace, stride length, intensity minutes, etc. live.
    Returns {} on failure.
    """
    try:
        return garmin.get_activity(str(activity_id))
    except (GarminConnectConnectionError, GarminConnectTooManyRequestsError):
        return {}


def fetch_activity_timeseries(garmin: Garmin, activity_id: int) -> dict[str, Any]:
    """Fetch the second-by-second sample data behind the app's Charts tab
    (pace/HR/elevation/cadence over time). Returns {} on failure.
    """
    try:
        return garmin.get_activity_details(str(activity_id))
    except (GarminConnectConnectionError, GarminConnectTooManyRequestsError):
        return {}


def fetch_hr_zones(garmin: Garmin, activity_id: int) -> list[dict[str, Any]]:
    """Fetch the Time-in-Heart-Rate-Zones breakdown for a single activity.
    Returns [] on failure.
    """
    try:
        data = garmin.get_activity_hr_in_timezones(str(activity_id))
    except (GarminConnectConnectionError, GarminConnectTooManyRequestsError):
        return []
    return data if isinstance(data, list) else []


def fetch_training_plan_schedule(garmin: Garmin, calendar_date: str) -> dict[str, Any]:
    """Fetch the Garmin Coach week containing ``calendar_date``."""
    query = {
        "query": (
            f'query{{trainingPlanScalar(calendarDate:"{calendar_date}", '
            'lang:"en-US", firstDayOfWeek:"monday")}'
        )
    }
    try:
        response = garmin.query_garmin_graphql(query)
    except (GarminConnectConnectionError, GarminConnectTooManyRequestsError):
        return {}
    if not isinstance(response, dict):
        return {}
    data = response.get("data") or {}
    plan = data.get("trainingPlanScalar") or {}
    return plan if isinstance(plan, dict) else {}
