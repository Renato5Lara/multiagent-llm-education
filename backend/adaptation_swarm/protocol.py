"""Factores experimentales de la arquitectura que SÍ existen en el código (OE3): protocolo de comunicación de AG0 y rol de AG1.

Los valores por defecto reproducen EXACTAMENTE el comportamiento de las corridas históricas (despacho por lotes, difusión de g_best, arranque heurístico de AG1): una
`SwarmOrchestrator` sin `protocol` se comporta igual que antes. Los demás niveles son variantes reales del mismo mecanismo, no sustitutos simulados:

    dispatch          "batch"      todas las peticiones de una iteración salen en un solo pipeline de Redis y AG2–AG4 responden en paralelo (RF03);
                      "sequential" una petición por vez: AG0 espera cada respuesta antes de publicar la siguiente (misma semántica, sin solapamiento).
    broadcast_gbest   True         AG0 difunde `GBEST_BROADCAST` a AG1–AG4 en cada iteración (retroalimentación del enjambre);
                      False        no la difunde (menos mensajes por el bus).
    heuristic_seed    True         la partícula 0 arranca en el punto heurístico derivado de W por AG1 (DEC-02);
                      False        las N partículas arrancan de U(0,2) (AG1 solo aporta W).

El mecanismo de enjambre (PSO completo, solo cognitivo, solo social) y el tamaño del enjambre se controlan con `PSOParams` (`c1`, `c2`, `n_particles`).
La réplica de agentes (`replicas`) se controla en `SwarmStack`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

DISPATCH_MODES = ("batch", "sequential")


@dataclass(frozen=True, slots=True)
class ProtocolConfig:
    dispatch: str = "batch"
    broadcast_gbest: bool = True
    heuristic_seed: bool = True

    def __post_init__(self) -> None:
        if self.dispatch not in DISPATCH_MODES:
            raise ValueError(f"dispatch debe ser uno de {DISPATCH_MODES}: {self.dispatch!r}")

    def to_dict(self) -> dict:
        return asdict(self)
