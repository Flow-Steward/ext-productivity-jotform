"""The only way this extension reaches Jotform.

Every operation is a REST call to the connection's API address (``https://api.jotform.com``,
``https://eu-api.jotform.com`` or ``https://hipaa-api.jotform.com``, the documentation's
"API Endpoints"), with ``Accept: application/json``. The API key travels only in the
``APIKEY`` header (the documentation's "Authenticate with HTTP Headers"). A body is sent
the way the documentation's own client sends it (MethodSectionView.js): ``post``
parameters as form fields (``application/x-www-form-urlencoded``), a ``JSON`` parameter
as the raw JSON text (``application/json``, as the label examples write it). Requests go
out through the public Flow Steward extension SDK, which pins DNS, verifies the
connected peer, refuses redirects and enforces the timeout. They are sent one at a time.

Rate: the documentation limits the API calls of a key per day by plan (1,000 for the
starter plan up to 100,000 for gold) and reports what is left as ``limit-left`` in
every answer; it states no per-second limit. Requests still start at least
``MIN_INTERVAL_SECONDS`` apart. A read refused with HTTP 429 waits as ``Retry-After``
asks (or ``DEFAULT_RETRY_WAIT_SECONDS``) and is tried again at most ``MAX_READ_RETRIES``
times while time is left; a write is never sent twice.

Success: the documentation's answers are HTTP 200 with a JSON body whose ``responseCode``
is 200 and ``message`` "success"; its own client counts an answer as successful only
when ``responseCode`` is 200. An answer with another 2xx status is not taken as success:
for a read it is an invalid answer, for a write the change may or may not have been made
(``timeout_unknown``).

Refusals: the statuses each operation documents (``statusCodes``: 404 for most, 400 for
some) prove that nothing changed only when the body has the answer form
(``responseCode`` equal to the status and a ``message``). Every other failure after a
change was sent leaves the write ``timeout_unknown``, and nothing is retried.
"""

from __future__ import annotations

import http.client
import json
import re
import secrets
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request

from flowsteward_extension_sdk import PinnedPeerError, open_pinned_url, parse_retry_after

from . import depth, errors, numbers
from .connection import Connection
from .errors import ExtensionError
from .identity import USER_AGENT

DEFAULT_TIMEOUT_SECONDS = 120.0
MAX_REQUEST_BODY_BYTES = 10 * 1024 * 1024
#: The most read from one answer.
MAX_ANSWER_BYTES = 30 * 1024 * 1024
MAX_ERROR_BODY_BYTES = 64 * 1024
CHUNK_BYTES = 64 * 1024
#: Shortest window still worth starting a request in.
MIN_CALL_WINDOW_SECONDS = 15.0
#: No per-second limit is documented; requests are still spaced a little.
MIN_INTERVAL_SECONDS = 0.1
DEFAULT_RETRY_WAIT_SECONDS = 1.0
MAX_RETRY_WAIT_SECONDS = 30.0
MAX_READ_RETRIES = 3
#: How long a write whose status confirmed it waits for its late body to give up.
BODY_GRACE_SECONDS = 5.0
ACCEPT = "application/json"
_PATH_RE = re.compile(r"^(/[A-Za-z0-9%._~-]+)+$")
FORM = "application/x-www-form-urlencoded"
JSON_BODY = "application/json"
CHECK = "; check in Jotform what changed before running the step again"
#: Response headers a step may return.
KEPT_HEADERS = ("Location", "Retry-After")


class DeadlineReached(Exception):
    """The invocation's time budget leaves no room for another request."""


@dataclass
class Answer:
    status: int
    raw: bytes
    content_type: str
    headers: dict[str, str] = field(default_factory=dict)
    #: Why the body of a confirmed write was not read (too large, too late); None when
    #: it was read. The status already confirmed the change.
    unread: str | None = None

    @property
    def empty(self) -> bool:
        return not self.raw.strip()


@dataclass(frozen=True)
class Call:
    """One request."""

    method: str
    path: str
    shown: str
    query: Sequence[tuple[str, str]] = ()
    body: bytes | None = None
    #: FORM or JSON_BODY: how ``body`` is written.
    content_type: str = FORM
    #: Documented refusal statuses: {status: its body must have the answer form}.
    refusals: Mapping[str, bool] = field(default_factory=dict)
    #: Documented 2xx statuses.
    success: Sequence[str] = ("200",)
    limit: int = MAX_ANSWER_BYTES


class JotformTransport:
    """Sends requests to one Jotform account."""

    def __init__(
        self,
        connection: Connection,
        *,
        opener: Callable[..., Any] = open_pinned_url,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._connection = connection
        self._opener = opener
        self.clock = clock
        self._sleep = sleep
        self._timeout_seconds = timeout_seconds
        self._call_timeout = timeout_seconds
        self._last_start: float | None = None
        #: True once a request that can change data may have left this process.
        self.mutated = False
        #: True once the account confirmed a change in this invocation.
        self.committed = False
        #: Monotonic time after which no request may start (set by the operation).
        self.deadline: float | None = None
        #: How many reads waited after HTTP 429 in this invocation.
        self.rate_waits = 0

    @property
    def connection(self) -> Connection:
        return self._connection

    def remaining(self) -> float:
        return float("inf") if self.deadline is None else self.deadline - self.clock()

    # -- public calls --------------------------------------------------------

    def read(self, call: Call) -> Answer:
        """A read; after HTTP 429 it waits as asked and tries again, a few times."""
        attempt = 0
        while True:
            try:
                return self._call(call, mutating=False)
            except ExtensionError as exc:
                if exc.code != errors.RATE_LIMITED or attempt >= MAX_READ_RETRIES:
                    raise
                wait = min(
                    MAX_RETRY_WAIT_SECONDS,
                    exc.retry_after_seconds or DEFAULT_RETRY_WAIT_SECONDS,
                )
                if self.remaining() - wait < MIN_CALL_WINDOW_SECONDS:
                    raise
                attempt += 1
                self.rate_waits += 1
                self._sleep(wait)

    def write(self, call: Call) -> Answer:
        """A change, sent once; its answer with a documented success status. Jotform
        confirms the change inside the body (``responseCode`` 200): ``outcome.write_outcome``
        reads it and sets ``committed``."""
        return self._call(call, mutating=True)

    def fetch_file(self, url: str, limit: int) -> Answer:
        """A file uploaded with a submission, from the address Jotform gave for it.

        The form uploads documentation (``GET /form/{id}/files``) gives files at
        ``https://www.jotform.com/uploads/{username}/{form-id}/{submission-id}/{file-name}``.
        Only an https address of a jotform.com host under ``/uploads/`` is fetched; the
        documentation does not say that this address takes the API key, so the key is
        not sent there. A read: nothing changes."""
        request = Request(url, method="GET", headers={"Accept": "*/*", "User-Agent": USER_AGENT})
        remaining = self.remaining()
        if remaining < MIN_CALL_WINDOW_SECONDS:
            raise DeadlineReached
        self._pace()
        self._call_timeout = min(self._timeout_seconds, remaining)
        expires = None if self.deadline is None else self.deadline + MIN_CALL_WINDOW_SECONDS
        call = Call(method="GET", path="/uploads", shown="the uploaded file", limit=limit)
        try:
            with self._opener(
                request, timeout_seconds=self._call_timeout, purpose="Jotform upload"
            ) as response:
                status = int(getattr(response, "status", 0) or getattr(response, "code", 0) or 0)
                headers = getattr(response, "headers", None) or {}
                raw = read_bounded(
                    response,
                    limit,
                    expires=expires,
                    clock=self.clock,
                    per_read=self._call_timeout,
                )
        except HTTPError as exc:
            raise self.refusal(int(exc.code), b"", call, mutating=False) from None
        except PinnedPeerError:
            raise errors.no_effect(
                errors.BLOCKED_ADDRESS,
                f"{request.host} is not reachable under the host network policy",
            ) from None
        except TimeoutError:
            raise errors.no_effect(errors.TIMEOUT, "The file did not arrive in time") from None
        except (OSError, http.client.HTTPException):
            raise errors.no_effect(
                errors.CONNECTION_FAILED, "The connection failed while the file was read"
            ) from None
        if status != 200:
            raise errors.no_effect(
                errors.INVALID_RESPONSE, f"The file address answered HTTP {status}"
            )
        kind = str(headers.get("Content-Type") or "") if hasattr(headers, "get") else ""
        return Answer(status, raw, kind.split(";")[0].strip().lower(), {}, None)

    # -- answers -------------------------------------------------------------

    def scrub(self, value: Any) -> Any:
        """The API key removed from every text and key of a parsed answer."""
        if isinstance(value, str):
            for form in self._connection.secret_forms():
                if form in value:
                    value = value.replace(form, "[redacted]")
            return value
        if isinstance(value, Mapping):
            return {self.scrub(k): self.scrub(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.scrub(v) for v in value]
        return value

    def json(self, answer: Answer) -> Any:
        """The answer's JSON value (numbers with a point as Decimal), key removed.
        ValueError when it is not JSON."""
        return self.scrub(parse_json(answer.raw))

    def text(self, answer: Answer, limit: int = 100_000) -> str:
        return self.scrub(answer.raw.decode("utf-8", "replace"))[:limit]

    # -- one request ---------------------------------------------------------

    def _pace(self) -> None:
        """Keep request starts at least ``MIN_INTERVAL_SECONDS`` apart."""
        if self._last_start is not None:
            gap = MIN_INTERVAL_SECONDS - (self.clock() - self._last_start)
            if gap > 0:
                self._sleep(gap)
        self._last_start = self.clock()

    def _call(self, call: Call, *, mutating: bool) -> Answer:
        if not _PATH_RE.fullmatch(call.path) or any(
            segment in {".", ".."} for segment in call.path.split("/")
        ):
            raise errors.invalid("Not a Jotform API path")
        headers = {
            "Accept": ACCEPT,
            "User-Agent": USER_AGENT,
            "APIKEY": self._connection.api_key,
        }
        if call.body is not None:
            if len(call.body) > MAX_REQUEST_BODY_BYTES:
                raise errors.invalid("The request is larger than the 10 MB this extension sends")
            headers["Content-Type"] = call.content_type
        url = self._connection.base_url + call.path
        if call.query:
            url += "?" + urlencode(list(call.query))
        request = Request(url, method=call.method, data=call.body, headers=headers)
        remaining = self.remaining()
        if remaining < MIN_CALL_WINDOW_SECONDS:
            raise DeadlineReached
        self._pace()
        self._call_timeout = min(self._timeout_seconds, remaining)
        if mutating:
            self.mutated = True
        expires = None if self.deadline is None else self.deadline + MIN_CALL_WINDOW_SECONDS
        if expires is None:
            return self._exchange(request, call, mutating)
        outcome: dict[str, Any] = {}
        progress: dict[str, Any] = {}

        def work() -> None:
            try:
                outcome["value"] = self._exchange(request, call, mutating, progress)
            except BaseException as exc:  # handed to the caller below
                outcome["error"] = exc

        worker = threading.Thread(target=work, name="jotform-call", daemon=True)
        worker.start()
        worker.join(max(0.0, expires - self.clock()))
        if worker.is_alive() and "head" in progress:
            # The account already confirmed the write with its status; only the body is
            # late. A moment for the reader to give up on its own, then the status counts.
            worker.join(BODY_GRACE_SECONDS)
            if worker.is_alive():
                status, headers = progress["head"]
                return self._answer(status, headers, b"", "it did not arrive in time")
        if worker.is_alive():
            _late(mutating)
        if "error" in outcome:
            raise outcome["error"]
        return outcome["value"]

    def _exchange(
        self,
        request: Request,
        call: Call,
        mutating: bool,
        progress: dict[str, Any] | None = None,
    ) -> Answer:
        expires = None if self.deadline is None else self.deadline + MIN_CALL_WINDOW_SECONDS
        unread: str | None = None
        try:
            with self._opener(
                request, timeout_seconds=self._call_timeout, purpose="Jotform"
            ) as response:
                status = int(getattr(response, "status", 0) or getattr(response, "code", 0) or 0)
                headers = getattr(response, "headers", None) or {}
                # The status is known before the body. Jotform confirms a write inside the
                # body, so a late or unread body leaves the outcome unknown (outcome.py, T4a);
                # the status only lets the step wait a moment for the body.
                confirmed = (
                    mutating
                    and 200 <= status < 300
                    and (not call.success or str(status) in call.success)
                )
                if confirmed and progress is not None:
                    progress["head"] = (status, headers)
                try:
                    raw = read_bounded(
                        response,
                        call.limit,
                        mutating=mutating,
                        expires=expires,
                        clock=self.clock,
                        per_read=self._call_timeout,
                    )
                except ExtensionError as exc:
                    if not confirmed:
                        raise
                    raw = b""
                    unread = (
                        f"it is larger than the {call.limit // (1024 * 1024)} MB this extension "
                        "reads"
                        if exc.code == errors.RESPONSE_TOO_LARGE
                        else "it did not arrive in time"
                    )
                except (OSError, http.client.HTTPException):
                    if not confirmed:
                        raise
                    raw = b""
                    unread = "the connection failed while it was read"
        except HTTPError as exc:
            try:
                body = exc.read(MAX_ERROR_BODY_BYTES)
            except Exception:  # pragma: no cover - upstream body is optional
                body = b""
            raise self.refusal(
                int(exc.code),
                body or b"",
                call,
                mutating=mutating,
                headers=self.scrub(_kept(exc.headers)),
            ) from None
        except PinnedPeerError as exc:
            # Raised while resolving and pinning, before anything was sent.
            host = request.host
            if "cannot be resolved" in str(exc):
                raise errors.no_effect(
                    errors.CONNECTION_FAILED, f"{host} could not be resolved"
                ) from None
            raise errors.no_effect(
                errors.BLOCKED_ADDRESS,
                f"{host} is not reachable under the host network policy",
            ) from None
        except TimeoutError:
            raise ExtensionError(
                errors.TIMEOUT_UNKNOWN if mutating else errors.TIMEOUT,
                "Jotform did not answer in time" + (CHECK if mutating else ""),
                **_transport_failure_facts(mutating=mutating),
            ) from None
        except (OSError, http.client.HTTPException):
            raise ExtensionError(
                errors.TIMEOUT_UNKNOWN if mutating else errors.CONNECTION_FAILED,
                "The connection to Jotform failed" + (CHECK if mutating else ""),
                **_transport_failure_facts(mutating=mutating),
            ) from None
        if status < 200 or status >= 300:
            raise self.refusal(
                status,
                raw[:MAX_ERROR_BODY_BYTES],
                call,
                mutating=mutating,
                headers=self.scrub(_kept(headers)),
            )
        if call.success and str(status) not in call.success:
            raise undocumented(status, call, mutating=mutating)
        return self._answer(status, headers, raw, unread)

    def _answer(self, status: int, headers: Any, raw: bytes, unread: str | None) -> Answer:
        kind = str(headers.get("Content-Type") or "") if hasattr(headers, "get") else ""
        return Answer(
            status, raw, kind.split(";")[0].strip().lower(), self.scrub(_kept(headers)), unread
        )

    # -- refusals ------------------------------------------------------------

    @staticmethod
    def error_form(raw: bytes, status: int) -> bool:
        """True when ``raw`` has the answer form of a refusal: a JSON object whose
        ``responseCode`` is ``status`` and which carries a ``message``."""
        try:
            data = parse_json(raw)
        except ValueError:
            return False
        if not isinstance(data, Mapping):
            return False
        code = data.get("responseCode")
        return (
            isinstance(code, int)
            and not isinstance(code, bool)
            and code == status
            and isinstance(data.get("message"), str)
        )

    def detail(self, raw: bytes) -> str:
        """Jotform's own words about a refusal (``message``); never the API key."""
        try:
            data = self.scrub(parse_json(raw))
        except ValueError:
            text = re.sub(r"<[^>]+>", " ", raw.decode("utf-8", "replace"))
            return errors.safe_text(self.scrub(text), 200)
        if not isinstance(data, Mapping):
            return errors.safe_text(data, 200)
        parts: list[str] = []
        for key in ("message", "content", "error"):
            value = data.get(key)
            if isinstance(value, str) and value.strip() and value.strip() not in parts:
                parts.append(value.strip())
        return errors.safe_text("; ".join(parts), 900)

    def refusal(
        self,
        status: int,
        raw: bytes,
        call: Call,
        *,
        mutating: bool,
        headers: Mapping[str, str] | None = None,
    ) -> ExtensionError:
        shown = call.shown
        detail = self.detail(raw)
        suffix = f": {detail}" if detail else ""
        retry_after = parse_retry_after((headers or {}).get("Retry-After"))
        documented = str(status) in call.refusals
        certain = not mutating or (
            documented and (not call.refusals[str(status)] or self.error_form(raw, status))
        )
        if status == 429:
            code = errors.RATE_LIMITED
            wait = f"; it asks to wait {int(retry_after)} s" if retry_after else ""
            message = (
                f"Jotform refused {shown}: the request limit is reached (HTTP 429){wait}{suffix}. "
                "The number of API calls a day depends on the plan"
            )
        elif status == 401:
            code = errors.SETUP_REQUIRED
            message = (
                f"Jotform refused the API key for {shown} (HTTP 401){suffix}. Check the key in "
                "My Account → API and the connection's region (standard, EU or HIPAA)"
            )
        elif status == 403:
            code = errors.AUTHENTICATION_FAILED
            message = (
                f"Jotform refused {shown} (HTTP 403){suffix}. A key with read access cannot "
                "change data: give it full access in My Account → API"
            )
        elif 300 <= status < 400:
            code = errors.REDIRECT_REJECTED
            message = f"Jotform redirected {shown} (HTTP {status}); redirects are not followed"
        elif status == 404:
            code = errors.NOT_FOUND
            message = f"Jotform found nothing for {shown} (HTTP 404){suffix}"
        elif status == 409:
            code = errors.CONFLICT
            message = f"Jotform refused {shown} as a conflict (HTTP 409){suffix}"
        elif status in {400, 422}:
            code = errors.UPSTREAM_VALIDATION_FAILED
            message = f"Jotform refused {shown} (HTTP {status}){suffix}"
        elif status >= 500 or status == 408:
            code = errors.TIMEOUT if status in {408, 504} else errors.UPSTREAM_FAILURE
            message = f"Jotform could not complete {shown} (HTTP {status}){suffix}"
        else:
            code = errors.UPSTREAM_VALIDATION_FAILED
            message = f"Jotform rejected {shown} (HTTP {status}){suffix}"
        if not certain:
            return unknown(message + CHECK, code, status)
        if mutating:
            message += "; nothing was changed"
        return ExtensionError(
            code,
            message,
            failure_class="provider",
            retryable=not mutating and (status >= 500 or status in {408, 429}),
            definitely_no_external_effect=True,
            external_effect_status="failed",
            http_status=status,
            retry_after_seconds=retry_after if status == 429 and not mutating else None,
        )


def undocumented(status: int, call: Call, *, mutating: bool) -> ExtensionError:
    """A 2xx answer the operation does not document: not taken as success."""
    message = (
        f"Jotform answered {call.shown} with HTTP {status}, which the API documentation does "
        f"not document for it (documented: {', '.join(call.success)})"
    )
    if mutating:
        return unknown(message + CHECK, errors.INVALID_RESPONSE, status)
    return errors.no_effect(
        errors.INVALID_RESPONSE,
        message,
        failure_class="provider",
        retryable=False,
        http_status=status,
    )


def unknown(message: str, code: str, status: int | None) -> ExtensionError:
    return ExtensionError(
        code,
        message,
        failure_class="provider",
        retryable=False,
        definitely_no_external_effect=False,
        external_effect_status="timeout_unknown",
        http_status=status,
    )


def _kept(headers: Any) -> dict[str, str]:
    kept: dict[str, str] = {}
    if headers is None or not hasattr(headers, "get"):
        return kept
    for name in KEPT_HEADERS:
        value = headers.get(name)
        if isinstance(value, str) and value.strip():
            kept[name] = errors.safe_text(value, 2000)
    return kept


def dumps_json(value: Any) -> str:
    """JSON with ``Decimal`` written as an exact number (never through float).

    A Decimal outside ``numbers``' bounds is written as text in its own exponential
    notation, never expanded."""
    marker = secrets.token_hex(8)

    def default(item: Any) -> str:
        if isinstance(item, Decimal) and numbers.bounded(item):
            return f"@{marker}@{numbers.plain(item)}@{marker}@"
        if isinstance(item, Decimal):
            return str(item)
        raise TypeError(f"{type(item).__name__} is not JSON")

    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=default)
    return re.sub(rf'"@{marker}@([-+0-9.]+)@{marker}@"', r"\1", text)


def _answer_number(integer: bool) -> Callable[[str], Any]:
    def read(text: str) -> Any:
        number = numbers.read(text, integer=integer)
        # Outside the bounds: kept as the account wrote it, as text, never expanded.
        return text if number is None else number

    return read


_ANSWER_FLOAT = _answer_number(False)
_ANSWER_INT = _answer_number(True)


class TooDeep(ValueError):
    """The answer nests deeper than ``depth.MAX_ANSWER_DEPTH`` levels; it is not read."""


def parse_json(raw: bytes) -> Any:
    """Any JSON value, numbers with a point read as Decimal; ValueError otherwise.

    A number outside ``numbers``' bounds (and NaN or Infinity) is kept as the text the
    account wrote, so reading it never expands it or fails on it. The nesting is counted
    on the raw bytes first: an answer deeper than ``depth.MAX_ANSWER_DEPTH`` raises
    ``TooDeep`` (a ValueError) and never reaches the recursive JSON reader."""
    if depth.too_deep(raw, depth.MAX_ANSWER_DEPTH):
        raise TooDeep(f"nested deeper than {depth.MAX_ANSWER_DEPTH} levels")
    try:
        text = raw.decode("utf-8-sig", "strict") if raw else ""
    except UnicodeDecodeError as exc:
        raise ValueError("not UTF-8") from exc
    if not text.strip():
        raise ValueError("empty")
    try:
        return json.loads(
            text, parse_float=_ANSWER_FLOAT, parse_int=_ANSWER_INT, parse_constant=str
        )
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("bad JSON") from exc


def read_bounded(
    response: Any,
    limit: int,
    *,
    mutating: bool = False,
    expires: float | None = None,
    clock: Callable[[], float] = time.monotonic,
    per_read: float | None = None,
) -> bytes:
    """Read at most ``limit`` bytes before ``expires``; a longer answer is an error."""
    buffer = bytearray()
    sock = _socket_of(response)
    while True:
        if expires is not None:
            left = expires - clock()
            if left <= 0:
                _late(mutating)
            if sock is not None:
                try:
                    sock.settimeout(max(0.5, min(left, per_read or left)))
                except OSError:  # pragma: no cover - a closed socket fails the read below
                    pass
        chunk = response.read(min(CHUNK_BYTES, limit + 1 - len(buffer)))
        if not chunk:
            break
        buffer.extend(chunk)
        if expires is not None and clock() > expires:
            _late(mutating)
        if len(buffer) > limit:
            if mutating:
                raise unknown(
                    "Jotform's answer was too large to read" + CHECK,
                    errors.RESPONSE_TOO_LARGE,
                    None,
                )
            raise errors.no_effect(
                errors.RESPONSE_TOO_LARGE,
                f"Jotform's answer is larger than the {limit // (1024 * 1024)} MB this "
                "extension reads; narrow the request",
            )
    return bytes(buffer)


def _late(mutating: bool) -> None:
    if not mutating:
        raise DeadlineReached
    raise ExtensionError(
        errors.TIMEOUT_UNKNOWN,
        "Jotform's answer did not arrive in time" + CHECK,
        failure_class="transient",
        retryable=False,
        definitely_no_external_effect=False,
        external_effect_status="timeout_unknown",
    )


def _socket_of(response: Any) -> Any:
    for path in (("fp", "raw", "_sock"), ("fp", "fp", "raw", "_sock"), ("_sock",)):
        node = response
        for name in path:
            node = getattr(node, name, None)
        if node is not None and hasattr(node, "settimeout"):
            return node
    return None


def _transport_failure_facts(*, mutating: bool) -> dict[str, Any]:
    return {
        "failure_class": "transient",
        "retryable": not mutating,
        "definitely_no_external_effect": not mutating,
        "external_effect_status": "timeout_unknown" if mutating else "failed",
    }


__all__ = [
    "ACCEPT",
    "CHECK",
    "FORM",
    "JSON_BODY",
    "MIN_CALL_WINDOW_SECONDS",
    "MIN_INTERVAL_SECONDS",
    "Answer",
    "Call",
    "DeadlineReached",
    "JotformTransport",
    "TooDeep",
    "dumps_json",
    "parse_json",
    "read_bounded",
    "undocumented",
    "unknown",
]
