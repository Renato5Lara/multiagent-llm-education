"""Clase base de los agentes AG1–AG4: bucle consumidor sobre el bus REAL de Redis,
idempotencia por `message_id`, errores explícitos (jamás silenciados) y marcas de tiempo
de handler (evidencia de paralelismo RF03 y de overhead de comunicación M2).
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, ClassVar

from adaptation_swarm.bus.redis_bus import RedisBus
from adaptation_swarm.schemas.errors import BusError, MessageValidationError
from adaptation_swarm.schemas.messages import AgentId, BusMessage, MessageType

log = logging.getLogger(__name__)
AGENT_VERSION = "ag-v1"


class SwarmAgent:
    agent_id: ClassVar[AgentId]
    version: ClassVar[str] = AGENT_VERSION

    def __init__(self, bus: RedisBus | None = None, consumer: str | None = None):
        # `bus=None` = uso OFFLINE (construcción de la biblioteca): el agente genera, no consume.
        self.bus = bus
        self.consumer = consumer or f"{self.agent_id.value}-{uuid.uuid4().hex[:8]}"
        self.handled = 0
        self.last_gbest: dict[str, Any] | None = None
        self.gbest_broadcasts = 0
        self.failures = 0                 # fallos acumulados procesando mensajes (el agente sigue vivo)
        self._retry_pending = False

    async def handle(self, msg: BusMessage) -> list[BusMessage]:
        raise NotImplementedError

    def reply(
        self, msg: BusMessage, message_type: MessageType, payload: dict[str, Any], *,
        request_key: str | None = None,
    ) -> BusMessage:
        return BusMessage(
            correlation_id=msg.correlation_id, cycle_id=msg.cycle_id, sender=self.agent_id,
            receiver=msg.sender, message_type=message_type, iteration=msg.iteration,
            request_key=request_key if request_key is not None else msg.request_key,
            in_reply_to=msg.message_id, instance=msg.instance, payload=payload,
        )

    def _error_reply(self, msg: BusMessage, exc: Exception) -> BusMessage:
        return BusMessage(
            correlation_id=msg.correlation_id, cycle_id=msg.cycle_id, sender=self.agent_id,
            receiver=AgentId.AG0, message_type=MessageType.ERROR, iteration=msg.iteration,
            request_key=msg.request_key, in_reply_to=msg.message_id, instance=msg.instance, status="error",
            error={"code": type(exc).__name__, "message": str(exc)[:500]},
        )

    async def start(self) -> None:
        if self.bus is None:
            raise BusError(f"{self.agent_id.value} sin bus: no puede escuchar")
        await self.bus.ensure_group(self.agent_id)

    async def _process(self, entry_id: str, msg: BusMessage) -> None:
        if not await self.bus.claim(self.agent_id, msg.message_id):
            await self.bus.ack(self.agent_id, entry_id)     # duplicado: idempotencia
            return
        t_recv = time.time_ns()
        t0 = time.perf_counter()
        try:
            if msg.message_type is MessageType.GBEST_BROADCAST:
                self.last_gbest = msg.payload
                self.gbest_broadcasts += 1
                replies: list[BusMessage] = []
            else:
                replies = await self.handle(msg)
        except Exception as exc:  # error explícito hacia AG0; nunca silencio
            log.warning("%s falló procesando %s: %s", self.agent_id.value, msg.message_type.value, exc)
            await self.bus.release(self.agent_id, msg.message_id)
            replies = [self._error_reply(msg, exc)]
        timing = {
            "agent": self.agent_id.value, "t_recv_wall_ns": t_recv, "t_done_wall_ns": time.time_ns(),
            "handler_ms": (time.perf_counter() - t0) * 1000.0,
        }
        for r in replies:
            r.timing = dict(timing)
            await self.bus.publish(r)
        await self.bus.ack(self.agent_id, entry_id)
        self.handled += 1

    async def run(self, stop: asyncio.Event) -> None:
        await self.start()
        pending = True
        while not stop.is_set():
            try:
                entries = await self.bus.read(self.agent_id, self.consumer, pending=pending)
            except MessageValidationError as exc:
                log.warning("%s: %s", self.agent_id.value, exc)
                continue
            except BusError as exc:
                log.error("%s: bus caído: %s", self.agent_id.value, exc)
                await asyncio.sleep(0.5)
                continue
            if pending:
                pending = False        # la relectura de pendientes se hace una sola vez al arrancar
            if entries:
                outcomes = await asyncio.gather(*(self._process(eid, m) for eid, m in entries), return_exceptions=True)
                for (eid, m), out in zip(entries, outcomes):
                    if isinstance(out, BaseException):
                        # Un fallo procesando UN mensaje jamás mata al agente: se registra con su traza y el
                        # mensaje queda pendiente (se reintenta en la relectura de pendientes).
                        log.error("%s: fallo procesando %s (%s): %r", self.agent_id.value, m.message_type.value,
                                  m.message_id, out, exc_info=out)
                        self.failures += 1
                        self._retry_pending = True
            if self._retry_pending and not entries:
                pending = True         # sin tráfico nuevo: reintenta los pendientes que fallaron
                self._retry_pending = False
