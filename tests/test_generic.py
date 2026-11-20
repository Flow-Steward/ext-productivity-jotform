"""The generated steps send their documented request and read the documented answer."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

import pytest
from support import API_KEY, FakeJotform, ok, raw, refuse, run

from runtime import generic

REGISTRY = generic.registry()


def sample_input(entry: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """The least input a step runs with, and the path it must call."""
    given: dict[str, Any] = {}
    path = entry["path"]
    for prm in entry["path_params"]:
        value = (prm["node"].get("allowed") or ["31751954731962"])[0]
        given[prm["input"]] = value
        path = path.replace("{" + prm["token"] + "}", quote(value, safe=""))
    for prm in entry["query"] + entry["form"]:
        if prm["node"]["required"]:
            given[prm["input"]] = (
                {"name": "x"}
                if prm["node"]["kind"] == "json_text"
                else (prm["node"].get("allowed") or ["x"])[0]
            )
    for group in entry["groups"]:
        if group["required"]:
            given[group["input"]] = {"1": "x"}
    body = entry["json_body"]
    if body and body["required"]:
        given[body["input"]] = [{"1": {"text": "a"}}] if body["type"] == "array" else {"a": "b"}
    return given, path


@pytest.mark.parametrize("operation_id", sorted(REGISTRY))
def test_every_generated_step_runs_its_documented_request(operation_id: str) -> None:
    entry = REGISTRY[operation_id]
    given, path = sample_input(entry)
    content: Any = (
        [{"submissionID": "1"}] if entry.get("step_class") == "confirm_batch" else {"id": "1"}
    )
    fake = FakeJotform(ok(content))
    result = run(operation_id, given, fake)
    assert result["ok"] is True, result
    call = fake.calls[0]
    assert call.verb == entry["method"] and call.path == path
    assert call.host == "api.jotform.com" and call.headers["apikey"] == API_KEY
    assert "apikey" not in {k.lower() for k, _ in call.query}
    out = result["result"]
    assert out["status"] == 200 and out["data"] == content and out["limit_left"] == 900
    assert ("result_set" in out) == entry["paged"]
    if entry["kind"] == "write":
        assert result["external_effect_status"] == "succeeded"
        assert out["processing"] == "completed" and out["applied"] is True
        if entry["json_body"]:
            assert call.headers["content-type"] == "application/json"
        elif call.raw_body:
            assert call.headers["content-type"] == "application/x-www-form-urlencoded"
    else:
        assert "external_effect_status" not in result


def test_a_group_of_form_fields_is_sent_in_the_documented_bracket_form() -> None:
    fake = FakeJotform(ok({"title": "x"}))
    given = {
        "questions": {"0": {"type": "control_head", "text": "Title"}},
        "properties": {"title": "New Form"},
    }
    result = run("create_form", given, fake)
    assert result["ok"] is True, result
    assert fake.calls[0].form == [
        ("questions[0][type]", "control_head"),
        ("questions[0][text]", "Title"),
        ("properties[title]", "New Form"),
    ]


def test_a_json_body_is_sent_as_the_documentation_shows_it() -> None:
    fake = FakeJotform(ok([{"submissionID": "1"}, {"submissionID": "2"}]))
    body = [{"1": {"text": "a"}}, {"1": {"text": "b"}}]
    result = run("add_submissions_to_form", {"id": "1", "submission": body}, fake)
    assert result["ok"] is True and result["result"]["unanswered"] == 0
    assert json.loads(fake.calls[0].raw_body) == body


def test_a_json_post_parameter_is_one_form_field_of_json_text() -> None:
    fake = FakeJotform(ok({"name": "Ops"}))
    run("update_label", {"id": "abc", "property": {"name": "Ops", "color": "#23FFDD"}}, fake)
    form = dict(fake.calls[0].form)
    assert json.loads(form["property"]) == {"name": "Ops", "color": "#23FFDD"}


def test_query_parameters_are_typed_as_documented() -> None:
    fake = FakeJotform(ok([]))
    result = run(
        "get_form_submissions",
        {"id": "1", "offset": 20, "limit": 1000, "filter": {"new": "1"}, "orderby": "created_at"},
        fake,
    )
    assert result["ok"] is True
    query = dict(fake.calls[0].query)
    assert query == {
        "offset": "20",
        "limit": "1000",
        "filter": '{"new":"1"}',
        "orderby": "created_at",
    }
    for bad in ({"limit": 1001}, {"offset": -1}, {"orderby": "price"}, {"filter": {"x y": 1}}):
        refused = run("get_form_submissions", {"id": "1", **bad}, FakeJotform())
        assert refused["error_code"] == "invalid_payload", bad


@pytest.mark.parametrize("value", ["02/30/2026", "2026-01-31", "13/01/2026"])
def test_history_dates_must_be_real_dates_written_as_documented(value: str) -> None:
    result = run("get_account_history", {"start_date": value}, FakeJotform())
    assert result["error_code"] == "invalid_payload" and "MM/DD/YYYY" in result["error"]


def test_a_documented_path_value_list_is_enforced() -> None:
    assert run("get_plan_details", {"plan_name": "DIAMOND"}, FakeJotform())["error_code"] == (
        "invalid_payload"
    )


def test_a_path_value_cannot_leave_its_segment() -> None:
    fake = FakeJotform(ok({}))
    run("get_form", {"id": "1/../../user"}, fake)
    assert fake.calls[0].path == "/form/1%2F..%2F..%2Fuser"


def test_an_unknown_input_is_refused() -> None:
    assert run("get_form", {"id": "1", "x": 1}, FakeJotform())["error_code"] == "invalid_payload"


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"responseCode": 404, "message": "Form not found"}, "not_found"),
        ({"responseCode": 401, "message": "You're not authorized"}, "setup_required"),
        ({"message": "odd"}, "invalid_response"),
        ([1, 2], "invalid_response"),
    ],
)
def test_a_read_without_response_code_200_is_refused(body: Any, code: str) -> None:
    fake = FakeJotform(raw(200, json.dumps(body).encode()))
    result = run("get_form", {"id": "1"}, fake)
    assert result["error_code"] == code, result
    assert result["definitely_no_external_effect"] is True


def test_a_read_answered_with_an_undocumented_2xx_is_an_invalid_answer() -> None:
    fake = FakeJotform(ok({"id": "1"}, status=203))
    result = run("get_form", {"id": "1"}, fake)
    assert result["error_code"] == "invalid_response" and "203" in result["error"]


def test_a_write_answered_with_an_undocumented_2xx_is_unknown() -> None:
    fake = FakeJotform(ok(True, status=202))
    result = run("delete_report", {"id": "1"}, fake)
    assert result["external_effect_status"] == "timeout_unknown"


def test_an_undocumented_refusal_of_a_write_leaves_it_unknown() -> None:
    fake = FakeJotform(refuse(500))
    result = run("delete_report", {"id": "1"}, fake)
    assert result["external_effect_status"] == "timeout_unknown"
    assert result["definitely_no_external_effect"] is False


def test_a_documented_refusal_of_a_write_in_the_answer_form_changed_nothing() -> None:
    fake = FakeJotform(refuse(404))
    result = run("delete_report", {"id": "1"}, fake)
    assert result["error_code"] == "not_found" and result["definitely_no_external_effect"] is True
    odd = run("delete_report", {"id": "1"}, FakeJotform(refuse(404, b"<html>not found</html>")))
    assert odd["external_effect_status"] == "timeout_unknown"


def test_a_test_run_of_a_generated_write_sends_nothing() -> None:
    fake = FakeJotform()
    result = run("delete_form", {"id": "1"}, fake, test_mode=True)
    assert result["ok"] is True and fake.calls == []
    out = result["result"]
    assert out["processing"] is None and out["applied"] is False and out["check"] is None
    assert result["definitely_no_external_effect"] is True
    batch = run(
        "add_submissions_to_form", {"id": "1", "submission": [{"1": "a"}]}, fake, test_mode=True
    )
    assert batch["result"]["unanswered"] is None
    bad = run("delete_form", {}, fake, test_mode=True)
    assert bad["error_code"] == "invalid_payload"
