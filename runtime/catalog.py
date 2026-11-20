"""The closed list of this extension's steps: the generated ones (runtime/registry.json),
the everyday ones (runtime/composites.py) and the self-service ones (runtime/readiness.py)."""

from __future__ import annotations

from . import composites, readiness
from .generic import registry

_REGISTRY = registry()

GENERATED_IDS: frozenset[str] = frozenset(_REGISTRY)
COMPOSITE_IDS: frozenset[str] = frozenset(composites.COMPOSITES) | frozenset(readiness.HANDLERS)
OPERATION_IDS: frozenset[str] = GENERATED_IDS | COMPOSITE_IDS
#: Steps that change data: every documented operation that changes data (by its meaning,
#: not its method), and the everyday writes.
EFFECT_OPERATION_IDS: frozenset[str] = (
    frozenset(oid for oid, spec in _REGISTRY.items() if spec["kind"] == "write")
    | composites.COMPOSITE_WRITES
)
#: Steps that may save a workflow file: their requests keep the file's time in reserve.
FILE_OUTPUT_IDS: frozenset[str] = composites.FILE_OUTPUT_IDS | {"build_support_report"}

__all__ = [
    "COMPOSITE_IDS",
    "EFFECT_OPERATION_IDS",
    "FILE_OUTPUT_IDS",
    "GENERATED_IDS",
    "OPERATION_IDS",
]
