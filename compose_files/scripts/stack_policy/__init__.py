"""Host-side stack policy: hardlink layout, *arr payloads, Plex prefs.

Stdlib only — systemd ExecStartPost and CI call this with system python3.
"""

from stack_policy.profiles import RADARR_QUALITY_PROFILE, SONARR_QUALITY_PROFILE

__all__ = ["RADARR_QUALITY_PROFILE", "SONARR_QUALITY_PROFILE"]
