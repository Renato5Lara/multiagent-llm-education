"""Bus de mensajes REAL sobre Redis Streams (DEC-05: Redis obligatorio; asesoría §3.4.2:
"Redis como bus de mensajes e intercambio de memoria compartida").

Claves (prefijo configurable, p. ej. `swarm:`):
  {p}agent:{AGx}          stream de entrada de cada agente (grupo de consumidores `grp:{AGx}`)
  {p}log:{cycle_id}       stream cronológico de TODOS los mensajes del ciclo (auditoría/trazabilidad)
  {p}state:{cycle_id}     hash con el estado de trabajo del ciclo (memoria compartida)
  {p}seen:{AGx}:{msg_id}  marca de idempotencia (SET NX con TTL)

No hay ningún sustituto: si Redis no está disponible, publicar/leer lanza `BusError` y el ciclo
falla explícitamente (stop_reason=error).
"""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis
from redis.exceptions import RedisError, ResponseError

from adaptation_swarm.config import SETTINGS, SwarmSettings
from adaptation_swarm.schemas.errors import BusError, MessageValidationError
from adaptation_swarm.schemas.messages import AgentId, BusMessage


class RedisBus:
    def __init__(self, settings: SwarmSettings = SETTINGS, *, url: str | None = None, prefix: str | None = None):
        self._settings = settings
        self._url = url or settings.redis_url
        self.prefix = prefix if prefix is not None else settings.key_prefix
        self._r: aioredis.Redis | None = None

    # ── conexión ─────────────────────────────────────────────────────────
    async def connect(self) -> "RedisBus":
        self._r = aioredis.from_url(self._url, decode_responses=True, socket_connect_timeout=3,
                                    max_connections=self._settings.redis_max_connections)
        try:
            await self._r.ping()
        except (RedisError, OSError) as exc:
            raise BusError(f"Redis no disponible en {self._url}: {exc}") from exc
        return self

    async def close(self) -> None:
        if self._r is not None:
            await self._r.aclose()
            self._r = None

    @property
    def redis(self) -> aioredis.Redis:
        if self._r is None:
            raise BusError("RedisBus no conectado (llamar connect())")
        return self._r

    # ── nombres de claves ────────────────────────────────────────────────
    def stream_key(self, agent: AgentId, instance: str | None = None) -> str:
        """Los streams de AG1–AG4 son compartidos (cualquier worker los atiende). Las respuestas a AG0 van al
        stream de la INSTANCIA que hizo la petición: con varios procesos AG0 no roba respuestas ajenas."""
        base = f"{self.prefix}agent:{agent.value}"
        return f"{base}:{instance}" if instance and agent is AgentId.AG0 else base

    def group_name(self, agent: AgentId) -> str:
        return f"grp:{agent.value}"

    def log_key(self, cycle_id: str) -> str:
        return f"{self.prefix}log:{cycle_id}"

    def state_key(self, cycle_id: str) -> str:
        return f"{self.prefix}state:{cycle_id}"

    def _seen_key(self, agent: AgentId, message_id: str) -> str:
        return f"{self.prefix}seen:{agent.value}:{message_id}"

    # ── transporte ───────────────────────────────────────────────────────
    async def ensure_group(self, agent: AgentId, instance: str | None = None) -> None:
        try:
            await self.redis.xgroup_create(self.stream_key(agent, instance), self.group_name(agent), id="$", mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise BusError(f"XGROUP CREATE falló: {exc}") from exc
        except (RedisError, OSError) as exc:
            raise BusError(f"Redis no disponible: {exc}") from exc

    async def publish(self, msg: BusMessage) -> str:
        """XADD al stream del receptor y al log del ciclo. Devuelve el entry id."""
        data = msg.to_json()
        try:
            pipe = self.redis.pipeline(transaction=False)
            pipe.xadd(self.stream_key(msg.receiver, msg.instance), {"data": data},
                      maxlen=self._settings.stream_maxlen, approximate=True)
            pipe.xadd(self.log_key(msg.cycle_id), {"data": msg.to_log_json()})
            pipe.expire(self.log_key(msg.cycle_id), self._settings.log_ttl_seconds)
            res = await pipe.execute()
        except (RedisError, OSError) as exc:
            raise BusError(f"publish falló ({msg.message_type.value}): {exc}") from exc
        return res[0]

    async def publish_many(self, msgs: list[BusMessage]) -> None:
        """Varias peticiones en UN solo viaje a Redis (pipeline): menos conexiones y menos latencia."""
        if not msgs:
            return
        try:
            pipe = self.redis.pipeline(transaction=False)
            for m in msgs:
                data = m.to_json()
                pipe.xadd(self.stream_key(m.receiver, m.instance), {"data": data},
                          maxlen=self._settings.stream_maxlen, approximate=True)
                pipe.xadd(self.log_key(m.cycle_id), {"data": m.to_log_json()})
            for cyc in {m.cycle_id for m in msgs}:
                pipe.expire(self.log_key(cyc), self._settings.log_ttl_seconds)
            await pipe.execute()
        except (RedisError, OSError) as exc:
            raise BusError(f"publish_many falló: {exc}") from exc

    async def read(
        self, agent: AgentId, consumer: str, *, count: int = 32, block_ms: int = 200, pending: bool = False,
        instance: str | None = None,
    ) -> list[tuple[str, BusMessage]]:
        """XREADGROUP. `pending=True` relee los mensajes entregados y no confirmados (id "0")."""
        try:
            resp = await self.redis.xreadgroup(
                self.group_name(agent), consumer, {self.stream_key(agent, instance): "0" if pending else ">"},
                count=count, block=None if pending else block_ms,
            )
        except (RedisError, OSError) as exc:
            raise BusError(f"XREADGROUP falló: {exc}") from exc
        out: list[tuple[str, BusMessage]] = []
        for _stream, entries in resp or []:
            for entry_id, fields in entries:
                try:
                    out.append((entry_id, BusMessage.from_json(fields["data"])))
                except Exception as exc:  # mensaje corrupto: se confirma para no re-entregarlo eternamente
                    await self.ack(agent, entry_id, instance)
                    raise MessageValidationError(f"mensaje inválido en {entry_id}: {exc}") from exc
        return out

    async def ack(self, agent: AgentId, entry_id: str, instance: str | None = None) -> None:
        try:
            await self.redis.xack(self.stream_key(agent, instance), self.group_name(agent), entry_id)
        except (RedisError, OSError) as exc:
            raise BusError(f"XACK falló: {exc}") from exc

    # ── idempotencia ─────────────────────────────────────────────────────
    async def claim(self, agent: AgentId, message_id: str) -> bool:
        """True si es la primera vez que `agent` procesa `message_id` (SET NX)."""
        try:
            ok = await self.redis.set(self._seen_key(agent, message_id), "1", nx=True,
                                      ex=self._settings.seen_ttl_seconds)
        except (RedisError, OSError) as exc:
            raise BusError(f"claim falló: {exc}") from exc
        return bool(ok)

    async def release(self, agent: AgentId, message_id: str) -> None:
        try:
            await self.redis.delete(self._seen_key(agent, message_id))
        except (RedisError, OSError) as exc:
            raise BusError(f"release falló: {exc}") from exc

    # ── memoria compartida del ciclo ─────────────────────────────────────
    async def set_state(self, cycle_id: str, mapping: dict[str, Any]) -> None:
        flat = {k: json.dumps(v, default=str) for k, v in mapping.items()}
        try:
            pipe = self.redis.pipeline(transaction=False)
            pipe.hset(self.state_key(cycle_id), mapping=flat)
            pipe.expire(self.state_key(cycle_id), self._settings.log_ttl_seconds)
            await pipe.execute()
        except (RedisError, OSError) as exc:
            raise BusError(f"set_state falló: {exc}") from exc

    async def get_state(self, cycle_id: str) -> dict[str, Any]:
        try:
            raw = await self.redis.hgetall(self.state_key(cycle_id))
        except (RedisError, OSError) as exc:
            raise BusError(f"get_state falló: {exc}") from exc
        return {k: json.loads(v) for k, v in raw.items()}

    # ── trazabilidad ─────────────────────────────────────────────────────
    async def read_log(self, cycle_id: str) -> list[BusMessage]:
        try:
            entries = await self.redis.xrange(self.log_key(cycle_id))
        except (RedisError, OSError) as exc:
            raise BusError(f"read_log falló: {exc}") from exc
        return [BusMessage.from_json(f["data"]) for _id, f in entries]

    async def purge_prefix(self) -> int:
        """Borra TODAS las claves con este prefijo (uso en tests con prefijo aislado)."""
        if not self.prefix or self.prefix == "swarm:":
            raise BusError("purge_prefix exige un prefijo aislado distinto del de producción")
        n = 0
        async for key in self.redis.scan_iter(match=f"{self.prefix}*", count=500):
            n += await self.redis.delete(key)
        return n
