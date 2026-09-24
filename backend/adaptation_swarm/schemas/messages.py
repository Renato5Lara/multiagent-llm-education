"""Contrato de mensajes AG0↔AG1..AG4 (`swarm-msg-v1`), compatible con FIPA-ACL
(asesoría §Glosario MAS: "mensajes estructurados FIPA-ACL o JSON-RPC").

Campos FIPA-ACL usados: `performative`, `sender`, `receiver`, `conversation-id`
(= `correlation_id`), `in-reply-to`, `content` (= `payload`).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from adaptation_swarm.schemas.ids import new_id

SCHEMA_VERSION = "swarm-msg-v1"
_LOG_DROP_KEYS = frozenset({"code", "mermaid", "text", "source", "profile", "heuristic_start"})


class AgentId(str, Enum):
    AG0 = "AG0"  # Swarm-Orchestrator
    AG1 = "AG1"  # Profil-Agent
    AG2 = "AG2"  # Code-Agent
    AG3 = "AG3"  # Diagram-Agent
    AG4 = "AG4"  # Text-Agent


class MessageType(str, Enum):
    PROFILE_REQUEST = "PROFILE_REQUEST"      # AG0 → AG1
    W_READY = "W_READY"                      # AG1 → AG0
    CODE_REQUEST = "CODE_REQUEST"            # AG0 → AG2
    CODE_READY = "CODE_READY"                # AG2 → AG0
    DIAGRAM_REQUEST = "DIAGRAM_REQUEST"      # AG0 → AG3
    DIAGRAM_READY = "DIAGRAM_READY"          # AG3 → AG0
    TEXT_REQUEST = "TEXT_REQUEST"            # AG0 → AG4 (texto + audio)
    TEXT_READY = "TEXT_READY"                # AG4 → AG0
    AUDIO_READY = "AUDIO_READY"              # AG4 → AG0
    GBEST_BROADCAST = "GBEST_BROADCAST"      # AG0 → AG1..AG4 (retroalimenta con g_best)
    ERROR = "ERROR"                          # cualquiera → AG0


class Performative(str, Enum):
    REQUEST = "request"
    INFORM = "inform"
    FAILURE = "failure"


_PERFORMATIVE_BY_TYPE: dict[MessageType, Performative] = {
    MessageType.PROFILE_REQUEST: Performative.REQUEST,
    MessageType.CODE_REQUEST: Performative.REQUEST,
    MessageType.DIAGRAM_REQUEST: Performative.REQUEST,
    MessageType.TEXT_REQUEST: Performative.REQUEST,
    MessageType.W_READY: Performative.INFORM,
    MessageType.CODE_READY: Performative.INFORM,
    MessageType.DIAGRAM_READY: Performative.INFORM,
    MessageType.TEXT_READY: Performative.INFORM,
    MessageType.AUDIO_READY: Performative.INFORM,
    MessageType.GBEST_BROADCAST: Performative.INFORM,
    MessageType.ERROR: Performative.FAILURE,
}

# Emisor/receptor permitidos por tipo (contrato de topología del enjambre).
_ALLOWED_ROUTES: dict[MessageType, tuple[AgentId, AgentId | None]] = {
    MessageType.PROFILE_REQUEST: (AgentId.AG0, AgentId.AG1),
    MessageType.W_READY: (AgentId.AG1, AgentId.AG0),
    MessageType.CODE_REQUEST: (AgentId.AG0, AgentId.AG2),
    MessageType.CODE_READY: (AgentId.AG2, AgentId.AG0),
    MessageType.DIAGRAM_REQUEST: (AgentId.AG0, AgentId.AG3),
    MessageType.DIAGRAM_READY: (AgentId.AG3, AgentId.AG0),
    MessageType.TEXT_REQUEST: (AgentId.AG0, AgentId.AG4),
    MessageType.TEXT_READY: (AgentId.AG4, AgentId.AG0),
    MessageType.AUDIO_READY: (AgentId.AG4, AgentId.AG0),
    MessageType.GBEST_BROADCAST: (AgentId.AG0, None),
}


class BusMessage(BaseModel):
    message_id: str = Field(default_factory=new_id)
    correlation_id: str
    cycle_id: str
    sender: AgentId
    receiver: AgentId
    message_type: MessageType
    performative: Performative | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    t_wall_ns: int = Field(default_factory=time.time_ns)
    iteration: int | None = None
    request_key: str | None = None          # identifica la petición dentro del ciclo (p. ej. variante)
    in_reply_to: str | None = None
    instance: str | None = None            # instancia de AG0 que debe recibir las respuestas (despliegue multiproceso)
    payload: dict[str, Any] = Field(default_factory=dict)
    timing: dict[str, Any] = Field(default_factory=dict)  # t_recv/t_done del handler (evidencia RF03)
    status: str = "ok"
    error: dict[str, str] | None = None
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def _check_contract(self) -> "BusMessage":
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"schema_version {self.schema_version!r} != {SCHEMA_VERSION!r}")
        if self.performative is None:
            self.performative = _PERFORMATIVE_BY_TYPE[self.message_type]
        if self.message_type is MessageType.ERROR:
            if self.receiver is not AgentId.AG0:
                raise ValueError("ERROR siempre se dirige a AG0")
            if self.error is None:
                raise ValueError("ERROR requiere el campo `error`")
            return self
        sender, receiver = _ALLOWED_ROUTES[self.message_type]
        if self.sender is not sender:
            raise ValueError(f"{self.message_type.value} debe emitirlo {sender.value}, no {self.sender.value}")
        if receiver is not None and self.receiver is not receiver:
            raise ValueError(f"{self.message_type.value} debe dirigirse a {receiver.value}")
        return self

    def to_json(self) -> str:
        return self.model_dump_json()

    def to_log_json(self) -> str:
        """Versión para el LOG de auditoría: sin el contenido pesado (código, diagrama, texto, perfil). El
        contenido vive en la biblioteca por hash (`content_id`/`sha256`); así el log no infla la memoria de Redis."""
        slim = self.model_copy(update={"payload": {k: v for k, v in self.payload.items() if k not in _LOG_DROP_KEYS}})
        return slim.model_dump_json()

    @classmethod
    def from_json(cls, raw: str) -> "BusMessage":
        return cls.model_validate_json(raw)
