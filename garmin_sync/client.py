"""Authentication and data fetching against Garmin Connect."""
from __future__ import annotations

import os
from datetime import date
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


def fetch_running_activities(
    garmin: Garmin, start_date: date, end_date: date
) -> list[dict[str, Any]]:
    """Fetch all running activities in [start_date, end_date]."""
    return garmin.get_activities_by_date(
        start_date.isoformat(), end_date.isoformat(), activitytype="running"
    )


def fetch_splits(garmin: Garmin, activity_id: int) -> list[dict[str, Any]]:
    """Fetch per-lap splits for a single activity. Returns [] on failure."""
    try:
        data = garmin.get_activity_splits(str(activity_id))
    except (GarminConnectConnectionError, GarminConnectTooManyRequestsError):
        return []
    return data.get("lapDTOs", []) if isinstance(data, dict) else []
