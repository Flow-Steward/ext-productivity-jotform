"""Health command for the Jotform extension (no network)."""

from __future__ import annotations

import json


def check_health() -> dict[str, object]:
    from runtime.catalog import EFFECT_OPERATION_IDS, OPERATION_IDS
    from runtime.generic import REGISTRY_FILE
    from runtime.identity import EXTENSION_ID

    source = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))["source"]
    return {
        "extension_id": EXTENSION_ID,
        "ok": True,
        "status": "healthy",
        "specification_sha256": source["sha256"],
        "specification_downloaded": source["downloaded"],
        "declared_operations": len(OPERATION_IDS),
        "effect_operations": len(EFFECT_OPERATION_IDS),
    }


if __name__ == "__main__":
    print(json.dumps(check_health(), separators=(",", ":"), sort_keys=True))
