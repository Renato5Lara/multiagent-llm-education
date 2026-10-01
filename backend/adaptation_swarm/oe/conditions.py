"""Condiciones experimentales de OE2, OE3 y OE4. Una `Condition` fija TODO lo que puede variar entre dos ejecuciones comparables; lo que no está aquí es constante (misma biblioteca, mismos
perfiles, mismos pesos de 𝓕, mismas semillas, mismo ensamblado y validación del paquete).

Factores (solo los que EXISTEN en la arquitectura; ver `protocol.py`):
    OE3 · roles de los agentes      heuristic_seed (rol de AG1 en el arranque), replicas (consumidores por agente)
    OE3 · protocolo de comunicación dispatch (batch|sequential), broadcast_gbest (True|False)
    OE3 · mecanismo de enjambre     mechanism: "pso" (c1, c2 > 0), "cognitive" (c2 = 0: cada partícula sigue solo su p_best), "social" (c1 = 0: sigue solo g_best); n_particles
    OE2 · sistema                   swarm | rules | bruteforce (`baselines/conventional.py`)
    OE4 · carga                     concurrency (usuarios virtuales en bucle cerrado, sin tiempo de espera)
"""

from __future__ import annotations

import itertools
from dataclasses import asdict, dataclass, replace

from adaptation_swarm.baselines.conventional import SYSTEMS as BASELINE_SYSTEMS
from adaptation_swarm.protocol import DISPATCH_MODES, ProtocolConfig
from adaptation_swarm.pso.params import PSOParams

SYSTEMS = ("swarm", *BASELINE_SYSTEMS)
MECHANISMS = ("pso", "cognitive", "social")
_REF = PSOParams()                               # c1 = c2 = 1.494, N = 20 (DEC-08)


@dataclass(frozen=True, slots=True)
class Condition:
    system: str = "swarm"
    dispatch: str = "batch"
    broadcast_gbest: bool = True
    heuristic_seed: bool = True
    mechanism: str = "pso"
    replicas: int = 1
    n_particles: int = _REF.n_particles
    concurrency: int = 1

    def __post_init__(self) -> None:
        if self.system not in SYSTEMS:
            raise ValueError(f"system debe ser uno de {SYSTEMS}: {self.system!r}")
        if self.dispatch not in DISPATCH_MODES:
            raise ValueError(f"dispatch inválido: {self.dispatch!r}")
        if self.mechanism not in MECHANISMS:
            raise ValueError(f"mechanism debe ser uno de {MECHANISMS}: {self.mechanism!r}")
        if self.replicas < 1 or self.n_particles < 1 or self.concurrency < 1:
            raise ValueError("replicas, n_particles y concurrency deben ser ≥ 1")

    @property
    def name(self) -> str:
        if self.system != "swarm":
            return f"{self.system}|c{self.concurrency}"
        return (f"swarm|{self.dispatch}|bc{int(self.broadcast_gbest)}|h{int(self.heuristic_seed)}|{self.mechanism}|r{self.replicas}"
                f"|N{self.n_particles}|c{self.concurrency}")

    def protocol(self) -> ProtocolConfig:
        return ProtocolConfig(self.dispatch, self.broadcast_gbest, self.heuristic_seed)

    def pso_params(self) -> PSOParams:
        c1 = 0.0 if self.mechanism == "social" else _REF.c1
        c2 = 0.0 if self.mechanism == "cognitive" else _REF.c2
        return replace(_REF, n_particles=self.n_particles, c1=c1, c2=c2)

    def factors(self) -> dict:
        return asdict(self)


def oe2_systems(concurrency: int = 1) -> list[Condition]:
    """Propuesta y sistemas convencionales bajo la MISMA carga (condiciones equivalentes)."""
    return [Condition(system=s, concurrency=concurrency) for s in SYSTEMS]


def oe3_full_factorial() -> list[Condition]:
    """2 (arranque heurístico) × 2 (réplicas) × 2 (despacho) × 2 (difusión) × 3 (mecanismo) = 48 condiciones; carga = 1 usuario (aísla el efecto de la configuración)."""
    return [Condition(dispatch=d, broadcast_gbest=b, heuristic_seed=h, mechanism=m, replicas=r)
            for h, r, d, b, m in itertools.product((True, False), (1, 2), DISPATCH_MODES, (True, False), MECHANISMS)]


def oe3_one_factor_at_a_time() -> list[Condition]:
    """Cribado barato: la referencia y cada factor cambiado de a uno (7 condiciones)."""
    ref = Condition()
    return [ref, replace(ref, heuristic_seed=False), replace(ref, replicas=2), replace(ref, dispatch="sequential"), replace(ref, broadcast_gbest=False),
            replace(ref, mechanism="cognitive"), replace(ref, mechanism="social")]


OE3_FACTORS = ("heuristic_seed", "replicas", "dispatch", "broadcast_gbest", "mechanism")


def oe4_grid(concurrency=(1, 5, 10, 25, 50, 100), n_particles=(10, 20, 30)) -> list[Condition]:
    """Condiciones de simulación del artefacto: carga (usuarios simultáneos, los escenarios de la asesoría §3.4.2 y dos intermedios) × tamaño del enjambre (barrido pre-registrado {10,20,30})."""
    return [Condition(concurrency=c, n_particles=n) for n in n_particles for c in concurrency]
