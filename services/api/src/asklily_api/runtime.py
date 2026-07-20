"""Runtime-profile boundary shared by API responses and standalone packaging."""

from __future__ import annotations

import os
from collections.abc import Mapping

SUPPORTED_RUNTIME_PROFILES = frozenset({"developer", "standalone"})


def runtime_profile(environment: Mapping[str, str] | None = None) -> str:
    """Return the explicit local profile without exposing any configuration values."""

    values = os.environ if environment is None else environment
    profile = values.get("ASKLILY_RUNTIME_PROFILE", "developer").strip()
    if profile not in SUPPORTED_RUNTIME_PROFILES:
        raise ValueError("asklily_runtime_profile_invalid")
    return profile
