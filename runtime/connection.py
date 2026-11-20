"""Project-scoped connection: one Jotform account's API key and the API address it uses.

The Jotform API documentation (https://api.jotform.com/docs/, "API Endpoints") names
three addresses: the standard one ``https://api.jotform.com``, ``https://eu-api.jotform.com``
for EU accounts and ``https://hipaa-api.jotform.com`` for HIPAA accounts. The connection
chooses one of them by name (``region``); it is never a free URL, so no request can go
anywhere else.

The documentation ("Authentication") sends the API key either as the ``apiKey`` query
parameter or as the ``APIKEY`` HTTP header. This extension sends it only in the header,
so it never appears in an address. The documentation states no lifetime for a key: it
works until it is deleted in My Account → API, and there is nothing to refresh.

The key lives in a private field of a frozen dataclass whose ``repr`` never shows it;
it is never placed in a result, a log line or an exception message.
"""

from __future__ import annotations

import html
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote, quote_plus

from . import errors
from .errors import ExtensionError

CONNECTION_TYPE = "jotform"
#: Region -> (name shown to people, API host).
REGIONS: dict[str, tuple[str, str]] = {
    "standard": ("Standard", "api.jotform.com"),
    "eu": ("EU", "eu-api.jotform.com"),
    "hipaa": ("HIPAA", "hipaa-api.jotform.com"),
}
DEFAULT_REGION = "standard"
CONFIG_FIELDS: frozenset[str] = frozenset({"label", "region"})
#: Keys the host may add to a connection's settings that this extension does not use.
HOST_CONFIG_FIELDS: frozenset[str] = frozenset({"oauth"})
SECRET_FIELDS: frozenset[str] = frozenset({"api_key"})
#: Shorter keys could not be removed from answers without mangling them.
MIN_KEY_LENGTH = 16
MAX_KEY_LENGTH = 256
#: Letters and digits: the keys My Account → API shows.
_KEY_RE = re.compile(r"^[A-Za-z0-9]+$")


@dataclass(frozen=True)
class Connection:
    """One validated Jotform connection."""

    connection_id: str
    region: str
    _api_key: str = field(repr=False)
    #: The key's forms, computed on first use (``secret_forms``).
    _forms: tuple[str, ...] = field(default=(), init=False, repr=False, compare=False)

    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    def connection_type(self) -> str:
        return CONNECTION_TYPE

    @property
    def environment(self) -> str:
        return REGIONS[self.region][0]

    @property
    def host(self) -> str:
        return REGIONS[self.region][1]

    @property
    def base_url(self) -> str:
        return "https://" + self.host

    def secret_forms(self) -> tuple[str, ...]:
        """Every way the key can appear in a text, as is and encoded; computed once per
        connection, not once per text of an answer."""
        if not self._forms:
            object.__setattr__(self, "_forms", _secret_forms(self._api_key))
        return self._forms

    def __repr__(self) -> str:  # pragma: no cover - defensive
        return f"Connection(connection_id={self.connection_id!r})"

    __str__ = __repr__


def _secret_forms(key: str) -> tuple[str, ...]:
    """Every way ``key`` can appear in a text: as is and encoded, any letter case."""
    forms = {
        key,
        key.lower(),
        key.upper(),
        quote_plus(key, safe=""),
        quote(key, safe=""),
        json.dumps(key, ensure_ascii=False)[1:-1],
        html.escape(key, quote=True),
    }
    # Longest first, so a form that contains another is removed whole.
    return tuple(sorted((f for f in forms if f), key=len, reverse=True))


def _setup(message: str) -> ExtensionError:
    return errors.setup(message)


def region_of(value: Any) -> str:
    if value in (None, ""):
        return DEFAULT_REGION
    if not isinstance(value, str) or value.strip().lower() not in REGIONS:
        raise _setup("The region is not usable: choose standard, eu or hipaa in the connection")
    return value.strip().lower()


def _key(value: Any) -> str:
    text = value.strip() if isinstance(value, str) else ""
    if not text:
        raise _setup(
            "Add the Jotform API key to this connection: My Account → API → Create New Key"
        )
    if len(text) < MIN_KEY_LENGTH or len(text) > MAX_KEY_LENGTH or not _KEY_RE.fullmatch(text):
        raise _setup(
            "The API key is not usable: copy the whole key My Account → API shows, without spaces"
        )
    return text


def connection_from_payload(payload: Mapping[str, Any], *, connection_ref: str) -> Connection:
    """Validate the selected project connection before any outbound request."""
    action = payload.get("action")
    target = action.get("target") if isinstance(action, Mapping) else None
    connection = target.get("connection") if isinstance(target, Mapping) else None
    if not isinstance(connection, Mapping):
        raise errors.no_effect(errors.INVALID_CONNECTION, "The selected connection is unavailable")
    connection_id = str(connection.get("connection_id") or "")
    if not connection_id or (connection_ref and connection_id != connection_ref):
        raise errors.no_effect(
            errors.INVALID_CONNECTION, "The selected connection does not match connection_ref"
        )
    connection_type = str(
        connection.get("connection_type_id") or connection.get("connection_type") or ""
    )
    if connection_type != CONNECTION_TYPE:
        raise errors.no_effect(
            errors.INVALID_CONNECTION, "The selected connection is not a Jotform connection"
        )
    config = connection.get("config")
    config = config if isinstance(config, Mapping) else {}
    if set(config) - CONFIG_FIELDS - HOST_CONFIG_FIELDS:
        raise errors.no_effect(
            errors.INVALID_CONNECTION, "The connection carries unsupported settings"
        )
    secrets = connection.get("secrets")
    secrets = secrets if isinstance(secrets, Mapping) else {}
    if set(secrets) - SECRET_FIELDS:
        raise errors.no_effect(
            errors.INVALID_CONNECTION, "The connection carries unsupported secrets"
        )
    return Connection(
        connection_id=connection_id,
        region=region_of(config.get("region")),
        _api_key=_key(secrets.get("api_key")),
    )


__all__ = [
    "CONFIG_FIELDS",
    "CONNECTION_TYPE",
    "DEFAULT_REGION",
    "REGIONS",
    "SECRET_FIELDS",
    "Connection",
    "connection_from_payload",
    "region_of",
]
