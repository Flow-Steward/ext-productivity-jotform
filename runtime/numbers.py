"""Bounds of the numbers this extension writes out in full.

A JSON number such as ``1e1000000`` is short to send but a million digits once
written in plain notation, and an integer literal of more than 4,300 digits makes
Python's ``int`` refuse it. So every number is first read as ``Decimal`` and its
digits and exponent are checked through ``Decimal.as_tuple()``, never through the
length of its text:

- a number in a request with more than ``MAX_DIGITS`` digits or an exponent outside
  ``MIN_EXPONENT``…``MAX_EXPONENT`` is refused before anything is sent;
- such a number in the account's answer is kept as text in the notation the account
  wrote it in, never expanded, so a change the account confirmed is never lost to it.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

MAX_DIGITS = 40
MIN_EXPONENT = -30
MAX_EXPONENT = 30


def bounded(number: Decimal) -> bool:
    """True when ``number`` is finite and inside the digit and exponent bounds."""
    if not number.is_finite():
        return False
    shape = number.as_tuple()
    exponent = shape.exponent
    return (
        isinstance(exponent, int)
        and len(shape.digits) <= MAX_DIGITS
        and MIN_EXPONENT <= exponent <= MAX_EXPONENT
    )


def read(text: str, *, integer: bool) -> Decimal | int | None:
    """A JSON number literal as ``int`` (integer literal) or ``Decimal``; None when it is
    outside the bounds."""
    try:
        number = Decimal(text)
    except InvalidOperation:  # pragma: no cover - the JSON scanner only passes numbers
        return None
    if not bounded(number):
        return None
    return int(number) if integer else number


def plain(number: Decimal) -> str:
    """``number`` as text: plain notation inside the bounds, its own exponential notation
    outside them."""
    return format(number, "f") if bounded(number) else str(number)


__all__ = ["MAX_DIGITS", "MAX_EXPONENT", "MIN_EXPONENT", "bounded", "plain", "read"]
