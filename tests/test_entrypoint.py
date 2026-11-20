"""main.py and health.py as the host runs them: a subprocess, JSON in and out."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from support import API_KEY, BUNDLE, payload

import main


def invoke(request: Any) -> tuple[int, dict[str, Any]]:
    proc = subprocess.run(
        [sys.executable, "main.py"],
        cwd=BUNDLE,
        input=json.dumps(request) if not isinstance(request, bytes) else request.decode(),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return proc.returncode, json.loads(proc.stdout)


def test_a_test_mode_write_answers_without_network() -> None:
    request = payload(
        "add_webhook_if_new",
        {"form_id": "1", "webhook_url": "https://hooks.example.com/a"},
        test_mode=True,
    )
    code, response = invoke(request)
    assert code == 0, response
    assert response["definitely_no_external_effect"] is True
    assert response["external_effect_status"] == "failed"
    assert API_KEY not in json.dumps(response)


def test_an_unknown_operation_is_refused() -> None:
    code, response = invoke(payload("drop_everything"))
    assert code == 2
    assert response["error_code"] == "unsupported_operation"
    assert response["result"] == {"warnings": []}


def test_a_request_that_is_not_json_is_refused() -> None:
    code, response = invoke(b"{not json")
    assert code == 2
    assert response["error_code"] == "invalid_payload"
    assert response["result"] == {"warnings": []} and response["warnings"] == []


def test_the_last_resort_answer_keeps_the_facts_of_a_write() -> None:
    huge = {
        "ok": True,
        "result": {"id": "1", "blob": "x" * 6_000_000},
        "external_effect_status": "succeeded",
        "definitely_no_external_effect": False,
    }
    final, _ = main._bounded_serialized_response(huge)
    assert final["ok"] is True and final["error_code"] is None
    assert final["external_effect_status"] == "succeeded"
    assert final["result"]["id"] == "1" and "blob" not in final["result"]


def test_health_answers_without_network() -> None:
    proc = subprocess.run(
        [sys.executable, "health.py"], cwd=BUNDLE, capture_output=True, text=True, check=True
    )
    report = json.loads(proc.stdout)
    assert report["ok"] is True
    assert report["extension_id"] == "com.brizzl.jotform"
    assert report["declared_operations"] == 64 and report["effect_operations"] == 31
