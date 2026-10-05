"""Contrato de métricas de TIEMPO de OE2 (Fase B.1; versión v2 en D.3). Distingue cosas que NO deben confundirse:

    time_to_final_config_ms   INDICADOR OPERACIONAL COMÚN (D.3, decisión B1-B congelada de forma PROVISIONAL, no aprobada por el asesor): tiempo desde que el sistema tiene el perfil validado hasta que tiene la
                  configuración S final decidida, SIN ensamblar el paquete, sin HTTP y sin persistencia; medido en condición AISLADA (en proceso, concurrencia 1). Se calcula para AMBOS sistemas con la misma frontera
                  conceptual. NO es T_conv ni «convergencia»: no se le asigna equivalencia con T_conv.

    t_conv_ms     T_conv REAL de la PROPUESTA (AG0, DEC-10), sin cambios: desde que se inicializó el enjambre hasta la convergencia de g_best (`step_finalize`); incluye las evaluaciones de 𝓕 por el bus de
                  agentes. SOLO la propuesta lo produce. Es `None` en todo sistema sin convergencia iterativa (`decision_table`, `rules`, `bruteforce`): a un tiempo de decisión no se le llama T_conv.
    decision_ms   campo HISTÓRICO (LEGACY / exploratorio). Su semántica NO coincide con la del indicador común: en la propuesta copia `t_conv_ms` de AG0 (reloj tras `engine.initialize`, sin AG1 ni inicialización) y en el
                  convencional mide solo `_decide` (sin W). No se reutiliza como indicador común ni como T_conv; se conserva para trazabilidad de los datos exploratorios de D.1.
    total_ms      perfil recibido → paquete validado listo (en proceso). Mismas fronteras en ambos lados; sin HTTP.
    L_resp        latencia HTTP extremo a extremo (P95 por corrida), con la misma metodología en ambos lados.

SIN EQUIVALENCIA CON T_conv (decisión B1, D.3). No se afirma que ningún tiempo de los sistemas convencionales sea un «tiempo de convergencia»: el convencional decide sin iterar y no tiene criterio |ΔF|<ε (en el smoke: ≈128 ms
vs ≈0,015 ms: procesos computacionalmente distintos, no una simple diferencia de rendimiento). T_conv queda SOLO en la propuesta; lo que se compara entre sistemas es el indicador operacional separado
`time_to_final_config_ms`, y mientras su validación metodológica esté `PENDING` ningún contraste confirmatorio puede apoyarse en él (exploratorio, fuera de Holm, marcado) y OE2 oficial sigue bloqueado
(`campaign_spec.open_blockers()`). Este módulo no redefine ni modifica el T_conv de la propuesta.
"""

from __future__ import annotations

CONTRACT_VERSION = "oe2-time-contract-v2"
TTFC_METRIC = "time_to_final_config_ms"          # indicador operacional común (D.3); NO es T_conv
LEGACY_METRIC = "decision_ms"                    # campo histórico: semántica distinta (ver docstring); exploratorio, no se reutiliza
LEGACY_STATUS = "LEGACY_EXPLORATORY"
COMMON_METRIC = TTFC_METRIC                      # métrica común CANDIDATA vigente (ver VALIDATION_STATUS)
VALIDATION_STATUS = "PENDING_METHODOLOGICAL_VALIDATION"
T_CONV_EQUIVALENCE = "NOT_ESTABLISHED"
STATUS = "TECHNICAL_INTERNAL_DECISION_NOT_ADVISOR_APPROVED_UNVALIDATED"
PROPOSAL = "proposal"
APPROVED_STATUS = "ADVISOR_APPROVED"              # único valor de `TTFC_CONTRACT["status"]` que, junto con VALIDATION_STATUS == "VALIDATED", resuelve B1. Aprobar el indicador común NO es aprobar equivalencia con T_conv.
PENDING_NOTE = ("el indicador común (time_to_final_config_ms) es operacional y NO es T_conv: su validación metodológica está pendiente (decisión provisional, no aprobada por el asesor): resultado exploratorio, no confirmatorio, excluido de Holm")
LEGACY_NOTE = "decision_ms es un campo HISTÓRICO (semántica distinta de la del indicador común): exploratorio, no confirmatorio, excluido de Holm; no se reutiliza como indicador común ni como T_conv"

# Contrato del indicador operacional común (D.3). Todo lo que el análisis necesita saber de él vive aquí; nada se infiere de textos libres.
TTFC_CONTRACT = {
    "name": TTFC_METRIC, "unit": "ms", "status": "FROZEN_PROVISIONAL_NOT_ADVISOR_APPROVED", "validation": VALIDATION_STATUS, "is_t_conv": False, "t_conv_equivalence_claimed": False,
    "definition": "tiempo hasta obtener la configuración final S: del perfil validado en poder del sistema a la S final decidida; sin ensamblado/validación del paquete, sin HTTP, sin persistencia, sin 𝓕 de reporte",
    "start": {"swarm": "fin de `step_receive` de AG0 (RF01 validado y ciclo registrado): `t_start_ns`", "decision_table": "perfil ya validado (`ProfileRequest`), antes de calcular cualquier insumo que el sistema necesite para decidir"},
    "stop": {"swarm": "entrada de `step_finalize` de AG0 (g_best final): `t_search_ns + t_conv_ms`: el MISMO instante en que AG0 cierra T_conv", "decision_table": "configuración S devuelta por la decisión"},
    "swarm_formula": "(t_search_ns − t_start_ns)/1e6 + t_conv_ms   [incluye AG1 (W) por el bus, `engine.initialize` y toda la búsqueda; t_conv_ms no cambia]",
    "includes": {"swarm": ["petición a AG1 (W) por el bus", "engine.initialize + semilla heurística", "búsqueda iterativa completa (T_conv)"], "conventional": ["W solo en los sistemas que lo usan para decidir", "la decisión"]},
    "excludes": ["ensamblado y validación del paquete", "𝓕 de reporte", "HTTP y cola del servidor", "persistencia", "descarga de audio"],
    "condition": {"id": "isolated_inprocess", "concurrency": 1, "http": False, "note": "una observación con concurrencia > 1 o por HTTP NO es este indicador (mezclaría tiempo algorítmico con cola del event loop/servidor)"},
    "experimental_unit": "perfil: media de las K réplicas; diseño pareado swarm vs decision_table sobre los mismos perfiles",
    "statistical_treatment": {"status": "PROVISIONAL", "plan": "Shapiro-Wilk sobre diferencias → t pareada sobre log(tiempo) si razonable; si no Wilcoxon signed-rank (como el resto de contrastes pareados de OE2)",
                              "family": "PENDING: pertenencia a una familia de Holm no decidida; se calcula como EXPLORATORIO, fuera de Holm", "confirmatory": False},
    "provenance": ["time_contract.CONTRACT_VERSION", "campaign_spec.oe2.time_contract.common_indicator", "condición de medición por observación (`ttfc_isolated`)"],
    "known_asymmetries": ["obtención y evaluación de artefactos candidatos: dentro del indicador en el swarm, fuera en el convencional (se hace en el ensamblado). Limitación DOCUMENTADA; la frontera no se modifica ni se añade trabajo al convencional."],
    "separate_from": {"t_conv_ms": "métrica propia de la propuesta (DEC-10), definición intacta", "decision_ms": "campo histórico/legacy (frontera distinta)", "total_ms": "perfil → paquete validado listo (incluye ensamblado)", "L_resp": "latencia HTTP extremo a extremo"},
}


def ttfc_swarm_ms(t_start_ns: int | None, t_search_ns: int | None, t_conv_ms: float | None) -> float | None:
    """Indicador común de la PROPUESTA reconstruido desde las marcas que AG0 ya expone (observabilidad aditiva). `t_conv_ms` no se recalcula. Sin alguna de las tres marcas ⇒ None (nunca un valor inventado);
    marcas incoherentes (`t_search_ns < t_start_ns`) ⇒ ValueError (no se corrige en silencio)."""
    if t_start_ns is None or t_search_ns is None or t_conv_ms is None:
        return None
    if t_search_ns < t_start_ns:
        raise ValueError(f"marcas de AG0 incoherentes: t_search_ns ({t_search_ns}) < t_start_ns ({t_start_ns})")
    return (t_search_ns - t_start_ns) / 1e6 + t_conv_ms

DEFINITIONS = {
    "time_to_final_config_ms": TTFC_CONTRACT["definition"] + " (condición aislada; propuesta: (t_search_ns − t_start_ns)/1e6 + t_conv_ms). NO es T_conv.",
    "t_conv_ms": "T_conv REAL de la propuesta (AG0): tras engine.initialize -> convergencia de g_best (step_finalize); incluye el bus. Solo propuesta; None en el resto.",
    "decision_ms": "campo HISTÓRICO (LEGACY/exploratorio): propuesta = t_conv_ms de AG0 (copiado); convencional = medido alrededor de `_decide`. Frontera distinta de la del indicador común; NO es T_conv.",
    "total_ms": "perfil recibido -> paquete validado listo, en proceso (sin HTTP); mismas fronteras en ambos lados.",
    "L_resp": "latencia HTTP extremo a extremo; P95 por corrida; misma metodología en ambos lados.",
}
MEASUREMENT_REGIONS = {
    "time_to_final_config_ms": "perfil validado → S final decidida (propuesta: fin de step_receive → entrada de step_finalize; convencional: perfil validado → decisión, incluyendo W si el sistema lo usa); condición aislada en proceso",
    "decision_ms": "LEGACY: propuesta AG0 tras engine.initialize → step_finalize; convencional alrededor de `_decide` (fronteras distintas entre sí)",
    "total_ms": "perfil recibido → paquete validado listo (ensamblado y validación del paquete incluidos en ambos lados)",
    "http_latency": "petición → último byte de la respuesta: decisión + ensamblado/validación + serialización; NO incluye la evaluación de 𝓕 de reporte del convencional",
    "quality_reporting": "𝓕 de reporte del convencional: FUERA de toda región de tiempo (se reconstruye desde S fuera de la petición); en la propuesta 𝓕 es inherente a la búsqueda",
}
KNOWN_LIMITS = (
    "decision_ms (legacy) no comparte frontera entre sistemas: la inicialización de partículas y AG1 quedan fuera de la propuesta y W fuera del convencional; por eso no se reutiliza",
    "el intervalo del indicador común de la propuesta incluye el bus Redis y los agentes (coste de la arquitectura)",
    "el convencional decide sin iterar: el indicador común es tiempo hasta la configuración final, no convergencia en sentido estricto",
    "no se afirma equivalencia entre el indicador común y T_conv; la decisión de usarlo es provisional y no está aprobada por el asesor",
    "ASIMETRÍA CONOCIDA (D.4, pendiente metodológico, frontera sin cambios): el swarm obtiene y evalúa los artefactos candidatos (AG2–AG4 por el bus, lectura de biblioteca, scoring) DURANTE la búsqueda, dentro del indicador; "
    "el convencional decide primero y obtiene/ensambla los artefactos después, fuera del indicador",
)


def response_contract(role: str) -> dict:
    """Fragmento que viaja en la respuesta HTTP de cada endpoint: versión, métrica común CANDIDATA con su estado de validación, y si T_conv aplica a ese sistema."""
    return {"version": CONTRACT_VERSION, "candidate_common_metric": COMMON_METRIC, "validation": VALIDATION_STATUS, "t_conv_applies": role == PROPOSAL, "legacy_metric": LEGACY_METRIC, "legacy_status": LEGACY_STATUS}
