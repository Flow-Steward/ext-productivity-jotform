"""Runners of the generated steps: one documented Jotform API operation each.

What each step accepts and how it is sent comes from runtime/registry.json, built from
the pinned operation list of the documentation (request-models.js) by
tests/reference/build_contracts.py, following the way the documentation's own client
sends each parameter kind:

- ``url`` parameters are required, checked and percent-encoded as one path segment in
  place of their ``{token}``;
- ``query`` parameters are typed: numbers as whole numbers inside the documented
  maximum, a ``jsonString`` (``filter``) as an object sent as JSON text, an ``Enum`` as
  one of its documented values;
- ``post`` parameters are form fields. A documented field with a plain name is its own
  input; fields documented as ``prefix[...]`` (``submission[1]``, ``properties[title]``,
  ``questions[1][type]``) are one object input ``prefix`` whose keys become
  ``prefix[key]`` (nested objects ``prefix[key][sub]``);
- a ``JSON`` parameter is the raw JSON body.

Every documented answer is ``{"responseCode": 200, "message": "success", "content":
...}``; ``data`` is ``content``, ``limit_left`` the daily API calls the key has left.
A read whose body does not carry ``responseCode`` 200 is refused or invalid; a write's
outcome is decided by ``outcome.write_outcome`` (table T).
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

from . import budget, errors, outcome
from .context import Context
from .depth import MAX_ANSWER_DEPTH
from .errors import invalid
from .params import check, wire
from .transport import FORM, JSON_BODY, Answer, Call, TooDeep, dumps_json

REGISTRY_FILE = Path(__file__).resolve().parent / "registry.json"
#: The most items one form-field object or JSON list carries.
MAX_FIELDS = 500
_FIELD_KEY_RE = re.compile(r"^[A-Za-z0-9_]{1,64}$")


@cache
def _data() -> dict[str, Any]:
    return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))


def registry() -> dict[str, dict[str, Any]]:
    return dict(_data()["operations"])


def spec(operation_id: str) -> dict[str, Any]:
    return _data()["operations"][operation_id]


def inputs_of(entry: Mapping[str, Any]) -> set[str]:
    names = {p["input"] for p in entry["path_params"] + entry["query"] + entry["form"]}
    names |= {g["input"] for g in entry["groups"]}
    if entry["json_body"]:
        names.add(entry["json_body"]["input"])
    return names


@dataclass
class Plan:
    """A checked request."""

    method: str
    path: str
    shown: str
    query: list[tuple[str, str]] = field(default_factory=list)
    body: bytes | None = None
    content_type: str = FORM
    sent: int = 0
    warnings: list[str] = field(default_factory=list)


def form_pairs(prefix: str, value: Any, what: str, depth: int = 0) -> list[tuple[str, str]]:
    """An object as form fields: ``{"1": "a", "2": {"first": "b"}}`` under ``submission``
    as ``submission[1]=a&submission[2][first]=b``."""
    if depth > 4:
        raise invalid(f"{what} is nested too deep")
    if not isinstance(value, Mapping) or not value:
        raise invalid(f"{what} must be an object with at least one field")
    pairs: list[tuple[str, str]] = []
    for key, item in value.items():
        if not isinstance(key, str) or not _FIELD_KEY_RE.fullmatch(key):
            raise invalid(f"{what} has a key that is not a field name (letters, digits, _)")
        name = f"{prefix}[{key}]"
        if isinstance(item, Mapping):
            pairs += form_pairs(name, item, f"{what}.{key}", depth + 1)
        else:
            pairs.append((name, form_value(item, f"{what}.{key}")))
        if len(pairs) > MAX_FIELDS:
            raise invalid(f"{what} holds more than {MAX_FIELDS} fields")
    return pairs


def form_value(value: Any, what: str) -> str:
    """One form field's text: text, a number written exactly, true or false."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, str, Decimal)):
        shown = wire(value)
        if len(shown) > 100_000 or any(ord(ch) < 32 and ch not in "\t\r\n" for ch in shown):
            raise invalid(f"{what} is not usable text")
        return shown
    raise invalid(f"{what} must be text, a number or true/false")


def check_json_body(body: Mapping[str, Any], value: Any) -> int:
    """A JSON body checked against its documented top level; the records it carries."""
    shape = body["type"]
    if shape == "array":
        if not isinstance(value, list) or not value:
            raise invalid(f"{body['input']} must be a JSON list")
        if len(value) > MAX_FIELDS:
            raise invalid(f"{body['input']} holds more than {MAX_FIELDS} items")
        return len(value)
    if not isinstance(value, Mapping) or not value:
        raise invalid(f"{body['input']} must be a JSON object")
    return 0


def prepare(operation_id: str, operation_input: Mapping[str, Any]) -> Plan:
    """The checked request of a generated step (also its test-run check)."""
    entry = spec(operation_id)
    given = {k: v for k, v in operation_input.items() if k != "connection_ref"}
    unknown = sorted(set(given) - inputs_of(entry))
    if unknown:
        raise invalid(f"The step input has unknown fields: {', '.join(unknown[:10])}")
    path = entry["path"]
    for prm in entry["path_params"]:
        value = given.get(prm["input"])
        if value is None or value == "":
            raise invalid(f"{prm['input']} is required")
        segment = check(prm["node"], value, prm["input"])
        path = path.replace("{" + prm["token"] + "}", quote(wire(segment), safe=""))
    plan = Plan(method=entry["method"], path=path, shown=f"{entry['method']} {entry['path']}")
    for prm in entry["query"]:
        value = given.get(prm["input"])
        if value is None or value == "" or value == {}:
            if prm["node"]["required"]:
                raise invalid(f"{prm['input']} is required")
            continue
        checked = check(prm["node"], value, prm["input"])
        shown = dumps_json(checked) if prm["node"]["kind"] == "json_text" else wire(checked)
        plan.query.append((prm["name"], shown))
    pairs: list[tuple[str, str]] = []
    for prm in entry["form"]:
        value = given.get(prm["input"])
        if value is None or value == "" or value == {}:
            if prm["node"]["required"]:
                raise invalid(f"{prm['input']} is required")
            continue
        checked = check(prm["node"], value, prm["input"])
        pairs.append(
            (
                prm["name"],
                dumps_json(checked) if prm["node"]["kind"] == "json_text" else wire(checked),
            )
        )
    for group in entry["groups"]:
        value = given.get(group["input"])
        if value in (None, "", {}):
            if group["required"]:
                raise invalid(f"{group['input']} is required")
            continue
        pairs += form_pairs(group["prefix"], value, group["input"])
    body = entry["json_body"]
    if body:
        value = given.get(body["input"])
        if value in (None, "", {}, []):
            if body["required"]:
                raise invalid(f"{body['input']} is required")
        else:
            plan.sent = check_json_body(body, value)
            plan.body = dumps_json(value).encode("utf-8")
            plan.content_type = JSON_BODY
    if pairs:
        plan.body = urlencode(pairs).encode("ascii")
        plan.content_type = FORM
    elif entry["kind"] == "write" and plan.body is None and entry["method"] in {"POST", "PUT"}:
        plan.body = b""
    return plan


def to_call(entry: Mapping[str, Any], plan: Plan) -> Call:
    return Call(
        method=plan.method,
        path=plan.path,
        shown=plan.shown,
        query=tuple(plan.query),
        body=plan.body,
        content_type=plan.content_type,
        refusals=entry["refusals"],
        success=tuple(entry["success"]),
    )


def read_answer(context: Context, answer: Answer, shown: str) -> dict[str, Any]:
    """A read's answer: ``data`` (``content``), ``result_set``, ``limit_left``.

    The body must be the documented JSON object with ``responseCode`` 200; another
    ``responseCode`` is Jotform's refusal (nothing changed, it is a read)."""
    if answer.empty:
        raise errors.no_effect(
            errors.INVALID_RESPONSE,
            f"Jotform answered {shown} with an empty body",
            failure_class="provider",
            retryable=False,
        )
    try:
        data = context.transport.json(answer)
    except TooDeep:
        raise too_deep(shown) from None
    except ValueError:
        raise errors.no_effect(
            errors.INVALID_RESPONSE,
            f"Jotform answered {shown} with something that is not JSON",
            failure_class="provider",
            retryable=False,
        ) from None
    if not isinstance(data, Mapping):
        raise errors.no_effect(
            errors.INVALID_RESPONSE,
            f"Jotform's answer to {shown} is not the documented JSON object",
            failure_class="provider",
            retryable=False,
        )
    code = data.get("responseCode")
    if code != 200 or isinstance(code, bool):
        message = errors.safe_text(data.get("message"), 600)
        said = f": {message}" if message else ""
        known = isinstance(code, int) and not isinstance(code, bool)
        error_code = (
            errors.NOT_FOUND
            if code == 404
            else errors.SETUP_REQUIRED
            if code == 401
            else errors.AUTHENTICATION_FAILED
            if code == 403
            else errors.RATE_LIMITED
            if code == 429
            else errors.UPSTREAM_VALIDATION_FAILED
            if known
            else errors.INVALID_RESPONSE
        )
        what = f"responseCode {code}" if known else "no responseCode 200"
        raise errors.no_effect(
            error_code,
            f"Jotform refused {shown} ({what}){said}",
            failure_class="provider",
            retryable=False,
        )
    result_set = data.get("resultSet")
    return {
        "data": data.get("content"),
        "result_set": dict(result_set) if isinstance(result_set, Mapping) else None,
        "limit_left": outcome.limit_left(data),
    }


def too_deep(shown: str) -> errors.ExtensionError:
    """A read whose answer nests too deeply to be read: nothing was changed."""
    return errors.no_effect(
        errors.INVALID_RESPONSE,
        f"Jotform's answer to {shown} nests deeper than {MAX_ANSWER_DEPTH} levels and was not read",
        failure_class="provider",
        retryable=False,
    )


def step_class(entry: Mapping[str, Any]) -> str:
    return str(entry.get("step_class") or outcome.CONFIRM)


processing_of = outcome.processing_of
NOTHING_SENT = outcome.NOTHING_SENT


def run(context: Context, operation_id: str) -> dict[str, Any]:
    entry = spec(operation_id)
    plan = prepare(operation_id, context.operation_input)
    call = to_call(entry, plan)
    if entry["kind"] == "read":
        answer = context.transport.read(call)
        read = read_answer(context, answer, plan.shown)
        result: dict[str, Any] = {"status": answer.status, "data": read["data"]}
        if entry["paged"]:
            result["result_set"] = read["result_set"]
        result["limit_left"] = read["limit_left"]
        result["warnings"] = list(plan.warnings)
        budget.ensure_fits(result)
        return result
    answer = context.transport.write(call)
    decided = outcome.write_outcome(
        context, answer, plan.shown, entry=entry, step=step_class(entry), sent=plan.sent
    )
    said: list[str] = decided.pop("warnings")
    decided.pop("id", None)
    return {"status": answer.status, **decided, "warnings": plan.warnings + said}


__all__ = [
    "MAX_FIELDS",
    "NOTHING_SENT",
    "Plan",
    "check_json_body",
    "form_pairs",
    "inputs_of",
    "prepare",
    "processing_of",
    "read_answer",
    "registry",
    "run",
    "spec",
    "step_class",
    "too_deep",
]
