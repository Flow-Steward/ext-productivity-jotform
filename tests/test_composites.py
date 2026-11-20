"""The everyday steps against a fake Jotform API."""

from __future__ import annotations

import json
from typing import Any

import pytest
from support import API_KEY, Artifacts, FakeJotform, ok, page, raw, refuse, run, text_of

FORM = "30693660548966"


def sub(ident: str, created: str, **extra: Any) -> dict[str, Any]:
    return {"id": ident, "form_id": FORM, "created_at": created, "status": "ACTIVE", **extra}


QUESTIONS = {
    "1": {"qid": "1", "name": "email", "text": "E-mail", "type": "control_email", "order": "2"},
    "2": {
        "qid": "2",
        "name": "fullName",
        "text": "Name",
        "type": "control_fullname",
        "order": "1",
        "sublabels": {"first": "First", "last": "Last"},
    },
}


# -- test connection ---------------------------------------------------------------------


def test_the_connection_test_reads_the_account_with_the_key_in_the_header_only() -> None:
    fake = FakeJotform(
        routes={"GET /user": ok({"username": "ann", "name": "Ann", "account_type": "x/GOLD"})}
    )
    result = run("test_connection", {}, fake)
    assert result["ok"] is True, result
    out = result["result"]
    assert out["connected"] is True and out["username"] == "ann" and out["limit_left"] == 900
    call = fake.calls[0]
    assert call.host == "api.jotform.com" and call.headers["apikey"] == API_KEY
    assert API_KEY not in call.url


@pytest.mark.parametrize(
    ("region", "host"),
    [
        ("eu", "eu-api.jotform.com"),
        ("hipaa", "hipaa-api.jotform.com"),
        ("standard", "api.jotform.com"),
    ],
)
def test_the_region_chooses_the_documented_api_address(region: str, host: str) -> None:
    fake = FakeJotform(routes={"GET /user": ok({"username": "ann"})})
    assert run("test_connection", {}, fake, region=region)["ok"] is True
    assert fake.calls[0].host == host


def test_a_refused_key_says_to_check_the_key_and_the_region() -> None:
    fake = FakeJotform(routes={"GET /user": refuse(401)})
    result = run("test_connection", {}, fake)
    assert result["error_code"] == "setup_required"
    assert "region" in result["error"] and result["result"] == {"warnings": []}


# -- list forms --------------------------------------------------------------------------


def forms(start: int, n: int) -> list[dict[str, Any]]:
    return [{"id": str(start + i), "title": f"Form {start + i}"} for i in range(n)]


def test_list_forms_reads_whole_pages_until_a_short_one() -> None:
    fake = FakeJotform(routes={"GET /user/forms": [page(forms(0, 3)), page(forms(3, 1))]})
    result = run("list_forms", {"page_size": 3, "orderby": "created_at"}, fake)
    out = result["result"]
    assert out["count"] == 4 and out["complete"] is True and out["next_offset"] is None
    assert [c.q("offset") for c in fake.calls] == ["0", "3"]
    assert all(c.q("limit") == "3" and c.q("orderby") == "created_at" for c in fake.calls)


def test_the_maximum_inside_a_page_asks_only_the_rest() -> None:
    rows = forms(0, 6)

    def answer(call: Any) -> Any:
        offset, limit = int(call.q("offset")), int(call.q("limit"))
        return page(rows[offset : offset + limit], offset, limit)

    fake = FakeJotform(routes={"GET /user/forms": answer})
    out = run("list_forms", {"page_size": 3, "max_records": 4}, fake)["result"]
    assert [(c.q("offset"), c.q("limit")) for c in fake.calls] == [("0", "3"), ("3", "1")]
    assert out["count"] == 4 and out["complete"] is False and out["next_offset"] == 4
    assert "next_offset 4" in out["warnings"][-1]


def test_max_records_limits_the_first_page_and_the_rest_continues_exactly() -> None:
    rows = forms(0, 3)

    def answer(call: Any) -> Any:
        offset, limit = int(call.q("offset")), int(call.q("limit"))
        return page(rows[offset : offset + limit], offset, limit)

    fake = FakeJotform(routes={"GET /user/forms": answer})
    out = run("list_forms", {"page_size": 10, "max_records": 1}, fake)["result"]
    assert [(c.q("offset"), c.q("limit")) for c in fake.calls] == [("0", "1")]
    assert [f["id"] for f in out["forms"]] == ["0"]
    assert out["count"] == 1 and out["complete"] is False and out["next_offset"] == 1
    given = {"page_size": 10, "start_offset": out["next_offset"]}
    rest = run("list_forms", given, FakeJotform(routes={"GET /user/forms": answer}))["result"]
    assert [f["id"] for f in rest["forms"]] == ["1", "2"] and rest["complete"] is True


def test_max_records_limits_the_first_page_of_submissions_too() -> None:
    rows = [sub(str(20 + i), f"2026-11-20 10:00:0{i}") for i in range(3)]
    fake = FakeJotform(routes={f"GET /form/{FORM}/submissions": window(rows)})
    out = run(
        "get_form_submissions_since", {"form_id": FORM, "page_size": 10, "max_records": 1}, fake
    )["result"]
    assert [c.q("limit") for c in fake.calls] == ["1"]
    assert [s["id"] for s in out["submissions"]] == ["20"]
    assert out["complete"] is False and out["next_offset"] == 1


def test_a_filter_is_sent_as_json_text_and_its_dates_must_be_real() -> None:
    fake = FakeJotform(routes={"GET /user/forms": [page([])]})
    out = run("list_forms", {"filter": {"created_at:gt": "2026-01-02 03:04:05"}}, fake)
    assert out["ok"] is True
    assert json.loads(fake.calls[0].q("filter") or "") == {"created_at:gt": "2026-01-02 03:04:05"}
    bad = run("list_forms", {"filter": {"created_at:gt": "2026-02-30 00:00:00"}}, FakeJotform())
    assert bad["error_code"] == "invalid_payload" and "real date" in bad["error"]


def test_a_list_to_a_file_saves_json_and_returns_no_records() -> None:
    artifacts = Artifacts()
    fake = FakeJotform(routes={"GET /user/forms": [page(forms(0, 2))]})
    out = run("list_forms", {"output": "file"}, fake, artifacts=artifacts)["result"]
    assert out["forms"] == [] and out["file"] == "artifact-1"
    assert json.loads(artifacts.saved[0]["data"])[1]["id"] == "1"


def test_a_page_too_large_for_the_output_is_read_again_smaller_and_the_next_at_full_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from runtime import budget

    monkeypatch.setattr(budget, "MAX_SERIALIZED_BYTES", 6000)
    big = [{"id": str(i), "title": "x" * 2000} for i in range(4)]

    def answer(call: Any) -> Any:
        offset, limit = int(call.q("offset")), int(call.q("limit"))
        return page(big[offset : offset + limit], offset, limit)

    fake = FakeJotform(routes={"GET /user/forms": answer})
    out = run("list_forms", {"page_size": 4}, fake)["result"]
    asked = [(c.q("offset"), c.q("limit")) for c in fake.calls]
    assert asked[0] == ("0", "4") and asked[1] == ("0", "2")
    # After a smaller page the next one is asked at the full size again.
    assert asked[2] == ("2", "4")
    assert out["complete"] is False and out["next_offset"] == 2 and out["count"] == 2
    assert out["page_size"] == 4


def test_a_list_answer_that_is_not_the_documented_list_is_invalid() -> None:
    fake = FakeJotform(routes={"GET /user/forms": [ok({"not": "a list"})]})
    assert run("list_forms", {}, fake)["error_code"] == "invalid_response"


# -- questions ---------------------------------------------------------------------------


def test_describe_form_questions_lists_them_in_form_order() -> None:
    fake = FakeJotform(routes={f"GET /form/{FORM}/questions": ok(QUESTIONS)})
    out = run("describe_form_questions", {"form_id": FORM}, fake)["result"]
    assert [q["qid"] for q in out["questions"]] == ["2", "1"]
    assert out["questions"][0]["sub_fields"] == ["first", "last"]


def test_a_form_id_must_be_digits() -> None:
    result = run("describe_form_questions", {"form_id": "../user"}, FakeJotform())
    assert result["error_code"] == "invalid_payload"


# -- submissions since -------------------------------------------------------------------


def window(rows: list[dict[str, Any]]) -> Any:
    def answer(call: Any) -> Any:
        offset, limit = int(call.q("offset")), int(call.q("limit"))
        return page(rows[offset : offset + limit], offset, limit)

    return answer


def test_submissions_since_ask_the_window_from_one_second_before_and_skip_those_read() -> None:
    rows = [
        sub("11", "2026-11-20 10:00:00"),
        sub("12", "2026-11-20 10:00:00"),
        sub("13", "2026-11-20 10:00:05"),
        sub("14", "2026-11-20 10:00:05"),
    ]
    fake = FakeJotform(routes={f"GET /form/{FORM}/submissions": window(rows)})
    result = run(
        "get_form_submissions_since",
        {"form_id": FORM, "since": "2026-11-20 10:00:00", "after_ids": ["11"]},
        fake,
    )
    out = result["result"]
    flt = json.loads(fake.calls[0].q("filter") or "")
    assert flt == {"created_at:gt": "2026-11-20 09:59:59"}
    assert fake.calls[0].q("orderby") == "created_at"
    assert [s["id"] for s in out["submissions"]] == ["12", "13", "14"]
    assert out["complete"] is True
    assert out["next_since"] == "2026-11-20 10:00:05" and out["next_after_ids"] == ["13", "14"]


def test_the_cursor_does_not_depend_on_the_order_of_the_answer() -> None:
    rows = [sub("14", "2026-11-20 10:00:05"), sub("12", "2026-11-20 10:00:00")]
    fake = FakeJotform(routes={f"GET /form/{FORM}/submissions": window(rows)})
    out = run("get_form_submissions_since", {"form_id": FORM}, fake)["result"]
    assert out["next_since"] == "2026-11-20 10:00:05" and out["next_after_ids"] == ["14"]
    assert "filter" not in dict(fake.calls[0].query)


def test_a_window_with_nothing_new_keeps_the_cursor() -> None:
    fake = FakeJotform(routes={f"GET /form/{FORM}/submissions": window([])})
    given = {"form_id": FORM, "since": "2026-11-20 10:00:00", "after_ids": ["11", "12"]}
    out = run("get_form_submissions_since", given, fake)["result"]
    assert out["count"] == 0 and out["complete"] is True
    assert out["next_since"] == "2026-11-20 10:00:00" and out["next_after_ids"] == ["11", "12"]


def test_the_same_moment_keeps_the_ids_read_before() -> None:
    rows = [sub("11", "2026-11-20 10:00:00"), sub("12", "2026-11-20 10:00:00")]
    fake = FakeJotform(routes={f"GET /form/{FORM}/submissions": window(rows)})
    given = {"form_id": FORM, "since": "2026-11-20 10:00:00", "after_ids": ["11"]}
    out = run("get_form_submissions_since", given, fake)["result"]
    assert out["next_since"] == "2026-11-20 10:00:00" and out["next_after_ids"] == ["11", "12"]


def test_a_run_that_stops_early_keeps_the_window_and_gives_the_offset() -> None:
    rows = [sub(str(20 + i), f"2026-11-20 10:00:0{i}") for i in range(5)]
    fake = FakeJotform(routes={f"GET /form/{FORM}/submissions": window(rows)})
    given = {"form_id": FORM, "since": "2026-11-20 09:00:00", "page_size": 2, "max_records": 3}
    out = run("get_form_submissions_since", given, fake)["result"]
    assert [c.q("limit") for c in fake.calls] == ["2", "1"]
    assert out["complete"] is False and out["count"] == 3 and out["next_offset"] == 3
    assert out["next_since"] == "2026-11-20 09:00:00" and out["next_after_ids"] == []


def jotform_window(rows: list[dict[str, Any]]) -> Any:
    """The submissions list as Jotform answers it: the created_at filter applied, the
    rows in created_at order, then offset and limit."""

    def answer(call: Any) -> Any:
        flt = json.loads(call.q("filter") or "{}")
        kept = [
            r
            for r in rows
            if r["created_at"] > flt.get("created_at:gt", "")
            and r["created_at"] < flt.get("created_at:lt", "9999")
        ]
        kept.sort(key=lambda r: r["created_at"])
        offset, limit = int(call.q("offset")), int(call.q("limit"))
        return page(kept[offset : offset + limit], offset, limit)

    return answer


def test_a_window_read_in_two_runs_gives_a_cursor_that_returns_nothing_twice() -> None:
    rows = [
        sub("11", "2026-11-20 10:00:00"),
        sub("21", "2026-11-20 10:00:05"),
        sub("22", "2026-11-20 10:00:05"),
        sub("23", "2026-11-20 10:00:05"),
        sub("24", "2026-11-20 10:00:05"),
    ]
    route = f"GET /form/{FORM}/submissions"
    first_run = {"form_id": FORM, "page_size": 2, "max_records": 3}
    first = run(
        "get_form_submissions_since", first_run, FakeJotform(routes={route: jotform_window(rows)})
    )
    one = first["result"]
    # The run stops inside the second 10:00:05; the window continues at next_offset.
    assert one["complete"] is False and one["next_since"] is None
    given = {"form_id": FORM, "page_size": 2, "start_offset": one["next_offset"]}
    fake = FakeJotform(routes={route: jotform_window(rows)})
    two = run("get_form_submissions_since", given, fake)["result"]
    assert two["complete"] is True
    assert two["next_since"] == "2026-11-20 10:00:05"
    assert sorted(two["next_after_ids"]) == ["21", "22", "23", "24"]
    cursor = json.loads(fake.calls[-1].q("filter") or "")
    assert cursor == {
        "created_at:gt": "2026-11-20 10:00:04",
        "created_at:lt": "2026-11-20 10:00:06",
    }
    returned = {s["id"] for s in one["submissions"]} | {s["id"] for s in two["submissions"]}
    assert returned == {"11", "21", "22", "23", "24"}
    third_run = {
        "form_id": FORM,
        "since": two["next_since"],
        "after_ids": two["next_after_ids"],
    }
    fake3 = FakeJotform(routes={route: jotform_window([*rows, sub("25", "2026-11-20 10:00:09")])})
    three = run("get_form_submissions_since", third_run, fake3)["result"]
    assert [s["id"] for s in three["submissions"]] == ["25"]


def test_a_cursor_second_that_cannot_be_read_keeps_the_cursor_and_is_not_complete() -> None:
    rows = [sub("21", "2026-11-20 10:00:05"), sub("22", "2026-11-20 10:00:05")]
    calls = {"n": 0}

    def answer(call: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 1:
            return jotform_window(rows)(call)
        return refuse(500)

    fake = FakeJotform(routes={f"GET /form/{FORM}/submissions": answer})
    given = {"form_id": FORM, "since": "2026-11-20 10:00:00", "after_ids": ["20"]}
    out = run("get_form_submissions_since", given, fake)["result"]
    assert [s["id"] for s in out["submissions"]] == ["21", "22"]
    assert out["complete"] is False and out["next_offset"] == 2
    assert out["next_since"] == "2026-11-20 10:00:00" and out["next_after_ids"] == ["20"]
    assert any("latest second 2026-11-20 10:00:05" in w for w in out["warnings"])


def test_older_submissions_that_come_back_are_left_out_with_a_warning() -> None:
    rows = [sub("1", "2026-11-19 10:00:00"), sub("2", "2026-11-20 10:00:01")]
    fake = FakeJotform(routes={f"GET /form/{FORM}/submissions": window(rows)})
    given = {"form_id": FORM, "since": "2026-11-20 10:00:00"}
    out = run("get_form_submissions_since", given, fake)["result"]
    assert [s["id"] for s in out["submissions"]] == ["2"]
    assert any("older than since" in w for w in out["warnings"])


@pytest.mark.parametrize(
    "given",
    [
        {"since": "2026-13-01 00:00:00"},
        {"since": "yesterday"},
        {"after_ids": ["1"]},
        {"since": "2026-11-20", "filter": {"created_at:lt": "2026-11-21"}},
    ],
)
def test_the_window_inputs_are_checked(given: dict[str, Any]) -> None:
    result = run("get_form_submissions_since", {"form_id": FORM, **given}, FakeJotform())
    assert result["error_code"] == "invalid_payload", result


# -- one submission ----------------------------------------------------------------------


def test_get_submission_answers_orders_them_by_question() -> None:
    data = {
        "id": "237955080346633702",
        "form_id": FORM,
        "created_at": "2013-06-25 03:38:00",
        "answers": {
            "4": {"text": "Your Message", "type": "control_textarea", "answer": "Hi"},
            "3": {
                "text": "Name",
                "type": "control_fullname",
                "answer": {"first": "Bart", "last": "Simpson"},
                "prettyFormat": "Bart Simpson",
            },
        },
    }
    fake = FakeJotform(routes={"GET /submission/237955080346633702": ok(data)})
    out = run("get_submission_answers", {"submission_id": "237955080346633702"}, fake)["result"]
    assert [a["qid"] for a in out["answers"]] == ["3", "4"]
    assert out["answers"][0]["pretty"] == "Bart Simpson"


# -- create submission -------------------------------------------------------------------


def test_create_submission_checks_the_questions_then_sends_the_documented_fields() -> None:
    fake = FakeJotform(
        routes={
            f"GET /form/{FORM}/questions": ok(QUESTIONS),
            f"POST /form/{FORM}/submissions": ok({"submissionID": "555", "URL": "x"}),
        }
    )
    given = {"form_id": FORM, "answers": {"1": "a@b.c", "2": {"first": "Ann", "last": "Lee"}}}
    result = run("create_submission", given, fake)
    assert result["ok"] is True, result
    out = result["result"]
    assert out["submission_id"] == "555" and out["processing"] == "completed"
    assert result["external_effect_status"] == "succeeded"
    post = fake.calls[1]
    assert post.headers["content-type"] == "application/x-www-form-urlencoded"
    assert post.form == [
        ("submission[1]", "a@b.c"),
        ("submission[2][first]", "Ann"),
        ("submission[2][last]", "Lee"),
    ]


def test_an_answer_to_a_question_the_form_does_not_have_is_refused_before_sending() -> None:
    fake = FakeJotform(routes={f"GET /form/{FORM}/questions": ok(QUESTIONS)})
    result = run("create_submission", {"form_id": FORM, "answers": {"9": "x"}}, fake)
    assert result["error_code"] == "invalid_payload" and "9" in result["error"]
    assert result["definitely_no_external_effect"] is True
    assert [c.verb for c in fake.calls] == ["GET"]


def test_the_curl_form_of_a_part_is_sent_as_given() -> None:
    fake = FakeJotform(
        routes={
            f"GET /form/{FORM}/questions": ok(QUESTIONS),
            f"POST /form/{FORM}/submissions": ok({"submissionID": "556"}),
        }
    )
    run("create_submission", {"form_id": FORM, "answers": {"2_first": "Ann"}}, fake)
    assert fake.calls[1].form == [("submission[2_first]", "Ann")]


def test_a_created_submission_without_its_id_is_reported_as_created() -> None:
    fake = FakeJotform(
        routes={
            f"GET /form/{FORM}/questions": ok(QUESTIONS),
            f"POST /form/{FORM}/submissions": ok({"URL": "x"}),
        }
    )
    result = run("create_submission", {"form_id": FORM, "answers": {"1": "x"}}, fake)
    assert result["error_code"] == "invalid_response" and "was created" in result["error"]
    assert result["external_effect_status"] == "timeout_unknown"


def test_a_documented_refusal_of_a_submission_changed_nothing() -> None:
    fake = FakeJotform(
        routes={
            f"GET /form/{FORM}/questions": ok(QUESTIONS),
            f"POST /form/{FORM}/submissions": refuse(400),
        }
    )
    result = run("create_submission", {"form_id": FORM, "answers": {"1": "x"}}, fake)
    assert result["error_code"] == "upstream_validation_failed"
    assert result["definitely_no_external_effect"] is True
    assert "nothing was changed" in result["error"]


def test_a_test_run_of_create_submission_checks_the_shape_and_sends_nothing() -> None:
    fake = FakeJotform()
    result = run(
        "create_submission", {"form_id": FORM, "answers": {"1": "x"}}, fake, test_mode=True
    )
    assert result["ok"] is True and fake.calls == []
    assert result["result"]["submission_id"] is None and result["result"]["applied"] is False
    bad = run("create_submission", {"form_id": FORM, "answers": {"x1": "y"}}, fake, test_mode=True)
    assert bad["error_code"] == "invalid_payload"


# -- download a file ---------------------------------------------------------------------


FILES = [
    {
        "name": "picture.png",
        "type": "image/png",
        "size": "4",
        "submission_id": "777",
        "url": "http://www.jotform.com/uploads/ann/30693660548966/777/picture.png",
    },
    {
        "name": "other.pdf",
        "submission_id": "888",
        "url": "https://www.jotform.com/uploads/x/1/888/o.pdf",
    },
]


def test_download_submission_file_saves_the_uploaded_file_without_the_key() -> None:
    artifacts = Artifacts()
    fake = FakeJotform(
        routes={
            f"GET /form/{FORM}/files": ok(FILES),
            "GET /uploads/ann/30693660548966/777/picture.png": raw(200, b"\x89PNG", "image/png"),
        }
    )
    result = run(
        "download_submission_file",
        {"form_id": FORM, "submission_id": "777"},
        fake,
        artifacts=artifacts,
    )
    assert result["ok"] is True, result
    out = result["result"]
    assert out["file"] == "artifact-1" and out["size_bytes"] == 4
    assert out["content_type"] == "image/png"
    fetch = fake.calls[1]
    assert (
        fetch.url.startswith("https://www.jotform.com/uploads/") and "apikey" not in fetch.headers
    )
    assert artifacts.saved[0]["content_type"] == "application/octet-stream"
    assert artifacts.saved[0]["binding_key"] == "jotform_upload"


def test_a_file_address_outside_jotform_uploads_is_not_fetched() -> None:
    bad = [{**FILES[0], "url": "https://evil.example/uploads/x.png"}]
    fake = FakeJotform(routes={f"GET /form/{FORM}/files": ok(bad)})
    result = run("download_submission_file", {"form_id": FORM, "submission_id": "777"}, fake)
    assert result["error_code"] == "invalid_response" and len(fake.calls) == 1


def test_a_web_page_instead_of_the_file_is_a_setup_matter() -> None:
    fake = FakeJotform(
        routes={
            f"GET /form/{FORM}/files": ok(FILES),
            "GET /uploads/ann/30693660548966/777/picture.png": raw(200, b"<html>", "text/html"),
        }
    )
    result = run("download_submission_file", {"form_id": FORM, "submission_id": "777"}, fake)
    assert result["error_code"] == "setup_required"


@pytest.mark.parametrize("status", [401, 403])
def test_an_upload_address_that_refuses_is_a_setup_matter(status: int) -> None:
    fake = FakeJotform(
        routes={
            f"GET /form/{FORM}/files": ok(FILES),
            "GET /uploads/ann/30693660548966/777/picture.png": refuse(status, b""),
        }
    )
    result = run("download_submission_file", {"form_id": FORM, "submission_id": "777"}, fake)
    assert result["error_code"] == "setup_required" and "signing in" in result["error"]
    assert "API key" not in result["error"]


def test_a_submission_without_files_is_not_found() -> None:
    fake = FakeJotform(routes={f"GET /form/{FORM}/files": ok(FILES)})
    result = run("download_submission_file", {"form_id": FORM, "submission_id": "999"}, fake)
    assert result["error_code"] == "not_found"


# -- webhooks ----------------------------------------------------------------------------

HOOK = "https://hooks.example.com/jotform"


def test_list_form_webhooks_gives_ids_and_addresses() -> None:
    fake = FakeJotform(routes={f"GET /form/{FORM}/webhooks": ok({"0": "https://a", "1": HOOK})})
    out = run("list_form_webhooks", {"form_id": FORM}, fake)["result"]
    assert out["webhooks"] == [
        {"webhook_id": "0", "url": "https://a"},
        {"webhook_id": "1", "url": HOOK},
    ]


def test_add_webhook_if_new_sends_nothing_when_the_address_is_there() -> None:
    fake = FakeJotform(routes={f"GET /form/{FORM}/webhooks": ok({"0": HOOK})})
    result = run("add_webhook_if_new", {"form_id": FORM, "webhook_url": HOOK}, fake)
    out = result["result"]
    assert out["created"] is False and out["webhook_id"] == "0"
    assert result["definitely_no_external_effect"] is True
    assert result["external_effect_status"] == "failed"
    assert out["processing"] is None and out["applied"] is False


def test_add_webhook_if_new_adds_it_and_checks_once_more() -> None:
    fake = FakeJotform(
        routes={
            f"GET /form/{FORM}/webhooks": [
                ok({"0": "https://a"}),
                ok({"0": "https://a", "1": HOOK}),
            ],
            f"POST /form/{FORM}/webhooks": ok({"0": "https://a", "1": HOOK}),
        }
    )
    result = run("add_webhook_if_new", {"form_id": FORM, "webhook_url": HOOK}, fake)
    out = result["result"]
    assert out["created"] is True and out["webhook_id"] == "1"
    assert out["duplicate_detected"] is False and out["duplicate_ids"] == []
    assert fake.calls[1].form == [("webhookURL", HOOK)]


def test_a_parallel_run_that_added_the_same_address_is_reported() -> None:
    fake = FakeJotform(
        routes={
            f"GET /form/{FORM}/webhooks": [ok({}), ok({"0": HOOK, "1": HOOK})],
            f"POST /form/{FORM}/webhooks": ok({"0": HOOK}),
        }
    )
    out = run("add_webhook_if_new", {"form_id": FORM, "webhook_url": HOOK}, fake)["result"]
    assert out["duplicate_detected"] is True and out["duplicate_ids"] == ["0", "1"]


def test_an_address_there_twice_before_adding_is_a_conflict() -> None:
    fake = FakeJotform(routes={f"GET /form/{FORM}/webhooks": ok({"0": HOOK, "1": HOOK})})
    result = run("add_webhook_if_new", {"form_id": FORM, "webhook_url": HOOK}, fake)
    assert result["error_code"] == "conflict" and len(fake.calls) == 1


def test_a_webhook_list_in_another_form_makes_the_check_incomplete() -> None:
    fake = FakeJotform(routes={f"GET /form/{FORM}/webhooks": ok("odd")})
    result = run("add_webhook_if_new", {"form_id": FORM, "webhook_url": HOOK}, fake)
    assert result["error_code"] == "conflict" and len(fake.calls) == 1


def test_remove_webhook_by_address_deletes_its_id() -> None:
    fake = FakeJotform(
        routes={
            f"GET /form/{FORM}/webhooks": ok({"0": "https://a", "1": HOOK}),
            f"DELETE /form/{FORM}/webhooks/1": ok({"0": "https://a"}),
        }
    )
    result = run("remove_webhook", {"form_id": FORM, "webhook_url": HOOK}, fake)
    out = result["result"]
    assert out["removed"] is True and out["webhook_id"] == "1" and out["remaining"] == 1
    assert result["external_effect_status"] == "succeeded"


def test_remove_webhook_that_is_not_there_sends_nothing() -> None:
    fake = FakeJotform(routes={f"GET /form/{FORM}/webhooks": ok({"0": "https://a"})})
    result = run("remove_webhook", {"form_id": FORM, "webhook_id": "3"}, fake)
    assert result["result"]["removed"] is False and result["definitely_no_external_effect"] is True


def test_remove_webhook_needs_exactly_one_of_id_and_address() -> None:
    both = run("remove_webhook", {"form_id": FORM, "webhook_id": "1", "webhook_url": HOOK})
    none = run("remove_webhook", {"form_id": FORM})
    assert both["error_code"] == none["error_code"] == "invalid_payload"


def test_no_result_or_error_carries_the_key() -> None:
    echo = ok({"username": "ann", "note": f"key {API_KEY} and {API_KEY.upper()}"})
    fake = FakeJotform(routes={"GET /user": echo})
    result = run("get_account", {}, fake)
    assert result["ok"] is True and "[redacted]" in text_of(result)
    assert API_KEY not in text_of(result) and API_KEY.upper() not in text_of(result)
