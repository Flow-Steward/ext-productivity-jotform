"""The outcome of a write after it was sent: one decision for every write step.

``write_outcome`` is the only place that decides it, for the generated steps and the
everyday ones alike (table T). Its inputs are the status, the Content-Type, the state of
the body and the step's class; the first rule that applies decides.

Jotform confirms a change inside the body: every documented answer is HTTP 200 with
``{"responseCode": 200, "message": "success", "content": ...}``, and the
documentation's own client (MethodSectionView.js) counts an answer as successful only
when ``responseCode`` is 200. So every write step of this extension is of class (a), the
confirmation inside the body; two kinds of step also need something from ``content``:

- ``CONFIRM`` (a): the confirmation alone;
- ``CONFIRM_BATCH`` (a + b): a list of records sent (``PUT /form/{id}/submissions``),
  ``content`` documented as the list of the records added;
- ``CONFIRM_CREATE`` (a + c): the step returns the new record's id from ``content``
  (Create submission: ``content.submissionID``). Jotform documents no ``Location``.

The rules:

- T1. A status the operation does not document as success (200): decided by the
  transport before this (a refusal in the documented form, or an unknown outcome).
- T2. JSON is documented for HTTP 200 and the Content-Type is present and not JSON:
  ``timeout_unknown``, decided by the headers whatever happened to the body.
- T3. The body was read, is not empty, and does not start with ``{`` or ``[`` or does
  not parse: ``timeout_unknown``.
- T4. The body was not read in full (limit, deadline, broken connection) or nests
  deeper than 48 levels: (a) the confirmation is in the body, so ``timeout_unknown``,
  for every class.
- T5. The body parsed, but not in the form the step needs:
  a) no ``responseCode`` 200 in an object: ``responseCode`` one of the refusal statuses
     the operation documents, with a ``message`` → a refusal, nothing changed (the
     documented refusal form, as for an HTTP refusal); any other form →
     ``timeout_unknown``;
  b) confirmed, but ``content`` is not the documented list → ``ok``, ``succeeded``,
     ``applied: null``, ``unanswered`` = the records sent, a warning;
  c) confirmed, but ``content`` names no new id → ``invalid_response`` +
     ``timeout_unknown``, saying the record was created.
- T6. Otherwise success: ``processing``, ``applied``, ``check``, ``data`` (``content``),
  ``limit_left``.

An empty body is not a parsed body: it carries no confirmation (T4/T5a: unknown).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from . import errors
from .depth import MAX_ANSWER_DEPTH
from .errors import ExtensionError
from .transport import CHECK, Answer, TooDeep, unknown

CONFIRM = "confirm"
CONFIRM_BATCH = "confirm_batch"
CONFIRM_CREATE = "confirm_create"
CLASSES = (CONFIRM, CONFIRM_BATCH, CONFIRM_CREATE)

_JSON_STARTS = (b"{", b"[")


def json_type(content_type: str) -> bool:
    return content_type == "application/json" or (
        content_type.startswith("application/") and content_type.endswith("+json")
    )


def processing_of(entry: Mapping[str, Any] | None, status: int) -> dict[str, Any]:
    """What the answer to a write confirms: the change made (completed), or the request
    accepted, to be carried out by Jotform afterwards (accepted). The documentation
    describes no write as carried out afterwards; ``processing.accepted_always`` stays
    the place to mark one."""
    facts = (entry or {}).get("processing") or {}
    if status == 202 or facts.get("accepted_always"):
        return {
            "processing": "accepted",
            "applied": False,
            "check": {"operation_id": facts.get("check"), "location": None},
        }
    return {"processing": "completed", "applied": True, "check": None}


#: The processing outputs of a write that sent nothing (a test run, or nothing to do).
NOTHING_SENT: dict[str, Any] = {"processing": None, "applied": False, "check": None}


def limit_left(data: Any) -> int | None:
    """The answer's ``limit-left``: the API calls the key has left today."""
    value = data.get("limit-left") if isinstance(data, Mapping) else None
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def write_outcome(
    context: Any,
    answer: Answer,
    shown: str,
    *,
    entry: Mapping[str, Any] | None,
    step: str = CONFIRM,
    sent: int = 0,
    find_id: Callable[[Any], str | None] | None = None,
    what: str = "record",
) -> dict[str, Any]:
    """The outputs of a write Jotform answered with a documented success status:
    ``data`` (the answer's ``content``), ``limit_left``, ``warnings``, ``processing``,
    ``applied``, ``check``; for a batch also ``unanswered``, for a creation ``id``.
    Raises for a refusal stated in the body and for an unknown outcome."""
    if step not in CLASSES:  # pragma: no cover - a programming error
        raise ValueError(step)
    status = answer.status
    kind = answer.content_type
    # T2: by the headers, whatever happened to the body.
    if kind and not json_type(kind):
        raise _unknown(shown, status, f"its Content-Type is {errors.safe_text(kind, 60)}")
    # T4: the confirmation is inside a body that was not read.
    if answer.unread is not None:
        raise _unknown(shown, status, f"its answer was not read ({answer.unread})")
    if answer.empty:
        raise _unknown(shown, status, "its answer is empty")
    start = answer.raw.lstrip(b"\xef\xbb\xbf \t\r\n")[:1]
    if start not in _JSON_STARTS:  # T3
        raise _unknown(shown, status, "its body does not start with { or [")
    try:
        data = context.transport.json(answer)
    except TooDeep:  # T4
        raise _unknown(
            shown, status, f"its answer nests deeper than {MAX_ANSWER_DEPTH} levels"
        ) from None
    except ValueError:  # T3
        raise _unknown(shown, status, "its body does not parse") from None
    # T5a: the confirmation.
    code = data.get("responseCode") if isinstance(data, Mapping) else None
    if code != 200 or isinstance(code, bool):
        refusals = set((entry or {}).get("refusals") or ())
        message = data.get("message") if isinstance(data, Mapping) else None
        if (
            isinstance(code, int)
            and not isinstance(code, bool)
            and str(code) in refusals
            and isinstance(message, str)
        ):
            detail = errors.safe_text(context.transport.scrub(message), 600)
            raise errors.no_effect(
                errors.NOT_FOUND if code == 404 else errors.UPSTREAM_VALIDATION_FAILED,
                f"Jotform refused {shown} (responseCode {code}): {detail}; nothing was changed",
                failure_class="provider",
                retryable=False,
                http_status=status,
            )
        raise _unknown(shown, status, "its answer does not carry responseCode 200")
    context.transport.committed = True
    content = data.get("content")
    out: dict[str, Any] = {"data": content, "limit_left": limit_left(data), "warnings": []}
    out.update(processing_of(entry, status))
    if step == CONFIRM_BATCH:
        out["unanswered"] = 0
        if not isinstance(content, list):  # T5b
            out["data"] = None
            out["applied"] = None
            out["unanswered"] = sent
            out["warnings"].append(
                f"Jotform confirmed {shown} (responseCode 200) but its content is not the "
                f"documented list of the records added; which of the {sent} records were "
                "saved is not known: check them in Jotform"
            )
        return out
    if step == CONFIRM_CREATE:  # T5c
        found = find_id(content) if find_id is not None else None
        if found is None:
            raise ExtensionError(
                errors.INVALID_RESPONSE,
                f"The {what} was created: Jotform confirmed {shown} (responseCode 200) but its "
                f"answer does not name the new {what}, so its id is not known; find the "
                f"{what} in Jotform before running the step again",
                failure_class="provider",
                retryable=False,
                definitely_no_external_effect=False,
                external_effect_status="timeout_unknown",
                http_status=status,
            )
        out["id"] = found
    return out  # T6


def _unknown(shown: str, status: int, why: str) -> ExtensionError:
    return unknown(
        f"Jotform answered {shown} with HTTP {status} but not with the confirmation the "
        f"documentation shows (a JSON answer with responseCode 200): {why}" + CHECK,
        errors.INVALID_RESPONSE,
        status,
    )


__all__ = [
    "CLASSES",
    "CONFIRM",
    "CONFIRM_BATCH",
    "CONFIRM_CREATE",
    "NOTHING_SENT",
    "json_type",
    "limit_left",
    "processing_of",
    "write_outcome",
]
