"""One invocation's ports: its input, its transport and the artifact plane."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from .connection import Connection
from .transport import JotformTransport

TransportFactory = Callable[[Connection], JotformTransport]
ArtifactWriter = Callable[..., Mapping[str, Any]]


class Context:
    """One invocation: its input, its connection's transport and the artifact plane."""

    def __init__(
        self,
        *,
        payload: Mapping[str, Any],
        operation_input: Mapping[str, Any],
        transport: JotformTransport,
        artifact_writer: ArtifactWriter,
    ) -> None:
        self.payload = payload
        self.operation_input = operation_input
        self.transport = transport
        self.artifact_writer = artifact_writer
        #: What one invocation read once and uses again (field lists, pipelines).
        self.cache: dict[str, Any] = {}

    @property
    def connection(self) -> Connection:
        return self.transport.connection
