"""How deeply a JSON text nests, counted before it is parsed.

Python's JSON reader and every recursive walk after it (scrubbing the token, writing
numbers out, the host's own checks) recurse once per level, so a short text such as
``[[[[...]]]]`` a few thousand levels deep ends in ``RecursionError``. The depth is
therefore counted on the raw text first, outside strings, and a text deeper than its
limit is never handed to ``json.loads``:

- a request deeper than ``MAX_REQUEST_DEPTH`` is refused (``main.py``);
- an answer of the account deeper than ``MAX_ANSWER_DEPTH`` is not read
  (``runtime/transport.py``).

The host refuses an output nested deeper than 64 levels (core ``secret_reflection``),
and a step wraps the account's answer in a few levels of its own, so 48 leaves room.
"""

from __future__ import annotations

import re

MAX_REQUEST_DEPTH = 32
MAX_ANSWER_DEPTH = 48

#: A JSON string: its brackets do not nest anything.
_STRING = re.compile(rb'"(?:[^"\\]|\\.)*"', re.DOTALL)
_NOT_BRACKETS = bytes(b for b in range(256) if b not in b"[]{}")


def nesting(raw: bytes | str, limit: int) -> int:
    """The deepest bracket level of ``raw`` outside strings; it stops counting once the
    level passes ``limit`` and returns that level."""
    data = raw.encode("utf-8", "surrogatepass") if isinstance(raw, str) else raw
    brackets = _STRING.sub(b"", data).translate(None, _NOT_BRACKETS)
    level = deepest = 0
    for byte in brackets:
        if byte in (0x5B, 0x7B):  # [ {
            level += 1
            if level > deepest:
                deepest = level
                if deepest > limit:
                    return deepest
        else:
            level -= 1
    return deepest


def too_deep(raw: bytes | str, limit: int) -> bool:
    return nesting(raw, limit) > limit


__all__ = ["MAX_ANSWER_DEPTH", "MAX_REQUEST_DEPTH", "nesting", "too_deep"]
