"""The generated contracts match their sources; forms, inputs and the runtime agree; the
extension's standing rules (ids, names, outputs, UI, icon, version, identity) hold."""

from __future__ import annotations

import collections
import hashlib
import json
import re
import struct
import sys
from typing import Any

import pytest
import yaml
from support import BUNDLE

sys.path.insert(0, str(BUNDLE / "tests" / "reference"))

import build_contracts  # noqa: E402
import composite_specs  # noqa: E402
import names  # noqa: E402

from runtime import catalog, composites, generic, identity, limits, readiness  # noqa: E402

OUTPUTS = build_contracts.outputs()
SHA = "ded079d796ecde08f097af8845a409d6afdd8af3f4ad6023f3827af01c51b0a3"
FACTS = build_contracts.facts()
EVERYDAY = [c["operation_id"] for c in composite_specs.COMPOSITES]


def load(path: str) -> Any:
    return yaml.safe_load((BUNDLE / path).read_text(encoding="utf-8"))


def operations() -> list[dict[str, Any]]:
    return load("contracts/operation_manifest.yaml")["operations"]


@pytest.mark.parametrize("path", sorted(OUTPUTS))
def test_generated_files_are_current(path: str) -> None:
    assert (BUNDLE / path).read_text(encoding="utf-8") == build_contracts.render(
        path, OUTPUTS[path]
    ), f"{path} drifted: run python3 tests/reference/build_contracts.py"


def test_every_documented_operation_but_the_four_left_out_is_a_step() -> None:
    assert FACTS["source"]["sha256"] == SHA
    documented = {(o["method"], o["path"]) for o in FACTS["operations"]}
    assert len(documented) == len(FACTS["operations"]) == 56
    assert collections.Counter(m for m, _ in documented) == {
        "GET": 26,
        "POST": 14,
        "PUT": 9,
        "DELETE": 7,
    }
    assert set(names.EXCLUDED) == {
        ("POST", "/user/login"),
        ("GET", "/user/logout"),
        ("GET", "/user/labels"),
        ("POST", "/folder"),
    }
    registry = generic.registry()
    assert len(registry) == 52
    assert {(e["method"], e["path"]) for e in registry.values()} == documented - set(names.EXCLUDED)
    assert set(names.TITLES) == documented - set(names.EXCLUDED)
    manifest = [o["operation_id"] for o in operations()]
    assert manifest[: len(EVERYDAY)] == EVERYDAY
    assert sorted(manifest[len(EVERYDAY) :]) == sorted(registry) and len(manifest) == 64
    assert set(manifest) == set(catalog.OPERATION_IDS)


def test_the_operations_left_out_contradict_themselves_or_sign_in() -> None:
    by_key = {(o["method"], o["path"]): o for o in FACTS["operations"]}
    for where in (("GET", "/user/labels"), ("POST", "/folder")):
        op = by_key[where]
        url_params = [p for p in op["parameters"] if p["parameter_type"] == "url"]
        assert url_params and all(p["replace"] not in op["path"] for p in url_params)
        assert any(p["required"] for p in url_params)
    assert {p["name"] for p in by_key[("POST", "/user/login")]["parameters"]} >= {
        "username",
        "password",
    }


def test_step_ids_are_frozen_unique_and_never_documentation_ids() -> None:
    ids = json.loads((BUNDLE / "tests/reference/step_ids.json").read_text())
    assert set(ids) == {f"{m} {p}" for m, p in names.TITLES}
    values = list(ids.values()) + EVERYDAY
    assert len(values) == len(set(values))
    assert all(re.fullmatch(r"[a-z][a-z0-9_]{2,80}", v) for v in values)
    assert set(generic.registry()) == set(ids.values())
    documented = {o["doc_id"] for o in FACTS["operations"]}
    assert not documented & set(values)


def test_titles_are_verb_first_unique_and_not_noun_lists() -> None:
    titles = [o["display_name"] for o in operations()]
    assert len(titles) == len(set(titles))
    for title in titles:
        assert title.split()[0] in names.VERBS, title
        assert "·" not in title and not title.startswith(("Advanced", "List ·"))


def test_everyday_steps_come_first_and_deletions_close_each_area() -> None:
    ids = [o["operation_id"] for o in operations()]
    assert ids[: len(EVERYDAY)] == EVERYDAY
    registry = generic.registry()
    by_area: dict[str, list[str]] = collections.defaultdict(list)
    for oid in ids[len(EVERYDAY) :]:
        by_area[registry[oid]["area"]].append(registry[oid]["method"])
    assert list(by_area) == list(names.AREAS)
    for area, methods in by_area.items():
        first_delete = methods.index("DELETE") if "DELETE" in methods else len(methods)
        assert set(methods[first_delete:]) <= {"DELETE"}, area


def test_every_step_has_a_warnings_output_and_writes_their_effect_facts() -> None:
    effects = load("extension.yaml")["external_effects"]
    effect_ids = {e["operation_id"] for e in effects}
    for op in operations():
        names_out = [o["name"] for o in op["outputs"]]
        assert "warnings" in names_out, op["operation_id"]
        write = op["operation_kind"] == "action"
        assert write == (op["operation_id"] in effect_ids)
        assert write == (op["operation_id"] in catalog.EFFECT_OPERATION_IDS)
        if write:
            assert {"external_effect_status", "definitely_no_external_effect"} <= set(names_out)
            assert {"processing", "applied", "check"} <= set(names_out)
            assert "timeout_unknown" in op["error_codes"]
        else:
            assert not {"processing", "applied", "check"} & set(names_out)
        assert "setup_required" in op["error_codes"]
    generated_writes = {k for k, v in generic.registry().items() if v["method"] != "GET"}
    assert generated_writes | composites.COMPOSITE_WRITES == effect_ids
    assert len(effect_ids) == 28 + 3
    assert all(
        e["idempotency"] == "required" and e["test_mode_behavior"] == "suppress" for e in effects
    )


def test_reads_and_writes_follow_the_meaning_and_the_documented_lists() -> None:
    """No non-GET read and no GET write among the steps; no write is accepted for later."""
    assert build_contracts.READ_ONLY_NON_GET == {}
    assert build_contracts.WRITING_GET == {}
    assert build_contracts.ACCEPTED_ONLY == {}
    for entry in generic.registry().values():
        assert entry["kind"] == ("read" if entry["method"] == "GET" else "write")
        assert entry["success"] == ["200"]
        if entry["kind"] == "write":
            assert entry["processing"] == {"accepted_always": False, "check": None}
    batch = [k for k, e in generic.registry().items() if e.get("step_class") == "confirm_batch"]
    assert batch == ["add_submissions_to_form"]


def test_forms_inputs_and_runtime_agree() -> None:
    forms = {f["operation_id"]: f for f in load("contracts/step_ui_manifest.yaml")["forms"]}
    actions = {a["action_id"]: a for a in load("ui/actions/actions.yaml")["actions"]}
    registry = generic.registry()
    specs = {c["operation_id"]: c for c in composite_specs.COMPOSITES}
    for op in operations():
        oid = op["operation_id"]
        inputs = [i["name"] for i in op["inputs"] if i["name"] != "connection_ref"]
        assert [f["name"] for f in forms[oid]["fields"]] == inputs, oid
        assert [p["name"] for p in actions[oid]["parameters"]] == ["connection_ref", *inputs]
        if oid in registry:
            assert set(inputs) == generic.inputs_of(registry[oid]), oid
        else:
            assert inputs == [i["name"] for i in specs[oid]["inputs"]]
            assert composite_specs.REQUIRED.get(oid, frozenset()) <= set(inputs)


def test_the_test_run_outputs_of_the_everyday_writes_are_their_declared_outputs() -> None:
    from runtime.operations import TEST_RUN_OUTPUTS

    for spec in composite_specs.COMPOSITES:
        if spec["kind"] != "write":
            continue
        declared = [o["name"] for o in spec["outputs"] if o["name"] != "warnings"]
        assert list(TEST_RUN_OUTPUTS[spec["operation_id"]]) == declared, spec["operation_id"]
    assert set(TEST_RUN_OUTPUTS) == set(composites.COMPOSITE_WRITES) == set(composites.VALIDATORS)


def test_the_connection_type_is_an_api_key_and_a_documented_region() -> None:
    types = load("contracts/connection_types.yaml")["connection_types"]
    assert [t["connection_type_id"] for t in types] == ["jotform"]
    row = types[0]
    assert row["auth"] == {"type": "static_secret"}
    assert row["config_schema"]["properties"]["region"]["enum"] == ["standard", "eu", "hipaa"]
    assert set(row["secret_schema"]["properties"]) == {"api_key"}
    manifest = load("extension.yaml")
    assert "oauth_providers" not in manifest["runtime"]["extension_contract_v2"]
    assert "callbacks" not in manifest


def test_the_runtime_reaches_only_jotform_addresses() -> None:
    from runtime import connection

    hosts = {host for _, host in connection.REGIONS.values()}
    assert hosts == {"api.jotform.com", "eu-api.jotform.com", "hipaa-api.jotform.com"}
    egress = load("extension.yaml")["egress"]["hosts"]
    assert egress == [
        "api.jotform.com",
        "eu-api.jotform.com",
        "hipaa-api.jotform.com",
        "*.jotform.com",
    ]
    found = set()
    for path in (BUNDLE / "runtime").glob("*.py"):
        found |= set(re.findall(r"https://([a-z0-9.-]+)", path.read_text(encoding="utf-8")))
    # example.com only in the example of an error message.
    assert found - {"example.com"} <= hosts | {"github.com", "www.jotform.com"}


def _pages() -> list[tuple[str, str]]:
    manifest = load("ui/ui_manifest.yaml")
    out = []
    for ref in manifest["pages"]:
        page = load("ui/" + ref["ref"])
        for comp in page.get("components", []):
            out.append((page["page_id"], str(comp.get("body") or comp.get("content") or "")))
    return out


def test_ui_pages_have_no_tables_and_no_forbidden_words() -> None:
    files = {p.name for p in (BUNDLE / "ui" / "pages").glob("*.yaml")}
    assert files == {ref["ref"].split("/")[-1] for ref in load("ui/ui_manifest.yaml")["pages"]}
    for page_id, body in _pages():
        for line in body.splitlines():
            assert not line.strip().startswith("|"), (page_id, line)
        lowered = body.lower()
        for word in (
            "not verified",
            "unverified",
            "не проверено",
            "limits",
            "partner",
            "certified",
            "official",
        ):
            assert word not in lowered, (page_id, word)
    readme = (BUNDLE / "README.md").read_text(encoding="utf-8").lower()
    for word in ("partner", "certified", "official", "todo", "not yet", "coming soon"):
        assert word not in readme, word


def test_the_icon_is_a_square_png_and_branding_records_its_hash() -> None:
    data = (BUNDLE / "icon.png").read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    width, height = struct.unpack(">II", data[16:24])
    assert width == height and 32 <= width <= 512
    branding = (BUNDLE / "BRANDING.md").read_text(encoding="utf-8")
    assert hashlib.sha256(data).hexdigest() in branding
    assert "cdn.jotfor.ms/assets/img/favicons/apple-touch-icon-180x180.png" in branding


def test_version_step_limit_and_changelog() -> None:
    manifest = load("extension.yaml")
    assert manifest["version"] == identity.VERSION == "0.1.0"
    assert manifest["entrypoint"]["timeout_seconds"] == 600 == limits.STEP_TIMEOUT_SECONDS
    changelog = (BUNDLE / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## 0.1.0" in changelog and SHA in changelog
    page = json.dumps(load("ui/pages/changelog.yaml"), ensure_ascii=False)
    assert "0.1.0" in page and SHA in page
    total = len(generic.registry())
    for text in (changelog, page, (BUNDLE / "README.md").read_text(encoding="utf-8")):
        assert f"{total} operations" in text


def test_the_id_prefix_and_repository_are_written_in_few_places() -> None:
    """The provisional id and repository: identity.py, and the files people read."""
    expected = {"runtime/identity.py", "extension.yaml", "README.md", "ui/pages/support.yaml"}
    found = set()
    for path in BUNDLE.rglob("*"):
        if not path.is_file() or any(
            p in path.parts for p in (".git", "sources", "__pycache__", "dev-wheels", ".github")
        ):
            continue
        if path.suffix not in {".py", ".yaml", ".md", ".json", ".toml", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "com.brizzl" in text or "github.com/Brizzl-extensions" in text:
            found.add(str(path.relative_to(BUNDLE)))
    assert found <= expected | {"tests/test_contracts.py", "tests/test_entrypoint.py"}, found
    assert "flowsteward." not in load("extension.yaml")["extension_id"]


def test_readiness_names_every_everyday_step_with_its_title() -> None:
    specs = {c["operation_id"]: c["title"] for c in composite_specs.COMPOSITES}
    for oid, (title, _) in readiness.STEPS.items():
        assert specs[oid] == title
    writes = {oid for oid, (_, w) in readiness.STEPS.items() if w}
    assert writes == set(composites.COMPOSITE_WRITES)
