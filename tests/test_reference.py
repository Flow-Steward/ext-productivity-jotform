"""The pinned facts are what the pinned documentation says."""

from __future__ import annotations

import hashlib
import json
import re
import sys

import pytest
from support import BUNDLE

sys.path.insert(0, str(BUNDLE / "tests" / "reference"))

import build_contracts  # noqa: E402
import extract_reference  # noqa: E402

PAGE = BUNDLE / "tests" / "reference" / "sources" / "jotform_api_docs.html"
PAGE_SHA256 = "8b457afc3e3ef6590ec934791e8189f6dd8a9c7c75860b114137f247a07cc895"


def test_the_facts_are_extracted_from_the_pinned_operation_list() -> None:
    assert extract_reference.extract(extract_reference.SOURCE.read_bytes()) == json.loads(
        extract_reference.OUTPUT.read_text(encoding="utf-8")
    )


def test_a_changed_operation_list_is_refused() -> None:
    with pytest.raises(SystemExit, match="the specification changed"):
        extract_reference.extract(b"var requestModels = [];")


def test_the_reader_reads_data_and_never_runs_it() -> None:
    reader = extract_reference.Reader(
        extract_reference.tokens('var a = "x"; var b = {k: a, v: (f() ? 1 : 2), w: [1, true]};')
    )
    reader.statements()
    assert reader.names["b"] == {"k": {"$ref": "a"}, "v": None, "w": [1, True]}


def test_the_pins_are_the_downloaded_ones() -> None:
    source = build_contracts.facts()["source"]
    assert source["sha256"] == extract_reference.SHA256
    assert hashlib.sha256(extract_reference.SOURCE.read_bytes()).hexdigest() == source["sha256"]
    assert source["bytes"] == extract_reference.BYTES == 80910
    assert source["downloaded"] == "2026-11-20"
    assert source["url"].endswith("/js/apidocs/v1/request-models.js")
    assert source["page"] == "https://api.jotform.com/docs/"
    client = extract_reference.CLIENT.read_bytes()
    assert hashlib.sha256(client).hexdigest() == source["client"]["sha256"]


def test_the_documentation_client_sends_parameters_by_kind_and_checks_response_code() -> None:
    """MethodSectionView.js: query in the query string, post as form fields, url in the
    path, JSON as the raw body; success only when the body's responseCode is 200."""
    client = extract_reference.CLIENT.read_text(encoding="utf-8")
    assert """data-inputType")==='query'""" in client
    assert "queryParameters[name] = val" in client
    assert """data-inputType")==='post'""" in client and "data[name] = val" in client
    assert "url = url.replace(r, val)" in client
    assert """data-inputType")==='JSON'""" in client and "data = $(el).val()" in client
    assert "if(r.responseCode == 200)" in client


def test_every_operation_documents_its_refusals_and_the_list_has_nothing_hidden() -> None:
    data = build_contracts.facts()
    assert data["defined_not_listed"] == []
    assert data["commented_out"] == ["userApps", "userInvoices", "userKeys", "userRewards"]
    for op in data["operations"]:
        codes = {s["code"] for s in op["status_codes"]}
        if (op["method"], op["path"]) == ("DELETE", "/folder/{id}"):
            assert codes == set()
        else:
            assert codes in ({404}, {400}), op["path"]


@pytest.mark.skipif(not PAGE.exists(), reason="the documentation page is not committed")
def test_the_documentation_page_gives_the_regions_the_key_header_and_the_answer_form() -> None:
    raw = PAGE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PAGE_SHA256
    text = raw.decode("utf-8")
    assert "js/apidocs/v1/request-models.js" in text
    for host in (
        "https://api.jotform.com",
        "https://eu-api.jotform.com",
        "https://hipaa-api.jotform.com",
    ):
        assert host in text
    assert 'curl -H "APIKEY: {myApiKey}"' in text
    assert "1000 requests per day for the <b>starter</b> plan" in text
    samples = re.findall(r'"responseCode":\s*(\d+)', text)
    assert samples and set(samples) == {"200"}
    assert text.count("limit-left") >= 40
