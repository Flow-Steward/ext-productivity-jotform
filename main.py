#!/usr/bin/env python3
"""Jotform subprocess entrypoint."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from dispatcher import dispatch_runtime
from runtime import depth, numbers

MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_SERIALIZED_RESPONSE_BYTES = 9 * 512 * 1024
_CONTROL_TRANSLATION = {
    codepoint: " " for codepoint in (*range(32), *range(127, 160)) if codepoint not in {9, 10, 13}
}


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        response = _refused("The request exceeds its safe limit")
    else:
        try:
            payload = _load_payload(raw)
        except UnboundedNumber as exc:
            response = _refused(str(exc))
        except (TooDeep, RecursionError):
            response = _refused(TOO_DEEP)
        except (UnicodeDecodeError, json.JSONDecodeError):
            response = _refused("The request is not valid JSON")
        else:
            response = dispatch_runtime(payload)
    final_response, serialized = _bounded_serialized_response(response)
    sys.stdout.buffer.write(serialized)
    sys.stdout.buffer.write(b"\n")
    return 0 if final_response.get("ok") is True else 2


class UnboundedNumber(ValueError):
    """A number of the request is outside what this extension writes out in full."""


class TooDeep(ValueError):
    """The request nests deeper than ``depth.MAX_REQUEST_DEPTH`` levels."""


TOO_DEEP = (
    f"The request nests deeper than {depth.MAX_REQUEST_DEPTH} levels of lists and objects; "
    "nothing was sent"
)


def _float(text: str) -> Decimal:
    number = numbers.read(text, integer=False)
    if not isinstance(number, Decimal):
        raise UnboundedNumber(
            f"The request has a number with more than {numbers.MAX_DIGITS} digits or an "
            f"exponent outside {numbers.MIN_EXPONENT}..{numbers.MAX_EXPONENT}; nothing was sent"
        )
    return number


def _int(text: str) -> int:
    number = numbers.read(text, integer=True)
    if not isinstance(number, int):
        raise UnboundedNumber(
            f"The request has a whole number with more than {numbers.MAX_DIGITS} digits; "
            "nothing was sent"
        )
    return number


def _constant(text: str) -> Any:
    raise UnboundedNumber(f"The request has {text[:20]}, which is not a JSON number")


def _load_payload(raw: bytes) -> dict[str, Any]:
    """The request, with every number that has a point read as ``Decimal``.

    1234567890.12345678 reaches the checks as written, not rounded through float.
    Nothing in the host's envelope is used as a float, so the whole request is
    read the same way. A number outside ``runtime.numbers``' bounds (digits and
    exponent, from ``Decimal.as_tuple()``), NaN and Infinity refuse the request before
    it is used, so ``1e1000000`` is never written out in full.
    """
    text = raw.decode("utf-8")
    if not text.strip():
        return {}
    # Counted before parsing: a deep text never reaches the recursive JSON reader.
    if depth.too_deep(raw, depth.MAX_REQUEST_DEPTH):
        raise TooDeep(TOO_DEEP)
    payload = json.loads(text, parse_float=_float, parse_int=_int, parse_constant=_constant)
    return payload if isinstance(payload, dict) else {}


def _refused(message: str) -> dict[str, Any]:
    """A request refused before anything was read or sent."""
    response = _error_response("invalid_payload", message)
    response["definitely_no_external_effect"] = True
    response["external_effect_status"] = "failed"
    return response


def _bounded_serialized_response(response: Mapping[str, Any]) -> tuple[dict[str, Any], bytes]:
    sanitized, changed = _sanitize_json_value(dict(response))
    if not isinstance(sanitized, dict):
        raise TypeError("extension response must be an object")
    if changed:
        sanitized["output_sanitized"] = True
    serialized = _json_bytes(sanitized)
    if len(serialized) + 1 <= MAX_SERIALIZED_RESPONSE_BYTES:
        return sanitized, serialized
    return _too_large(sanitized)


#: What the last-resort answer keeps of a response that is too large.
MAX_KEPT_TEXT = 200
MAX_KEPT_FIELDS = 50


def _too_large(response: Mapping[str, Any]) -> tuple[dict[str, Any], bytes]:
    """The last-resort answer: it keeps the write's facts and the result's short values.

    A write the account confirmed (``succeeded``) is still a success: the answer is
    ``ok`` with the result cut to its short values (ids, status, processing) and a
    warning, never ``ok: false`` with ``succeeded``, which the host would turn into an
    unknown outcome. Anything else becomes ``response_too_large``.
    """
    result = response.get("result")
    kept = _short_values(result) if isinstance(result, Mapping) else {}
    status = response.get("external_effect_status")
    if response.get("ok") is True and status == "succeeded":
        kept["warnings"] = [
            (
                "The result is too large for the step output and is cut to its identifiers; "
                "the change was saved, see it in the account"
            )
        ]
        confirmed: dict[str, Any] = {
            "ok": True,
            "result": kept,
            "error_code": None,
            "error": None,
            "errors": [],
            "external_effect_status": "succeeded",
            "definitely_no_external_effect": False,
        }
        return confirmed, _json_bytes(confirmed)
    message = "The extension response exceeds its safe output limit"
    if status == "timeout_unknown":
        message += "; a change may have been saved, check it before running the step again"
    error_response = _error_response("response_too_large", message)
    for key in ("external_effect_status", "definitely_no_external_effect"):
        if key in response:
            error_response[key] = response[key]
    if kept:
        error_response["result"] = {**kept, "warnings": []}
    return error_response, _json_bytes(error_response)


def _short_values(result: Mapping[str, Any]) -> dict[str, Any]:
    kept = {
        key: value
        for key, value in list(result.items())[: MAX_KEPT_FIELDS * 4]
        if isinstance(key, str)
        and key != "warnings"
        and len(key) <= MAX_KEPT_TEXT
        and isinstance(value, (str, int, float, bool, type(None)))
        and len(str(value)) <= MAX_KEPT_TEXT
    }
    return dict(list(kept.items())[:MAX_KEPT_FIELDS])


def _sanitize_json_value(value: Any) -> tuple[Any, bool]:
    if isinstance(value, str):
        sanitized = value.translate(_CONTROL_TRANSLATION)
        return sanitized, sanitized != value
    if isinstance(value, Mapping):
        mapped: dict[Any, Any] = {}
        changed = False
        for key, item in value.items():
            sanitized, item_changed = _sanitize_json_value(item)
            mapped[key] = sanitized
            changed = changed or item_changed
        return mapped, changed
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        items: list[Any] = []
        changed = False
        for item in value:
            sanitized, item_changed = _sanitize_json_value(item)
            items.append(sanitized)
            changed = changed or item_changed
        return items, changed
    return value, False


def _json_bytes(response: Mapping[str, Any]) -> bytes:
    return json.dumps(
        response,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _error_response(code: str, message: str) -> dict[str, Any]:
    return {
        "ok": False,
        # Every step declares warnings; a failure carries the list too, empty.
        "result": {"warnings": []},
        "warnings": [],
        "error_code": code,
        "error": message,
        "errors": [{"code": code, "message": message}],
    }


if __name__ == "__main__":
    raise SystemExit(main())
