"""Contrato de métricas de TIEMPO de OE2 (Fase B.1). Distingue tres cosas que NO deben confundirse:

    t_conv_ms     T_conv REAL de la PROPUESTA (AG0, DEC-10), sin cambios: desde que se inicializó el enjambre hasta la convergencia de g_best (`step_finalize`); incluye las evaluaciones de 𝓕 por el bus de
                  agentes. SOLO la propuesta lo produce. Es `None` en todo sistema sin convergencia iterativa (`decision_table`, `rules`, `bruteforce`): a un tiempo de decisión no se le llama T_conv.
    decision_ms   tiempo OPERACIONAL de decisión: desde que el sistema dispone del perfil y de W y empieza a decidir la configuración S hasta que tiene S final, SIN ensamblar el paquete. Se mide para la propuesta
                  (copia el valor que AG0 mide como `t_conv_ms`, sin recalcularlo) y para el convencional (lo mide `ConventionalAdapter`). Es una métrica común CANDIDATA: NO es T_conv validado.
    total_ms      perfil recibido → paquete validado listo (en proceso). Mismas fronteras en ambos lados; sin HTTP.
    L_resp        latencia HTTP extremo a extremo (P95 por corrida), con la misma metodología en ambos lados.

EQUIVALENCIA NO VALIDADA. Que `decision_ms` represente el «tiempo de convergencia» que exige OE2 para ambos sistemas NO está demostrado: el reloj de AG0 arranca tras `engine.initialize`, su intervalo incluye el bus
Redis y los agentes, y el convencional decide sin iterar (en el smoke: ≈128 ms vs ≈0,015 ms: procesos computacionalmente distintos, no una simple diferencia de rendimiento). Mientras esa validación metodológica esté
`PENDING`, ningún contraste confirmatorio puede apoyarse en `decision_ms` como si fuera T_conv (se calcula como exploratorio, fuera de Holm y marcado) y OE2 oficial sigue bloqueado
(`campaign_spec.open_blockers()`). Este módulo no redefine ni modifica el T_conv de la propuesta.
"""

from __future__ import annotations

CONTRACT_VERSION = "oe2-time-contract-v1"
COMMON_METRIC = "decision_ms"                    # identificador histórico del campo; semántica: métrica común CANDIDATA (ver VALIDATION_STATUS)
VALIDATION_STATUS = "PENDING_METHODOLOGICAL_VALIDATION"
T_CONV_EQUIVALENCE = "NOT_ESTABLISHED"
STATUS = "TECHNICAL_INTERNAL_DECISION_NOT_ADVISOR_APPROVED_UNVALIDATED"
PROPOSAL = "proposal"
PENDING_NOTE = ("decision_ms es una métrica común CANDIDATA de tiempo de decisión; su equivalencia con el T_conv de la propuesta NO está validada: resultado exploratorio, no confirmatorio, excluido de Holm")

DEFINITIONS = {
    "t_conv_ms": "T_conv REAL de la propuesta (AG0): tras engine.initialize -> convergencia de g_best (step_finalize); incluye el bus. Solo propuesta; None en el resto.",
    "decision_ms": "tiempo OPERACIONAL de decisión (candidata a métrica común; validación pendiente): perfil y W disponibles -> S final decidida, sin ensamblar el paquete. Propuesta: = t_conv_ms de AG0 (copiado). Convencional: medido alrededor de la decisión. NO es T_conv.",
    "total_ms": "perfil recibido -> paquete validado listo, en proceso (sin HTTP); mismas fronteras en ambos lados.",
    "L_resp": "latencia HTTP extremo a extremo; P95 por corrida; misma metodología en ambos lados.",
}
KNOWN_LIMITS = (
    "AG0 inicia el reloj tras engine.initialize: la inicialización de partículas queda fuera de decision_ms de la propuesta",
    "el intervalo de la propuesta incluye el bus Redis y los agentes (coste de la arquitectura)",
    "el convencional decide sin iteración: decision_ms no es convergencia en sentido estricto",
    "equivalencia metodológica entre decision_ms y T_conv NO validada",
)


def response_contract(role: str) -> dict:
    """Fragmento que viaja en la respuesta HTTP de cada endpoint: versión, métrica común CANDIDATA con su estado de validación, y si T_conv aplica a ese sistema."""
    return {"version": CONTRACT_VERSION, "candidate_common_metric": COMMON_METRIC, "validation": VALIDATION_STATUS, "t_conv_applies": role == PROPOSAL}
