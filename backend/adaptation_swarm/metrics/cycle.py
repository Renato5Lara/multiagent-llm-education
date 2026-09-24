"""Métricas por ciclo (RF06: tiempo, iteraciones, estado de convergencia) y sobrecoste de
comunicación inter-agente (M2), derivadas del log de mensajes REAL del bus."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from adaptation_swarm.schemas.messages import BusMessage, MessageType

_REQUEST_TYPES = {
    MessageType.PROFILE_REQUEST, MessageType.CODE_REQUEST, MessageType.DIAGRAM_REQUEST, MessageType.TEXT_REQUEST,
}


@dataclass
class CycleMetrics:
    cycle_id: str
    correlation_id: str
    profile_id: str
    status: str
    stop_reason: str
    k_stop: int | None
    t_conv_ms: float | None            # T_conv en milisegundos (t_convergencia − t_inicio_busqueda)
    total_ms: float                    # ciclo completo (recepción → paquete)
    gbest_F: float | None
    n_messages: int = 0
    comm_overhead_ms: float | None = None
    parallel_overlap: bool | None = None
    inflight_overlap: bool | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def t_conv_iterations(self) -> int | None:
        return self.k_stop

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id, "correlation_id": self.correlation_id, "profile_id": self.profile_id,
            "status": self.status, "stop_reason": self.stop_reason, "k_stop": self.k_stop,
            "t_conv_iterations": self.t_conv_iterations, "t_conv_ms": self.t_conv_ms, "total_ms": self.total_ms,
            "gbest_F": self.gbest_F, "n_messages": self.n_messages,
            "comm_overhead_ms": self.comm_overhead_ms, "parallel_overlap": self.parallel_overlap,
            "inflight_overlap": self.inflight_overlap, **self.extra,
        }


def comm_overhead_ms(log: Sequence[BusMessage]) -> float:
    """M2: Σ sobre pares petición→respuesta de (latencia observada − tiempo de handler del agente)."""
    sent = {m.message_id: m for m in log if m.message_type in _REQUEST_TYPES}
    total = 0.0
    for m in log:
        req = sent.get(m.in_reply_to) if m.in_reply_to else None
        if req is None:
            continue
        rtt_ms = (m.t_wall_ns - req.t_wall_ns) / 1e6
        handler = float(m.timing.get("handler_ms", 0.0))
        total += max(0.0, rtt_ms - handler)
    return total


def inflight_overlap(log: Sequence[BusMessage]) -> bool:
    """RF03 (despacho concurrente): ¿hubo peticiones a agentes DISTINTOS en vuelo a la vez, es decir,
    con ventanas [t_petición, t_respuesta] solapadas? Se mide sobre el log real del bus."""
    sent = {m.message_id: m for m in log if m.message_type in _REQUEST_TYPES}
    windows: list[tuple[str, int, int]] = []
    for m in log:
        req = sent.get(m.in_reply_to) if m.in_reply_to else None
        if req is not None and m.sender.value in {"AG2", "AG3", "AG4"}:
            windows.append((m.sender.value, req.t_wall_ns, m.t_wall_ns))
    for i, (a, s1, e1) in enumerate(windows):
        for b, s2, e2 in windows[i + 1:]:
            if a != b and s1 < e2 and s2 < e1:
                return True
    return False


def parallel_overlap(log: Sequence[BusMessage]) -> bool:
    """RF03 (ejecución concurrente): ¿algún par de agentes distintos tuvo HANDLERS con intervalos de
    tiempo solapados? Con recuperación desde biblioteca los handlers duran microsegundos, así que puede
    dar False aun cuando el despacho fue concurrente (ver `inflight_overlap`)."""
    spans: list[tuple[str, int, int]] = []
    seen: set[tuple[str, int, int]] = set()
    for m in log:
        t = m.timing
        if "t_recv_wall_ns" in t and m.sender.value in {"AG2", "AG3", "AG4"}:
            key = (t["agent"], t["t_recv_wall_ns"], t["t_done_wall_ns"])
            if key not in seen:
                seen.add(key)
                spans.append(key)
    for i, (a, s1, e1) in enumerate(spans):
        for b, s2, e2 in spans[i + 1:]:
            if a != b and s1 < e2 and s2 < e1:
                return True
    return False
