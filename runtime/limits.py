"""Step limits shared by every runner."""

from __future__ import annotations

#: The entrypoint is given 600 s (extension.yaml). Every request must start early
#: enough to finish inside it.
STEP_TIMEOUT_SECONDS = 600.0

STEP_MARGIN_SECONDS = 30.0
