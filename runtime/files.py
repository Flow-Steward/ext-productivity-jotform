"""Workflow files: the JSON lists the reading steps save, uploaded files and the support report."""

from __future__ import annotations

from collections.abc import Mapping

from . import errors
from .context import Context
from .errors import ExtensionError

ARTIFACT_TIMEOUT_SECONDS = 120.0
MAX_DOWNLOAD_BYTES = 40 * 1024 * 1024
MAX_REPORT_BYTES = 2 * 1024 * 1024

#: Must match contracts/artifact_policies.yaml (tests/reference/build_contracts.py).
DOWNLOAD_BINDING = "jotform_file"
REPORT_BINDING = "jotform_report"
#: A file uploaded with a submission, saved as it came (its own type is a step output:
#: the host grants one content type per binding).
UPLOAD_BINDING = "jotform_upload"
BINARY_CONTENT_TYPE = "application/octet-stream"


def save(
    context: Context,
    data: bytes,
    *,
    content_type: str,
    what: str,
    binding_key: str = DOWNLOAD_BINDING,
) -> str:
    """Save ``data`` as a workflow file; its handle."""
    limit = MAX_REPORT_BYTES if binding_key == REPORT_BINDING else MAX_DOWNLOAD_BYTES
    if len(data) > limit:
        raise errors.no_effect(
            errors.RESPONSE_TOO_LARGE, f"{what} is larger than {limit // (1024 * 1024)} MB"
        )
    try:
        written = context.artifact_writer(
            dict(context.payload),
            [data],
            binding_key=binding_key,
            content_type=content_type,
            timeout_seconds=ARTIFACT_TIMEOUT_SECONDS,
        )
    except ExtensionError:
        raise
    except Exception:
        raise errors.no_effect(
            errors.ARTIFACT_OUTPUT_UNAVAILABLE, f"{what} could not be saved"
        ) from None
    handle = written.get("artifact_handle") if isinstance(written, Mapping) else None
    if not isinstance(handle, str) or not handle.strip():
        raise errors.no_effect(errors.ARTIFACT_OUTPUT_UNAVAILABLE, f"{what} could not be saved")
    return handle.strip()


__all__ = [
    "ARTIFACT_TIMEOUT_SECONDS",
    "BINARY_CONTENT_TYPE",
    "DOWNLOAD_BINDING",
    "MAX_DOWNLOAD_BYTES",
    "MAX_REPORT_BYTES",
    "REPORT_BINDING",
    "UPLOAD_BINDING",
    "save",
]
