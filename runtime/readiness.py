"""Self-service: what works with this API key and account, and a report for support.

Check readiness reads and changes nothing: the account (``GET /user``), its monthly
usage (``GET /user/usage``) and one form of the form list (``GET /user/forms``). For
every everyday step it says ``works``, ``needs_setup`` or ``not_available``, why, and
what to set up. The documentation describes no way to read whether a key has read or
full access, so the steps that change data say that a key with read access cannot.

Build support report saves that check, the extension version, the region and the failed
step's error as a JSON workflow file. It holds no records, no API key and no account
name; e-mail addresses and long numbers in the error text are masked.
"""

from __future__ import annotations

import re
from typing import Any

from . import budget, composites, errors, files
from .context import Context
from .errors import ExtensionError
from .identity import EXTENSION_ID, SUPPORT_URL, VERSION
from .transport import DeadlineReached, dumps_json

WORKS = "works"
NEEDS_SETUP = "needs_setup"
NOT_AVAILABLE = "not_available"
KEY_ACTION = (
    "Check the API key in My Account → API and the connection's region (standard, EU or "
    "HIPAA), then put the key in the connection"
)
#: Everyday step -> (title, whether it changes data).
STEPS: dict[str, tuple[str, bool]] = {
    "test_connection": ("Test connection", False),
    "list_forms": ("List forms", False),
    "describe_form_questions": ("Describe form questions", False),
    "get_form_submissions_since": ("Get form submissions since", False),
    "get_submission_answers": ("Get submission answers", False),
    "create_submission": ("Create submission", True),
    "download_submission_file": ("Download submission file", False),
    "list_form_webhooks": ("List form webhooks", False),
    "add_webhook_if_new": ("Add webhook if new", True),
    "remove_webhook": ("Remove webhook", True),
}
#: Which probe a step depends on.
PROBES = {
    "list_forms": "forms",
    "describe_form_questions": "forms",
    "get_form_submissions_since": "forms",
    "get_submission_answers": "forms",
    "create_submission": "forms",
    "download_submission_file": "forms",
    "list_form_webhooks": "forms",
    "add_webhook_if_new": "forms",
    "remove_webhook": "forms",
}
WRITE_NOTE = (
    "The account answers. The key's access (read or full) cannot be read through the API: "
    "a key with read access cannot change data"
)


def _status(operation_id: str, status: str, reason: str, action: str = "") -> dict[str, Any]:
    return {
        "operation_id": operation_id,
        "title": STEPS[operation_id][0],
        "status": status,
        "reason": reason,
        "action": action,
    }


def _probe(
    context: Context, path: str, query: list[tuple[str, str]], documented_as: str
) -> dict[str, Any]:
    try:
        composites.get(context, path, query, documented_as=documented_as)
    except ExtensionError as exc:
        return {"ok": False, "error_code": exc.code, "error": exc.message}
    return {"ok": True}


def readiness(context: Context) -> dict[str, Any]:
    """The check itself; an account that cannot be read is an error, not a result."""
    acc = composites.account(context)
    probes = {
        "usage": _probe(context, "/user/usage", [], "get_monthly_usage"),
        "forms": _probe(context, "/user/forms", [("limit", "1")], "get_forms"),
    }
    steps = []
    for operation_id, (_, writes) in STEPS.items():
        probe = probes.get(PROBES.get(operation_id, ""), {"ok": True})
        if not probe["ok"]:
            code = probe["error_code"]
            status = (
                NOT_AVAILABLE
                if code in {errors.NOT_FOUND, errors.UNSUPPORTED_OPERATION}
                else NEEDS_SETUP
            )
            steps.append(
                _status(
                    operation_id,
                    status,
                    errors.safe_text(probe["error"], 300),
                    KEY_ACTION if code == errors.SETUP_REQUIRED else "",
                )
            )
        elif writes:
            steps.append(_status(operation_id, WORKS, WRITE_NOTE))
        else:
            steps.append(_status(operation_id, WORKS, "The account answers"))
    ready = all(s["status"] == WORKS for s in steps)
    summary = {
        "region": context.connection.region,
        "account_type": errors.safe_text(acc.get("account_type"), 300) or None,
        "status": errors.safe_text(acc.get("status"), 40) or None,
        "limit_left": acc.get("_limit_left"),
        "probes": probes,
    }
    return {"ready": ready, "steps": steps, "account": summary, "warnings": []}


def check_readiness(context: Context) -> dict[str, Any]:
    composites._closed(context.operation_input, set())
    result = readiness(context)
    budget.ensure_fits(result)
    return result


_EMAIL = re.compile(r"[^\s@]+@[^\s@]+")
_LONG_NUMBER = re.compile(r"\d[\d\s()+-]{6,}\d")


def clean_text(context: Context, value: str, limit: int = 2000) -> str:
    """An error text without the API key, e-mails or long numbers (ids included)."""
    cleaned = context.transport.scrub(value)
    cleaned = _EMAIL.sub("[email]", cleaned)
    cleaned = _LONG_NUMBER.sub("[number]", cleaned)
    return errors.safe_text(cleaned, limit)


def build_support_report(context: Context) -> dict[str, Any]:
    given = composites._closed(
        context.operation_input, {"failed_operation_id", "failed_error_code", "failed_error"}
    )
    report: dict[str, Any] = {
        "report": f"{EXTENSION_ID} support report",
        "extension": {"id": EXTENSION_ID, "version": VERSION},
        "connection": {
            "type": context.connection.connection_type,
            "region": context.connection.region,
            "sign_in": "API key in the APIKEY header",
        },
    }
    try:
        check = readiness(context)
        report["readiness"] = {
            "ready": check["ready"],
            "steps": check["steps"],
            "account": check["account"],
        }
    except (ExtensionError, DeadlineReached) as exc:
        code = exc.code if isinstance(exc, ExtensionError) else errors.TIMEOUT
        message = exc.message if isinstance(exc, ExtensionError) else "out of time"
        report["readiness"] = {"error_code": code, "error": clean_text(context, message)}
    for step in report["readiness"].get("steps", []):
        step["reason"] = clean_text(context, step["reason"], 300)
    for probe in report["readiness"].get("account", {}).get("probes", {}).values():
        if "error" in probe:
            probe["error"] = clean_text(context, probe["error"], 300)
    failed = {
        "operation_id": errors.safe_text(given.get("failed_operation_id") or "", 100),
        "error_code": errors.safe_text(given.get("failed_error_code") or "", 100),
        "error": clean_text(context, str(given.get("failed_error") or ""), 4000),
    }
    if any(failed.values()):
        report["failed_step"] = failed
    data = (dumps_json(report) + "\n").encode("utf-8")
    handle = files.save(
        context,
        data,
        content_type="application/json",
        what="The support report",
        binding_key=files.REPORT_BINDING,
    )
    part = report["readiness"]
    if "steps" in part:
        counts: dict[str, int] = {}
        for step in part["steps"]:
            counts[step["status"]] = counts.get(step["status"], 0) + 1
        state = f"ready: {'yes' if part['ready'] else 'no'}; steps " + ", ".join(
            f"{k} {v}" for k, v in sorted(counts.items())
        )
    else:
        state = f"readiness check failed: {part['error_code']}"
    lines = [f"{EXTENSION_ID} {VERSION}; region {context.connection.region}", state]
    if "failed_step" in report:
        lines.append(
            f"failed step: {failed['operation_id'] or '-'} {failed['error_code']}".rstrip()
        )
    lines.append(f"Attach the report file to a request at {SUPPORT_URL}")
    return {
        "file": handle,
        "summary": "\n".join(lines),
        "support_url": SUPPORT_URL,
        "warnings": [
            "The report holds the readiness check and the failed step's error, no records: "
            "review it before you send it"
        ],
    }


HANDLERS = {"check_readiness": check_readiness, "build_support_report": build_support_report}

__all__ = [
    "HANDLERS",
    "STEPS",
    "build_support_report",
    "check_readiness",
    "clean_text",
    "readiness",
]
