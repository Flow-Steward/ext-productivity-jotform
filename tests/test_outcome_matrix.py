"""Table T: the outcome of a write, decided in one place (runtime/outcome.py), for every
cell of status × Content-Type × body × class of step."""

from __future__ import annotations

import json
from email.message import Message
from typing import Any

import pytest
from support import FakeJotform, Response, ok, run

FORM = "30693660548966"
QUESTIONS = {"1": {"qid": "1", "name": "email", "type": "control_email"}}


def answer(content: Any, code: int = 200) -> bytes:
    return json.dumps(
        {"responseCode": code, "message": "success", "content": content, "limit-left": 5}
    ).encode()


#: One write step per class: (step, input, method and path, a good body, a body of the
#: wrong form, a body refusing with a status the operation documents).
STEPS: dict[str, tuple[str, dict[str, Any], str, bytes, bytes, bytes]] = {
    "confirm": (
        "add_form_webhook",
        {"id": FORM, "webhook_url": "https://hooks.example.com/a"},
        f"POST /form/{FORM}/webhooks",
        answer({"0": "https://hooks.example.com/a"}),
        b'{"content": {"0": "https://hooks.example.com/a"}}',
        json.dumps({"responseCode": 404, "message": "Form not found"}).encode(),
    ),
    "confirm_batch": (
        "add_submissions_to_form",
        {"id": FORM, "submission": [{"1": {"text": "a"}}]},
        f"PUT /form/{FORM}/submissions",
        answer([{"submissionID": "1", "URL": "x"}]),
        answer({"submissionID": "1"}),
        json.dumps({"responseCode": 400, "message": "Question ID is not in request"}).encode(),
    ),
    "confirm_create": (
        "create_submission",
        {"form_id": FORM, "answers": {"1": "a@b.c"}},
        f"POST /form/{FORM}/submissions",
        answer({"submissionID": "77", "URL": "x"}),
        answer({"URL": "x"}),
        json.dumps({"responseCode": 400, "message": "Question ID is not in request"}).encode(),
    ),
}
STATUSES = [200, 201]  # documented, and a 2xx the documentation does not give
TYPES = ["application/json", "text/html", ""]
BODIES = [
    "empty",
    "good",
    "wrong_form",
    "no_json_start",
    "unparsable",
    "unread",
    "too_deep",
    "refused_in_body",
    "other_code",
]


class Answer(Response):
    """A 2xx answer with the given Content-Type (none when empty) and body state."""

    def __init__(self, status: int, content_type: str, body: bytes, endless: bool) -> None:
        super().__init__(status, body)
        self.headers = Message()
        if content_type:
            self.headers["Content-Type"] = content_type
        self.endless = endless

    def read(self, size: int = -1) -> bytes:
        if self.endless:
            return b" " * (65536 if size < 0 else size)
        return super().read(size)


def body_of(state: str, step: str) -> tuple[bytes, bool]:
    _, _, _, good, wrong, refused = STEPS[step]
    return {
        "empty": (b"", False),
        "good": (good, False),
        "wrong_form": (wrong, False),
        "no_json_start": (b"ok", False),
        "unparsable": (b"{bad json", False),
        "unread": (b"", True),
        "too_deep": (("[" * 60 + "]" * 60).encode(), False),
        "refused_in_body": (refused, False),
        "other_code": (json.dumps({"responseCode": 500, "message": "Oops"}).encode(), False),
    }[state]


def expected(status: int, content_type: str, state: str, step: str) -> str:
    """Table T, written out independently of the code under test."""
    if status != 200:
        return "unknown"  # T1
    if content_type and content_type != "application/json":
        return "unknown"  # T2
    if state in ("no_json_start", "unparsable"):
        return "unknown"  # T3
    if state in ("unread", "too_deep"):
        return "unknown"  # T4a: the confirmation is in the body
    if state in ("empty", "other_code"):
        return "unknown"  # T5a: no confirmation
    if state == "refused_in_body":
        return "refused"  # T5a: a documented refusal, nothing changed
    if state == "wrong_form":  # T5
        return {"confirm": "unknown", "confirm_batch": "unanswered", "confirm_create": "no_id"}[
            step
        ]
    return "success"  # T6


CELLS = [
    pytest.param(s, t, b, c, id=f"{s}-{t or 'none'}-{b}-{c}")
    for s in STATUSES
    for t in TYPES
    for b in BODIES
    for c in STEPS
]


@pytest.mark.parametrize(("status", "content_type", "state", "step"), CELLS)
def test_table_t_decides_every_write_outcome(
    status: int, content_type: str, state: str, step: str
) -> None:
    operation, given, route, *_ = STEPS[step]
    body, endless = body_of(state, step)
    routes: dict[str, Any] = {route: [Answer(status, content_type, body, endless)]}
    if step == "confirm_create":
        routes[f"GET /form/{FORM}/questions"] = ok(QUESTIONS)
    fake = FakeJotform(routes=routes)
    result = run(operation, given, fake)
    outcome = expected(status, content_type, state, step)
    if outcome in ("unknown", "no_id"):
        assert result["ok"] is False, (outcome, result)
        assert result["external_effect_status"] == "timeout_unknown", result
        assert result["definitely_no_external_effect"] is False
        assert ("was created" in result["error"]) == (outcome == "no_id"), result
        assert result["result"] == {"warnings": []}
        return
    if outcome == "refused":
        assert result["ok"] is False, result
        assert result["definitely_no_external_effect"] is True, result
        assert result["external_effect_status"] == "failed"
        assert "nothing was changed" in result["error"]
        return
    assert result["ok"] is True, (outcome, result)
    assert result["external_effect_status"] == "succeeded"
    out = result["result"]
    if outcome == "unanswered":
        assert out["applied"] is None and out["unanswered"] == 1 and out["warnings"], out
        return
    assert out["applied"] is True and out["processing"] == "completed", out
    assert out["limit_left"] == 5
    if step == "confirm_batch":
        assert out["unanswered"] == 0
    if step == "confirm_create":
        assert out["submission_id"] == "77"


def test_the_matrix_covers_every_cell() -> None:
    assert len(CELLS) == 2 * 3 * 9 * 3


def test_a_late_body_after_a_documented_status_leaves_the_write_unknown() -> None:
    """The status alone never confirms a Jotform write (T4a)."""
    from runtime import transport

    fake = FakeJotform(
        routes={f"POST /form/{FORM}/webhooks": [Answer(200, "application/json", b"", True)]}
    )
    result = run(
        "add_form_webhook", {"id": FORM, "webhook_url": "https://hooks.example.com/a"}, fake
    )
    assert result["external_effect_status"] == "timeout_unknown"
    assert transport.MAX_ANSWER_BYTES > 0
