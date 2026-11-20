"""A fake Jotform API, an in-memory artifact plane and helpers."""

from __future__ import annotations

import io
import json
from collections.abc import Callable
from email.message import Message
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlsplit

from runtime.operations import handle_runtime
from runtime.transport import JotformTransport, parse_json

BUNDLE = Path(__file__).resolve().parents[1]
API_KEY = "0123456789abcdef0123456789abcdef"  # pragma: allowlist secret
JSON = "application/json"


class Call:
    def __init__(self, request: Any) -> None:
        parts = urlsplit(request.full_url)
        self.url = request.full_url
        self.host = parts.hostname
        self.path = parts.path
        self.query = parse_qsl(parts.query, keep_blank_values=True)
        self.verb = request.get_method()
        self.headers = {k.lower(): v for k, v in request.header_items()}
        self.raw_body = request.data or b""
        self.form = (
            parse_qsl(self.raw_body.decode(), keep_blank_values=True)
            if self.headers.get("content-type") == "application/x-www-form-urlencoded"
            else []
        )
        try:
            self.body: Any = (
                parse_json(self.raw_body)
                if self.raw_body and self.headers.get("content-type") == JSON
                else None
            )
        except ValueError:
            self.body = None

    @property
    def key(self) -> str:
        return f"{self.verb} {self.path}"

    def q(self, name: str) -> str | None:
        return dict(self.query).get(name)


class Response:
    def __init__(self, status: int, body: bytes, headers: dict[str, str] | None = None) -> None:
        self.status = status
        self._body = body
        self.headers = Message()
        for name, value in (headers or {"Content-Type": JSON}).items():
            self.headers[name] = value

    def read(self, size: int = -1) -> bytes:
        chunk, self._body = (
            (self._body, b"") if size < 0 else (self._body[:size], self._body[size:])
        )
        return chunk

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def envelope(content: Any = None, *, limit_left: int = 900, **extra: Any) -> dict[str, Any]:
    """The documented answer: responseCode 200, message success, content."""
    return {
        "responseCode": 200,
        "message": "success",
        "content": content,
        **extra,
        "limit-left": limit_left,
    }


def ok(content: Any = None, status: int = 200, **extra: Any) -> Response:
    return Response(status, json.dumps(envelope(content, **extra), default=str).encode("utf-8"))


def raw(status: int, body: bytes, content_type: str = JSON, **headers: str) -> Response:
    return Response(
        status, body, {"Content-Type": content_type, **headers} if content_type else headers
    )


def refuse(status: int, body: Any = None, **headers: str) -> HTTPError:
    if body is None:
        body = {"responseCode": status, "message": "refused for a reason"}
    data = body if isinstance(body, bytes) else json.dumps(body).encode()
    message = Message()
    message["Content-Type"] = JSON
    for name, value in headers.items():
        message[name.replace("_", "-")] = value
    return HTTPError("https://api.jotform.com/x", status, "refused", message, io.BytesIO(data))


def page(items: list[Any], offset: int = 0, limit: int = 1000) -> Response:
    return ok(items, resultSet={"offset": offset, "limit": limit, "count": len(items)})


class FakeJotform:
    """Answers requests in order (a list) or by key (``"GET /user"`` -> answer)."""

    def __init__(self, *answers: Any, routes: dict[str, Any] | None = None) -> None:
        self.answers = list(answers)
        self.routes = routes or {}
        self.calls: list[Call] = []

    def __call__(self, request: Any, *, timeout_seconds: float, purpose: str) -> Any:
        call = Call(request)
        self.calls.append(call)
        if call.key in self.routes:
            answer = self.routes[call.key]
            if isinstance(answer, list):
                answer = answer.pop(0)
        elif self.answers:
            answer = self.answers.pop(0)
        else:
            raise AssertionError(f"unexpected request {call.key}")
        if callable(answer) and not isinstance(answer, (Response, HTTPError)):
            answer = answer(call)
        if isinstance(answer, BaseException):
            raise answer
        return answer


class Artifacts:
    def __init__(self) -> None:
        self.saved: list[dict[str, Any]] = []

    def writer(self, payload: Any, chunks: list[bytes], **kwargs: Any) -> dict[str, Any]:
        data = b"".join(chunks)
        handle = f"artifact-{len(self.saved) + 1}"
        self.saved.append({"handle": handle, "data": data, **kwargs})
        return {"artifact_handle": handle}


def payload(
    operation_id: str,
    operation_input: dict[str, Any] | None = None,
    *,
    region: str = "standard",
    api_key: str = API_KEY,
    test_mode: bool = False,
    connection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target_connection = connection or {
        "connection_id": "conn-1",
        "connection_type": "jotform",
        "config": {"label": "Example", "region": region},
        "secrets": {"api_key": api_key},
    }
    return {
        "mode": "action",
        "contract_version": "extension_host_v2",
        "runtime_context": {
            "test_mode": test_mode,
            "group_id": None,
            "for_each_id": None,
            "step_id": "step-1",
            "step_execution_id": "exec-1",
        },
        "action": {
            "action_id": operation_id,
            "input": {"connection_ref": "conn-1", **(operation_input or {})},
            "target": {"connection": target_connection},
        },
    }


class Clock:
    """A clock that moves only when the transport sleeps or a test moves it."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def run(
    operation_id: str,
    operation_input: dict[str, Any] | None = None,
    fake: FakeJotform | None = None,
    *,
    artifacts: Artifacts | None = None,
    clock: Clock | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    fake = fake if fake is not None else FakeJotform()
    artifacts = artifacts or Artifacts()
    clock = clock or Clock()

    def factory(connection: Any) -> JotformTransport:
        return JotformTransport(connection, opener=fake, clock=clock, sleep=clock.sleep)

    return handle_runtime(
        payload(operation_id, operation_input, **kwargs),
        transport_factory=factory,
        artifact_writer=artifacts.writer,
    )


def text_of(response: dict[str, Any]) -> str:
    return json.dumps(response, default=str)


Handler = Callable[[Call], Any]
