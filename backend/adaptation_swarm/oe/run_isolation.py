"""Aislamiento ESTRUCTURAL de Redis entre las corridas de una campaña HTTP (D.4.1). Solo hace posible que una futura campaña garantice, y pruebe, que una corrida no hereda el estado por ciclo de la anterior.

Mecanismo (compatible con la arquitectura: el servidor ya lee `SWARM_REDIS_PREFIX`):
    1. NAMESPACE de campaña: `campaign_prefix(campaign_id)` = `oe2c:<id>:`. Toda la campaña usa ese prefijo (nunca el de producción `swarm:`, ni el de otra campaña, ni los de los pilotos), así que ninguna clave
       de otra campaña o de datos históricos puede mezclarse ni borrarse.
    2. LIMPIEZA CONTROLADA antes de cada corrida (`RedisRunIsolation.reset`): se espera a que el servidor quede quieto (ningún ciclo rezagado de la corrida anterior escribiendo) y se eliminan SOLO las claves
       por ciclo del namespace (`log:*`, `state:*`, `seen:*`); después se VERIFICA que no queda ninguna (si queda, la corrida no arranca). Los streams de agentes (`agent:*`) NO se tocan: son la infraestructura viva del
       servidor (grupos de consumidores) y están acotados por `stream_maxlen`; su longitud se registra.
    3. Al terminar la campaña, con el servidor detenido, `purge_namespace` borra todo el namespace de la campaña.

LO QUE NO RESUELVE (decisión metodológica PENDIENTE: política cold/warm de cachés): el PROCESO del servidor no se reinicia entre corridas del mismo (N, persistencia), así que sus cachés en memoria (validación de
paquetes, biblioteca, instancia del baseline) persisten; este módulo no decide si eso es lo deseado.
"""

from __future__ import annotations

import re
import time
from typing import Callable

NAMESPACE_ROOT = "oe2c:"
PER_CYCLE_KINDS = ("log:", "state:", "seen:")        # claves por ciclo (RedisBus.log_key / state_key / _seen_key)
STREAM_KIND = "agent:"                               # infraestructura viva: no se borra
MECHANISM = ("prefijo de campaña `oe2c:<campaign_id>:` + eliminación verificada de las claves por ciclo (log/state/seen) antes de cada corrida; streams de agentes intactos; "
             "purga del namespace de la campaña al terminar")
PENDING_DECISION = "PENDING_METHODOLOGICAL_DECISION: política cold/warm de cachés en memoria del servidor (el proceso no se reinicia entre corridas del mismo N y persistencia)"


def campaign_prefix(campaign_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "-", str(campaign_id)).strip("-")
    if not safe:
        raise ValueError("campaign_id vacío: no hay namespace de campaña")
    return f"{NAMESPACE_ROOT}{safe}:"


def _check_prefix(prefix: str) -> None:
    if not prefix.startswith(NAMESPACE_ROOT) or len(prefix) <= len(NAMESPACE_ROOT) + 1:
        raise ValueError(f"prefijo {prefix!r} fuera del namespace de campañas ({NAMESPACE_ROOT}<id>:): no se limpia (protege los datos de producción, pilotos y otras campañas)")


class PostgresRunProbe:
    """OBSERVACIÓN de solo lectura de PostgreSQL (no aísla ni limpia nada): cuenta los ciclos persistidos con la etiqueta de la campaña (`SWARM_API_RUN_LABEL`). Permite comprobar, por corrida, que la persistencia ON escribió filas y que la OFF
    no escribió ninguna. La persistencia síncrona mínima inserta `swarm_cycles` dentro de la petición; el fallo de esa inserción no llega a la respuesta (el router lo traga), y esta sonda es lo que lo delata."""

    def __init__(self, run_label: str, session_factory=None):
        self.run_label, self._session_factory = run_label, session_factory

    def cycles(self) -> int | None:
        """Ciclos persistidos con la etiqueta de la campaña; `None` si PostgreSQL no responde (nunca un valor inventado)."""
        try:
            from sqlalchemy import func, select
            factory = self._session_factory
            if factory is None:
                from app.db.session import SessionLocal as factory
            from app.models.swarm_adaptation import SwarmCycle
            with factory() as s:
                return int(s.scalar(select(func.count()).select_from(SwarmCycle).where(SwarmCycle.run_label == self.run_label)) or 0)
        except Exception:
            return None


class RedisRunIsolation:
    def __init__(self, prefix: str, client=None, *, quiesce_s: float = 1.0, timeout_s: float = 30.0, sleep: Callable[[float], None] = time.sleep):
        _check_prefix(prefix)
        self.prefix, self._client_obj, self.quiesce_s, self.timeout_s, self._sleep = prefix, client, quiesce_s, timeout_s, sleep

    @property
    def client(self):
        if self._client_obj is None:
            import redis
            from adaptation_swarm.config import SETTINGS
            self._client_obj = redis.Redis.from_url(SETTINGS.redis_url, socket_connect_timeout=5, socket_timeout=10)
        return self._client_obj

    def _keys(self, kinds) -> list[bytes]:
        out: list[bytes] = []
        for kind in kinds:
            out.extend(self.client.scan_iter(match=f"{self.prefix}{kind}*", count=500))
        return sorted(out)

    def wait_quiescent(self) -> None:
        """Espera a que el conjunto de claves por ciclo deje de cambiar durante `quiesce_s` (un ciclo rezagado de la corrida anterior seguiría escribiendo). Sin quietud en `timeout_s` ⇒ error: no se limpia a ciegas."""
        waited, snap = 0.0, self._keys(PER_CYCLE_KINDS)
        while True:
            self._sleep(self.quiesce_s)
            waited += self.quiesce_s
            now = self._keys(PER_CYCLE_KINDS)
            if now == snap:
                return
            if waited >= self.timeout_s:
                raise RuntimeError(f"Redis no quedó quieto en {self.timeout_s:.0f} s (hay ciclos activos en el namespace {self.prefix!r}): la corrida no arranca")
            snap = now

    def reset(self, run_id: str) -> dict:
        """Deja el namespace SIN estado por ciclo y lo verifica. Devuelve el registro que viaja con la corrida."""
        self.wait_quiescent()
        found = self._keys(PER_CYCLE_KINDS)
        deleted = self.client.delete(*found) if found else 0
        remaining = self._keys(PER_CYCLE_KINDS)
        if remaining:
            raise RuntimeError(f"aislamiento Redis fallido: quedan {len(remaining)} claves por ciclo en {self.prefix!r} tras la limpieza")
        streams = {k.decode() if isinstance(k, bytes) else k: int(self.client.xlen(k)) for k in self._keys((STREAM_KIND,))}
        return {"run_id": run_id, "prefix": self.prefix, "mechanism": MECHANISM, "per_cycle_keys_found": len(found), "per_cycle_keys_deleted": int(deleted), "per_cycle_keys_remaining": 0,
                "agent_streams_untouched": streams, "quiescent": True, "cache_policy": PENDING_DECISION}

    def purge_namespace(self) -> dict:
        """Fin de campaña (servidor detenido): borra TODO el namespace de ESTA campaña. Informa lo que había."""
        keys = self._keys(("",))
        n = self.client.delete(*keys) if keys else 0
        return {"prefix": self.prefix, "keys_found": len(keys), "keys_deleted": int(n)}
