"""Keep one step's result inside what the host accepts.

The host scans every string of an extension response for reflected secrets and
fails closed past fixed budgets (core ``secret_reflection``: 3 Mi traversed nodes,
nesting deeper than 64 levels, 64 Mi compared code points of distinct strings),
refuses an output above 5 MiB (core ``remote_runtime_protocol_v2``), and ``main.py``
caps the serialized response at 4.5 MiB. This module measures a result as it will be
written: every ``Decimal`` as the plain text ``results.plain`` makes of it (a string
the host scans), every text after the API key was scrubbed from the answer. Its limits
(3,500,000 serialized bytes, 2,000,000 nodes, 48 levels) are inside the host's, with a
margin for the envelope; the number of rows is not limited.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, NamedTuple

from . import errors, numbers
from .errors import ExtensionError

#: The serialized result: the limit that decides in practice (main.py caps the whole
#: response at 4.5 MiB, the host takes 5 MiB).
MAX_SERIALIZED_BYTES = 3_500_000
#: Nodes (values and dict keys), well inside the host's 3 Mi.
MAX_NODES = 2_000_000
#: Nesting of the result, well inside the host's 64 (the envelope adds a few levels).
MAX_DEPTH = 48


class Totals(NamedTuple):
    """What ``measure`` counts of a result as it will be written."""

    strings: int
    nodes: int
    codepoints: int
    size: int
    depth: int


def measure(value: Any) -> Totals:
    """Strings, nodes, string code points, serialized bytes and nesting depth of ``value``
    as it is written out: a ``Decimal`` counts as the text ``numbers.plain`` writes.

    There is no limit on the number of strings or rows: the host's own scan has none;
    the serialized size, the nodes and the depth are what is checked."""
    strings = nodes = codepoints = deepest = 0
    stack: list[tuple[Any, int]] = [(value, 0)]
    while stack:
        node, level = stack.pop()
        nodes += 1
        if isinstance(node, Decimal):
            node = numbers.plain(node)
        if isinstance(node, str):
            strings += 1
            codepoints += len(node)
        elif isinstance(node, dict):
            level += 1
            deepest = max(deepest, level)
            for key, nested in node.items():
                nodes += 1
                if isinstance(key, str):
                    strings += 1
                    codepoints += len(key)
                stack.append((nested, level))
        elif isinstance(node, (list, tuple)):
            level += 1
            deepest = max(deepest, level)
            stack.extend((item, level) for item in node)
    size = len(
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=_written).encode(
            "utf-8"
        )
    )
    return Totals(strings, nodes, codepoints, size, deepest)


def _written(item: Any) -> Any:
    if isinstance(item, Decimal):
        return numbers.plain(item)
    return str(item)


def _within(totals: Totals) -> bool:
    return (
        totals.size <= MAX_SERIALIZED_BYTES
        and totals.nodes <= MAX_NODES
        and totals.depth <= MAX_DEPTH
    )


def too_large() -> ExtensionError:
    return ExtensionError(
        errors.RESPONSE_TOO_LARGE,
        "This result is too large for one step output. Narrow it with the step's "
        "filters or read fewer records per page.",
        definitely_no_external_effect=True,
        external_effect_status="failed",
    )


def fits(result: Any) -> bool:
    return _within(measure(result))


def ensure_fits(result: Any) -> None:
    if not fits(result):
        raise too_large()


__all__ = ["ensure_fits", "fits", "measure", "too_large"]
