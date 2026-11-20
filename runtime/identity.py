"""Who this extension is: the one place its id, version and repository are written.

The id and the repository address are written here; changing them here (and in
the README and the support page, which name the repository for people) is the whole
change. build_contracts.py writes extension.yaml from these values.
"""

from __future__ import annotations

EXTENSION_ID = "flowsteward.jotform"
DISPLAY_NAME = "Jotform"
VERSION = "0.1.0"
VENDOR_NAME = "Flow Steward"
REPOSITORY_URL = "https://github.com/Flow-Steward/ext-productivity-jotform"
SUPPORT_URL = REPOSITORY_URL + "/issues"
#: Sent as User-Agent with every request.
USER_AGENT = "FlowSteward-Jotform/" + VERSION

__all__ = [
    "DISPLAY_NAME",
    "EXTENSION_ID",
    "REPOSITORY_URL",
    "SUPPORT_URL",
    "USER_AGENT",
    "VENDOR_NAME",
    "VERSION",
]
