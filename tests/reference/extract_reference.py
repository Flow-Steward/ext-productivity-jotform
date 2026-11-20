#!/usr/bin/env python3
"""Extract the facts of the Jotform API documentation from its pinned sources.

The documentation page https://api.jotform.com/docs/ builds its list of operations
with scripts. The list itself is the script ``request-models.js`` the page loads
(``<script src="https://cdn.jotfor.ms/s/static/ae9b124410a/js/apidocs/v1/request-models.js">``),
a plain request without signing in: one JavaScript object per operation
(``id``, ``type`` = HTTP method, ``url``, ``definition``, ``explanation``,
``parameters``, ``statusCodes``) and the array ``requestModels`` that names the
operations the page shows. It is pinned in ``pinned/jotform_request_models.js``.

The page's own client, ``MethodSectionView.js`` (pinned in
``pinned/jotform_method_section_view.js``), shows how the documentation sends each
parameter kind: ``query`` in the query string, ``post`` as form fields, ``url``
replacing its ``{token}`` in the path, ``JSON`` as the raw request body; and that it
counts an answer as a success only when the body's ``responseCode`` is 200.

The file is read as data, never run: a small tokenizer reads the object literals.
A value that is an expression (the page fills the API key field from a cookie) is
recorded as ``null``. Run from the bundle root, with the isolated interpreter:

    python3 -I tests/reference/extract_reference.py

It writes ``jotform_api.json``. tests/test_reference.py fails when the pinned file
changes or the facts drift from it.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "pinned" / "jotform_request_models.js"
CLIENT = HERE / "pinned" / "jotform_method_section_view.js"
OUTPUT = HERE / "jotform_api.json"
URL = "https://cdn.jotfor.ms/s/static/ae9b124410a/js/apidocs/v1/request-models.js"
CLIENT_URL = "https://cdn.jotfor.ms/s/static/ae9b124410a/js/apidocs/v1/MethodSectionView.js"
PAGE_URL = "https://api.jotform.com/docs/"
SHA256 = "ded079d796ecde08f097af8845a409d6afdd8af3f4ad6023f3827af01c51b0a3"
BYTES = 80910
CLIENT_SHA256 = "e9463bd0c0d172dc96a618fd9b736c2fa630d043f7033253c1b9bb840cd2ecf8"
DOWNLOADED = "2026-11-20"

_TOKEN = re.compile(
    r"""
    (?P<space>\s+)
    |(?P<line_comment>//[^\n]*)
    |(?P<block_comment>/\*.*?\*/)
    |(?P<string>"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')
    |(?P<number>-?\d+(?:\.\d+)?)
    |(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)
    |(?P<op>!==|===|[{}\[\]():,;=?.!])
    """,
    re.VERBOSE | re.DOTALL,
)
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "/": "/"}


def tokens(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    pos = 0
    while pos < len(text):
        match = _TOKEN.match(text, pos)
        if match is None:
            raise SystemExit(f"the specification changed: unreadable text at {pos}")
        kind = match.lastgroup or ""
        if kind not in {"space", "line_comment", "block_comment"}:
            out.append((kind, match.group()))
        pos = match.end()
    return out


def unquote(literal: str) -> str:
    body = literal[1:-1]
    out: list[str] = []
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 1 < len(body):
            nxt = body[i + 1]
            out.append(_ESCAPES.get(nxt, nxt))
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


class Reader:
    """Reads the ``var name = value;`` statements of the file as data."""

    def __init__(self, items: list[tuple[str, str]]) -> None:
        self.items = items
        self.pos = 0
        self.names: dict[str, Any] = {}
        #: Variables a top-level array refers to, by position (requestModels).
        self.references: dict[str, list[str]] = {}

    def peek(self) -> tuple[str, str]:
        return self.items[self.pos] if self.pos < len(self.items) else ("end", "")

    def take(self, value: str | None = None) -> tuple[str, str]:
        item = self.peek()
        if value is not None and item[1] != value:
            raise SystemExit(f"the specification changed: expected {value!r}, found {item[1]!r}")
        self.pos += 1
        return item

    def statements(self) -> None:
        while self.peek()[0] != "end":
            self.take("var")
            name = self.take()[1]
            self.take("=")
            self.names[name] = self.value(top=name)
            if self.peek()[1] == ";":
                self.take(";")

    def value(self, top: str | None = None) -> Any:
        kind, text = self.peek()
        if text == "{":
            return self.mapping()
        if text == "[":
            return self.sequence(top)
        if kind == "string":
            self.take()
            value = unquote(text)
            # "a" + "b": the page writes no concatenation; refuse it to notice a change.
            if self.peek()[1] == "+":
                raise SystemExit("the specification changed: a concatenated text")
            return value
        if kind == "number":
            self.take()
            return int(text) if re.fullmatch(r"-?\d+", text) else text
        if kind == "name" and text in {"true", "false", "null"}:
            self.take()
            return {"true": True, "false": False, "null": None}[text]
        if kind == "name" and self._ends_here(1):
            self.take()
            if text not in self.names:
                raise SystemExit(f"the specification changed: unknown name {text}")
            return {"$ref": text}
        # An expression (the API key field's cookie value): skipped, recorded as null.
        self._skip_expression()
        return None

    def _ends_here(self, offset: int) -> bool:
        nxt = self.items[self.pos + offset][1] if self.pos + offset < len(self.items) else ""
        return nxt in {",", "}", "]", ";"}

    def _skip_expression(self) -> None:
        depth = 0
        while True:
            kind, text = self.peek()
            if kind == "end":
                raise SystemExit("the specification changed: an unterminated expression")
            if text in "([{":
                depth += 1
            elif text in ")]}":
                if depth == 0:
                    return
                depth -= 1
            elif text == "," and depth == 0:
                return
            self.take()

    def mapping(self) -> dict[str, Any]:
        self.take("{")
        out: dict[str, Any] = {}
        while self.peek()[1] != "}":
            kind, text = self.take()
            key = unquote(text) if kind == "string" else text
            self.take(":")
            if key in out:
                raise SystemExit(f"the specification changed: key {key} twice")
            out[key] = self.value()
            if self.peek()[1] == ",":
                self.take(",")
        self.take("}")
        return out

    def sequence(self, top: str | None) -> list[Any]:
        self.take("[")
        out: list[Any] = []
        while self.peek()[1] != "]":
            out.append(self.value())
            if self.peek()[1] == ",":
                self.take(",")
        self.take("]")
        if top is not None:
            self.references[top] = [i["$ref"] for i in out if isinstance(i, dict) and "$ref" in i]
        return out


def _resolve(value: Any, names: dict[str, Any]) -> Any:
    if isinstance(value, dict) and set(value) == {"$ref"}:
        return names[value["$ref"]]
    if isinstance(value, dict):
        return {k: _resolve(v, names) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve(v, names) for v in value]
    return value


#: The fields an operation object and a parameter object may have.
OPERATION_KEYS = {"id", "type", "url", "definition", "explanation", "parameters", "statusCodes"}
PARAMETER_KEYS = {
    "name",
    "description",
    "type",
    "inputType",
    "parameterType",
    "required",
    "value",
    "replace",
    "values",
    "example",
    "Example",
}
PARAMETER_TYPES = {"query", "url", "post", "JSON", ""}
METHODS = {"GET", "POST", "PUT", "DELETE"}


def commented_models(text: str) -> list[str]:
    """Names the requestModels array lists only in comments (``// ,userApps``)."""
    start = text.find("var requestModels")
    return re.findall(r"//\s*,\s*([A-Za-z]+)", text[start:]) if start >= 0 else []


def extract(raw: bytes) -> dict[str, Any]:
    if hashlib.sha256(raw).hexdigest() != SHA256:
        raise SystemExit("the specification changed: request-models.js is not the pinned file")
    text = raw.decode("utf-8")
    reader = Reader(tokens(text))
    reader.statements()
    names = reader.names
    if "requestModels" not in reader.references:
        raise SystemExit("the specification changed: no requestModels array")
    listed = reader.references["requestModels"]
    if len(listed) != len(set(listed)):
        raise SystemExit("the specification changed: an operation is listed twice")
    operations: list[dict[str, Any]] = []
    for model in listed:
        obj = _resolve(names[model], names)
        if set(obj) - OPERATION_KEYS or not {"id", "type", "url"} <= set(obj):
            raise SystemExit(f"the specification changed: {model} has {sorted(obj)}")
        if obj["type"] not in METHODS:
            raise SystemExit(f"the specification changed: {model} method {obj['type']}")
        params = []
        for prm in obj.get("parameters") or []:
            if set(prm) - PARAMETER_KEYS:
                raise SystemExit(f"the specification changed: {model} parameter {sorted(prm)}")
            if prm.get("parameterType", "") not in PARAMETER_TYPES:
                raise SystemExit(f"the specification changed: {model} {prm.get('parameterType')}")
            params.append(
                {
                    "name": prm.get("name", ""),
                    "description": prm.get("description") or "",
                    "type": prm.get("type", ""),
                    "input_type": prm.get("inputType", ""),
                    "parameter_type": prm.get("parameterType", ""),
                    "required": prm.get("required") is True,
                    "replace": prm.get("replace"),
                    "values": prm.get("values"),
                    "example": prm.get("example", prm.get("Example")),
                }
            )
        operations.append(
            {
                "model": model,
                "doc_id": obj["id"],
                "method": obj["type"],
                "path": obj["url"],
                "definition": obj.get("definition") or "",
                "explanation": obj.get("explanation") or "",
                "parameters": params,
                "status_codes": [
                    {"code": int(s["code"]), "reason": s.get("reason") or ""}
                    for s in obj.get("statusCodes") or []
                ],
            }
        )
    defined = [n for n, v in names.items() if isinstance(v, dict) and "url" in v]
    return {
        "source": {
            "page": PAGE_URL,
            "url": URL,
            "sha256": SHA256,
            "bytes": len(raw),
            "downloaded": DOWNLOADED,
            "client": {"url": CLIENT_URL, "sha256": CLIENT_SHA256},
        },
        "operations": operations,
        # Objects the file defines but the page does not list, and names it lists only in
        # comments: neither is an operation the documentation shows.
        "defined_not_listed": sorted(set(defined) - set(listed)),
        "commented_out": commented_models(text),
    }


def main() -> int:
    facts = extract(SOURCE.read_bytes())
    if hashlib.sha256(CLIENT.read_bytes()).hexdigest() != CLIENT_SHA256:
        raise SystemExit("the specification changed: MethodSectionView.js is not the pinned file")
    OUTPUT.write_text(json.dumps(facts, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("operations", len(facts["operations"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
