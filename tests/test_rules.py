"""The standing rules: the connection and its key, numbers, the output budget, rate
limits, deadlines, error envelopes and the pair "no effect" for a write that sent
nothing."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from decimal import Decimal
from typing import Any

import pytest
from support import (
    API_KEY,
    BUNDLE,
    Clock,
    FakeJotform,
    ok,
    page,
    payload,
    raw,
    refuse,
    run,
    text_of,
)

from runtime import budget, connection, results

FORM = "30693660548966"


# -- connection --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("config", "secrets", "code"),
    [
        ({"region": "mars"}, {"api_key": API_KEY}, "setup_required"),
        ({"region": "eu"}, {"api_key": "short"}, "setup_required"),
        ({"region": "eu"}, {"api_key": API_KEY + " x"}, "setup_required"),
        ({"region": "eu"}, {}, "setup_required"),
        ({"region": "eu", "base_url": "https://evil"}, {"api_key": API_KEY}, "invalid_connection"),
        ({"region": "eu"}, {"api_key": API_KEY, "token": "x"}, "invalid_connection"),
    ],
)
def test_a_connection_is_a_documented_region_and_a_usable_key(
    config: dict[str, Any], secrets: dict[str, Any], code: str
) -> None:
    conn = {
        "connection_id": "conn-1",
        "connection_type": "jotform",
        "config": config,
        "secrets": secrets,
    }
    result = run("test_connection", {}, FakeJotform(), connection=conn)
    assert result["error_code"] == code, result
    assert API_KEY not in text_of(result)


def test_no_region_is_the_standard_address() -> None:
    conn = {
        "connection_id": "conn-1",
        "connection_type": "jotform",
        "config": {},
        "secrets": {"api_key": API_KEY},
    }
    fake = FakeJotform(routes={"GET /user": ok({"username": "a"})})
    assert run("test_connection", {}, fake, connection=conn)["ok"] is True
    assert fake.calls[0].host == "api.jotform.com"


def test_the_key_forms_are_computed_once_per_connection() -> None:
    conn = connection.Connection(connection_id="c", region="eu", _api_key=API_KEY)
    first = conn.secret_forms()
    assert API_KEY in first and API_KEY.upper() in first
    assert conn.secret_forms() is first
    assert API_KEY not in repr(conn)


# -- numbers -----------------------------------------------------------------------------


def invoke(raw_request: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "main.py"],
        cwd=BUNDLE,
        input=raw_request,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return proc.returncode, proc.stdout


def with_number(number: str, *, test_mode: bool) -> str:
    request = json.dumps(
        payload(
            "create_submission", {"form_id": FORM, "answers": {"1": "@N@"}}, test_mode=test_mode
        )
    )
    return request.replace('"@N@"', number)


@pytest.mark.parametrize("number", ["1e1000000", "9" * 5000, "1" * 41, "1e31", "NaN", "-Infinity"])
def test_a_number_outside_the_bounds_is_refused_before_anything_is_sent(number: str) -> None:
    for test_mode in (True, False):
        code, out = invoke(with_number(number, test_mode=test_mode))
        assert len(out) < 2000
        response = json.loads(out)
        assert code == 2 and response["error_code"] == "invalid_payload", response
        assert response["definitely_no_external_effect"] is True


def test_an_exact_decimal_answer_is_sent_as_written() -> None:
    fake = FakeJotform(
        routes={
            f"GET /form/{FORM}/questions": ok({"1": {"qid": "1"}}),
            f"POST /form/{FORM}/submissions": ok({"submissionID": "5"}),
        }
    )
    run(
        "create_submission",
        {"form_id": FORM, "answers": {"1": Decimal("1234567890.12345678")}},
        fake,
    )
    assert fake.calls[1].form == [("submission[1]", "1234567890.12345678")]


def test_a_huge_number_in_an_answer_stays_text() -> None:
    body = b'{"responseCode": 200, "message": "success", "content": {"n": 1e1000000}}'
    result = run("get_form", {"id": "1"}, FakeJotform(raw(200, body)))
    assert result["ok"] is True and result["result"]["data"]["n"] == "1e1000000"


def test_no_number_is_written_out_bypassing_numbers_plain() -> None:
    plain_format = re.compile(r"""format\([^()]*,\s*["']f["']\s*\)|\{[^{}]*:f\}""")
    found = [
        f"{path.name}:{n}"
        for path in sorted((BUNDLE / "runtime").glob("*.py"))
        if path.name != "numbers.py"
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if plain_format.search(line)
    ]
    assert found == []


# -- budget ------------------------------------------------------------------------------


def endless(size: int) -> Any:
    def answer(call: Any) -> Any:
        offset, limit = int(call.q("offset")), int(call.q("limit"))
        return page([{"id": str(offset + i), "t": "x" * size} for i in range(limit)], offset, limit)

    return answer


def test_a_list_filled_to_the_brim_is_never_refused_by_the_final_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(budget, "MAX_SERIALIZED_BYTES", 30_000)
    for size in [*range(40, 400, 7), *range(2000, 9000, 397)]:
        fake = FakeJotform(routes={"GET /user/forms": endless(size)})
        result = run("list_forms", {"page_size": 10}, fake)
        assert result["ok"] is True, (size, result)
        assert result["result"]["complete"] is False


def test_submissions_filled_to_the_brim_keep_their_cursor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(budget, "MAX_SERIALIZED_BYTES", 30_000)

    def answer(call: Any) -> Any:
        offset, limit = int(call.q("offset")), int(call.q("limit"))
        rows = [
            {"id": str(10**17 + offset + i), "created_at": "2026-11-20 10:00:00", "t": "x" * 150}
            for i in range(limit)
        ]
        return page(rows, offset, limit)

    fake = FakeJotform(routes={f"GET /form/{FORM}/submissions": answer})
    result = run("get_form_submissions_since", {"form_id": FORM, "page_size": 10}, fake)
    assert result["ok"] is True, result
    assert result["result"]["complete"] is False and result["result"]["next_offset"]


def test_a_write_result_too_large_is_cut_and_stays_a_success() -> None:
    result: dict[str, Any] = {
        "status": 200,
        "data": {"id": "1", "big": "x" * 4_000_000},
        "warnings": [],
    }
    cut = results.fit_write_result(result)
    assert budget.fits(cut) and cut["data"] == {"id": "1"}
    assert any("too large" in w for w in cut["warnings"])


# -- rate and time -----------------------------------------------------------------------


def test_a_read_refused_with_429_waits_and_tries_again() -> None:
    clock = Clock()
    fake = FakeJotform(refuse(429, Retry_After="2"), ok({"id": "1"}))
    result = run("get_form", {"id": "1"}, fake, clock=clock)
    assert result["ok"] is True and 2.0 in clock.slept and len(fake.calls) == 2


def test_a_write_refused_with_429_is_never_sent_again() -> None:
    fake = FakeJotform(refuse(429, Retry_After="2"))
    result = run("delete_report", {"id": "1"}, fake)
    assert len(fake.calls) == 1 and result["ok"] is False


def test_requests_are_spaced() -> None:
    clock = Clock()
    fake = FakeJotform(routes={"GET /user/forms": [page([{"id": "1"}], 0, 1), page([], 1, 1)]})
    run("list_forms", {"page_size": 1}, fake, clock=clock)
    assert clock.slept and all(s <= 0.1 for s in clock.slept)


def test_a_read_after_the_deadline_is_not_started() -> None:
    from runtime import transport

    clock = Clock()

    def slow(call: Any) -> Any:
        clock.now += 430
        return page([{"id": "1"}], 0, 1)

    fake = FakeJotform(routes={"GET /user/forms": [slow, page([], 1, 1)]})
    result = run("list_forms", {"page_size": 1}, fake, clock=clock)
    assert result["ok"] is True and result["result"]["complete"] is False
    assert len(fake.calls) == 1 and transport.MIN_CALL_WINDOW_SECONDS > 0


# -- envelopes ---------------------------------------------------------------------------


def test_every_error_envelope_carries_warnings() -> None:
    result = run("get_form", {"id": "1"}, FakeJotform(refuse(404)))
    assert result["result"] == {"warnings": []} and result["warnings"] == []


def test_an_error_text_never_carries_the_key() -> None:
    body = {"responseCode": 404, "message": f"no form for key {API_KEY}"}
    result = run("get_form", {"id": "1"}, FakeJotform(refuse(404, body)))
    assert API_KEY not in text_of(result) and "[redacted]" in result["error"]


def test_a_write_that_sent_nothing_is_the_pair_no_effect() -> None:
    hook = "https://hooks.example.com/a"
    fake = FakeJotform(routes={f"GET /form/{FORM}/webhooks": ok({"0": hook})})
    result = run("add_webhook_if_new", {"form_id": FORM, "webhook_url": hook}, fake)
    assert result["ok"] is True
    assert result["external_effect_status"] == "failed"
    assert result["definitely_no_external_effect"] is True
