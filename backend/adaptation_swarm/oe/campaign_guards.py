"""Guards de campaña OE2 DINÁMICOS: cada bloqueo se CALCULA del estado real (constantes de contrato, registro de definiciones, esquema de registros, política de persistencia, provenance), no de un texto fijo.
Modificar un mensaje no desbloquea nada: para desbloquear hay que cambiar el estado que lo origina (p. ej. que el contrato de tiempo pase a VALIDATED, o que la definición de L_resp y la política de persistencia sean
compatibles). Ningún guard decide cuestiones metodológicas: los marcados `frozen` (B1, B5, B13) solo REPRESENTAN la decisión pendiente.

    B1   indicador común `time_to_final_config_ms` sin aprobar/validar (decisión B1-B provisional)    (metodológico, congelado). Se resuelve SOLO con su estado de aprobación explícito; NUNCA con una
         equivalencia con T_conv (declararla es una contradicción de B1).
    B3   la evaluación de 𝓕 de reporte del baseline corre dentro de la petición medida                (técnico)
    B5   decisión B5-C (comparación OFF común + costo ON de la propuesta) sin aprobar                  (metodológico, congelado). Se resuelve SOLO con su estado de aprobación explícito y coherencia
         de la política; NO modificando L_resp ni activando persistencia en el baseline.
    B6   timeout de cliente no configurado (provisional = aviso no crítico)                             (técnico)
    B7   política del generador de carga no definida                                                    (técnico)
    B11  esquema de corrida/análisis HTTP sin integrar (campos requeridos, `inprocess_obs`)            (técnico)
    B12  provenance incompleta (solo con provenance)                                                    (técnico)
    B13  alcance del comparador pendiente de validación (OE2 dice «sistemas convencionales»)           (metodológico, congelado)
    P6   hardware objetivo sin aprobación metodológica (`oe2.hardware_target_validation`)             (metodológico, congelado). `meets_target(hw)` es solo COMPATIBILIDAD TÉCNICA con el criterio operativo del código;
         NO resuelve P6. Se resuelve SOLO con su estado de aprobación explícito.
    PEND decisiones metodológicas de D.5 sin resolver (hoy: estadístico de latencia y H1/L_resp literal; las demás tienen decisión INTERNA F.2.3, no aprobada por el asesor)   (metodológico, congelado)
    DEF  definiciones PENDING DE LAS DEPENDENCIAS DEL OBJETIVO (`definitions.blocked_for(experiment)`)  (definición; dependency-aware: las PENDING de OE1/OE5 que OE2 no necesita no bloquean)
"""

from __future__ import annotations

import inspect
import re
from dataclasses import asdict, dataclass
from typing import Mapping

REQUIRED_RUN_FIELDS = (
    "campaign_id", "system", "system_role", "run_id", "batch_seed", "profile_sequence_hash", "load", "users", "warmup_seconds", "persist_policy", "p95_latency_ms", "throughput_http",
    "error_count", "timeout_count", "decision_ms_mean", "decision_ms_median", "decision_ms_p95", "t_conv_ms_mean", "metric_validation_status", "comparable", "client_timeout_s", "official", "oe2_official",
    "persistence_condition", "comparison_role", "confirmatory_role", "persist_policy_effective", "redis_isolation",
    "run_index", "execution_index", "server_instance", "server_restarted_before_run", "server_runs_served_before", "postgres_observation",
    "started_utc", "pair_first_system", "non_timeout_errors", "timeout_rate", "total_failure_rate", "non_timeout_error_rate", "latency_p95_successful_ms", "throughput_successful_rps",
)


@dataclass(frozen=True)
class Blocker:
    id: str
    kind: str                 # methodological | technical | definition
    critical: bool
    reason: str
    frozen: bool = False      # decisión metodológica pendiente: el código solo la representa

    def as_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        return f"[{self.id}] {self.reason}"


def l_resp_requires_sync_persistence() -> bool:
    """Lee la definición APROBADA de L_resp (registro de definiciones, en vivo): ¿exige persistencia? FALLA CERRADO: si el texto menciona la persistencia, se considera exigida salvo que EXCLUYA de forma explícita
    la persistencia síncrona («sin / no incluye / excluye … persistencia síncrona»); reformular la definición (p. ej. «incorpora persistencia») no desbloquea B5. La persistencia ASÍNCRONA excluida de la definición
    vigente no cuenta como exclusión de la síncrona."""
    from adaptation_swarm.oe import definitions as defs
    text = defs.DEFINITIONS["latency_l_resp"]["definition"]
    mentions = "persistencia" in text.lower()
    explicitly_excluded = bool(re.search(r"(?:sin|no incluye|excluye)\b[^;]*persistencia s[ií]ncrona", text, re.I))
    return mentions and not explicitly_excluded


def persistence_status(policy: str | None, baseline_supports_persistence: bool | None = None) -> dict:
    """Estado de la política de persistencia frente a la definición vigente de L_resp. NO decide ON/OFF: solo informa la (in)compatibilidad."""
    from adaptation_swarm.oe import campaign_spec
    required = l_resp_requires_sync_persistence()
    supports = campaign_spec.SPEC["oe2"]["persist_policy"]["on_supported_for_comparison"] if baseline_supports_persistence is None else baseline_supports_persistence
    if policy not in ("on", "off"):
        status = "UNDECIDED"
    elif required and policy == "off":
        status = "INCOMPATIBLE_WITH_APPROVED_L_RESP_DEFINITION"
    elif required and policy == "on" and not supports:
        status = "UNSUPPORTED_BY_BASELINE"
    else:
        status = "COMPATIBLE"
    return {"policy": policy, "l_resp_definition_requires_sync_persistence": required, "baseline_supports_persistence": supports, "status": status}


def persistence_decision_state(policy: str | None) -> dict:
    """Estado de la decisión B5-C. Se resuelve SOLO si (1) tiene aprobación EXPLÍCITA del asesor, (2) su estructura es coherente (contraste OFF, costo ON de la propuesta, sin persistencia en el baseline, OFF declarado como NO
    literal), (3) la política efectiva es la del contraste y (4) la definición aprobada de L_resp sigue exigiendo la persistencia síncrona (nadie la reformuló para que OFF parezca literal). Nada de esto exige que el
    baseline persista ni que L_resp cambie."""
    from adaptation_swarm.oe import campaign_spec
    pp = campaign_spec.SPEC["oe2"]["persist_policy"]
    approved = pp.get("status") == campaign_spec.APPROVED_STATUS
    reasons = [] if approved else [f"sin aprobación del asesor (estado {pp.get('status')})"]
    if not (pp.get("comparison_persistence") == "off" and pp.get("proposal_persistence_cost") == "on" and pp.get("artificial_persistence_in_baseline") is False
            and pp.get("comparison_off_is_literal_l_resp") is False and pp.get("on_supported_for_comparison") is False):
        reasons.append("la estructura de la decisión no es coherente (contraste OFF, costo ON de la propuesta, sin persistencia en el baseline, OFF no literal)")
    if policy != pp.get("comparison_persistence"):
        reasons.append(f"la política efectiva {policy!r} no es la del contraste ({pp.get('comparison_persistence')!r})")
    if not l_resp_requires_sync_persistence():
        reasons.append("la definición aprobada de L_resp dejó de exigir la persistencia síncrona (fue modificada)")
    return {"approved": approved, "pending_approval": not approved, "reasons": reasons, "blocking": bool(reasons)}


def pending_methodological_decisions() -> list[str]:
    """Decisiones de `campaign_spec.oe2.methodological_decisions` aún sin resolver. FALLA CERRADO: se resuelve solo con `status == DECIDED` y `chosen` ∈ `options`; cualquier otra cosa (estado ausente, elección fuera de las opciones,
    estructura mal formada) cuenta como pendiente. No decide nada y no mira textos."""
    from adaptation_swarm.oe import campaign_spec
    decisions = campaign_spec.SPEC["oe2"].get("methodological_decisions")
    if not isinstance(decisions, Mapping) or not decisions:
        return ["<estructura de decisiones ausente>"]
    return sorted(k for k, d in decisions.items() if not (isinstance(d, Mapping) and d.get("status") == "DECIDED" and d.get("chosen") in (d.get("options") or ())))


def evaluate(prov: Mapping | None = None, experiment: str | None = None) -> list[Blocker]:
    """Todos los bloqueos y avisos vigentes. Sin `prov` se evalúa el estado del CÓDIGO; con `prov` (la provenance de la campaña) también lo registrado para esa ejecución. `experiment` (por defecto el de la provenance,
    si no `oe2`) elige las dependencias de definición que cuentan (`definitions.blocked_for`): DEF no bloquea por definiciones PENDING de otros objetivos (p. ej. OE1) ni por F1 v3 (dependencia de OE5)."""
    from adaptation_swarm.baselines import conventional
    from adaptation_swarm.oe import campaign_spec, code_state, definitions as defs, http_campaign as hc, http_window, time_contract
    experiment = experiment or (prov or {}).get("experiment") or "oe2"
    out: list[Blocker] = [Blocker("DEF", "definition", True, f"definición PENDING (dependencia de {experiment}): {k}") for k in defs.blocked_for(experiment)]
    spec = campaign_spec.SPEC["oe2"]

    if time_contract.T_CONV_EQUIVALENCE == "ESTABLISHED":
        out.append(Blocker("B1", "methodological", True, "contradicción con B1: se declaró equivalencia de T_conv entre sistemas (T_CONV_EQUIVALENCE = ESTABLISHED). T_conv es SOLO de la propuesta; esa equivalencia no se establece y no desbloquea nada"))
    elif time_contract.TTFC_CONTRACT.get("status") != time_contract.APPROVED_STATUS or time_contract.VALIDATION_STATUS != "VALIDATED":
        out.append(Blocker("B1", "methodological", True, f"contrato de tiempo {time_contract.CONTRACT_VERSION} sin validar: el indicador común `{time_contract.COMMON_METRIC}` es una decisión provisional "
                           f"(estado {time_contract.TTFC_CONTRACT.get('status')}, validación {time_contract.VALIDATION_STATUS}); se resuelve con su aprobación/validación explícita, NO con equivalencia con T_conv "
                           f"({time_contract.T_CONV_EQUIVALENCE}); `decision_ms` es LEGACY; ninguno puede sustituir a T_conv en un contraste confirmatorio", frozen=True))

    policy = (prov or {}).get("persist_policy", spec["persist_policy"]["campaign"])
    b5 = persistence_decision_state(policy)
    if b5["blocking"]:
        out.append(Blocker("B5", "methodological", True, f"decisión B5-C de persistencia ({policy!r}) sin resolver: " + "; ".join(b5["reasons"]) + ". Se resuelve con su aprobación explícita (comparación OFF común aceptada, costo ON de la propuesta aparte, "
                           "sin persistencia en el baseline, L_resp aprobado intacto); no modificando L_resp ni activando persistencia en el baseline", frozen=b5["pending_approval"]))

    scope = spec.get("comparator_scope_validation", {})
    if scope.get("status") != "VALIDATED":
        out.append(Blocker("B13", "methodological", True, f"alcance del comparador pendiente de validación: solo {scope.get('implemented_conventional_systems')} implementado(s) como convencional independiente "
                           "(LMS real y LLM monolítico no implementados) y OE2 habla de «sistemas convencionales»; OE2 solo puede concluir sobre ese comparador", frozen=True))

    hw_val = spec.get("hardware_target_validation", {})
    if hw_val.get("status") != campaign_spec.APPROVED_STATUS:
        out.append(Blocker("P6", "methodological", True, f"hardware objetivo (P6) sin aprobación metodológica (estado {hw_val.get('status')}): cumplir el criterio operativo del código (`meets_target`) es solo compatibilidad técnica, "
                           "no aprobación del requisito; se resuelve con su aprobación explícita, no con el hardware medido", frozen=True))

    pending = pending_methodological_decisions()
    if pending:
        out.append(Blocker("PEND", "methodological", True, f"decisiones metodológicas de D.5 sin cerrar: {', '.join(pending)}. Se resuelven con una decisión explícita (`status = DECIDED` y `chosen` entre sus opciones); "
                           "ningún código las decide por defecto", frozen=True))

    in_request = conventional.BASELINE_REPORTS_QUALITY_IN_REQUEST
    if prov is not None and in_request is False:
        in_request = prov.get("server", {}).get("baseline_quality_in_request")                 # lo registrado para esta ejecución; no registrado = no verificado
    if in_request is not False:
        out.append(Blocker("B3", "technical", True, "medición no equivalente: la evaluación de 𝓕 de reporte del baseline se ejecuta dentro de la petición medida (o no se verificó que no lo haga)"))

    timeout = hc.CLIENT_TIMEOUT_S if prov is None else prov.get("client_timeout_s")
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        out.append(Blocker("B6", "technical", True, "timeout de cliente no configurado: una petición colgada no se detectaría como timeout"))
    elif hc.CLIENT_TIMEOUT_STATUS != "VALIDATED":
        out.append(Blocker("B6", "technical", False, f"timeout de cliente {timeout} s configurado pero {hc.CLIENT_TIMEOUT_STATUS}"))

    gp = http_window.GENERATOR_POLICY
    if not all(k in gp for k in ("threshold_percent", "on_saturation", "on_missing_cpu_samples", "level_rule", "scope")) or not isinstance(gp.get("threshold_percent"), (int, float)):
        out.append(Blocker("B7", "technical", True, "política del generador de carga no definida (umbral, acción, regla por carga y alcance)"))
    elif gp.get("status") != "VALIDATED":
        out.append(Blocker("B7", "technical", False, f"política del generador {gp['id']} definida pero {gp['status']}"))

    missing = hc.missing_run_fields()
    if missing or "inprocess_obs" not in inspect.signature(hc.analyze_records).parameters:
        out.append(Blocker("B11", "technical", True, "análisis HTTP no integrado: " + (f"faltan campos de corrida {missing}; " if missing else "") +
                           ("`analyze_records` no acepta observaciones in-process" if "inprocess_obs" not in inspect.signature(hc.analyze_records).parameters else "")))

    if prov is not None:
        if prov.get("server", {}).get("library_version_matches") is False:
            out.append(Blocker("B12", "technical", True, "la biblioteca efectiva del servidor (/health) no coincide con la registrada en la provenance"))
        gaps = code_state.provenance_gaps(prov)
        if gaps:
            out.append(Blocker("B12", "technical", True, f"provenance incompleta: faltan {gaps}"))
    return sorted(out, key=lambda b: (b.id == "DEF", b.id))


def methodological_blockers(experiment: str = "oe2") -> list[Blocker]:
    """Bloqueos METODOLÓGICOS críticos (B1, B5, B13, P6, PEND): la fuente única de autorización metodológica que usan la campaña HTTP y el runner in-process. Las definiciones (DEF) y los técnicos quedan fuera."""
    return [b for b in evaluate(None, experiment) if b.critical and b.kind == "methodological"]


def hardware_state(hw: Mapping) -> dict:
    """SEPARA la compatibilidad TÉCNICA del hardware con el criterio operativo del código de su aprobación METODOLÓGICA (P6). `environment_class` solo es OFFICIAL_TARGET si ambas se cumplen."""
    from adaptation_swarm.analysis.baseline_bruteforce import meets_target
    from adaptation_swarm.oe import campaign_spec
    status = campaign_spec.SPEC["oe2"].get("hardware_target_validation", {}).get("status")
    technical, approved = bool(meets_target(dict(hw))), status == campaign_spec.APPROVED_STATUS
    return {"technically_compatible": technical, "methodological_status": status, "methodologically_approved": approved,
            "environment_class": "OFFICIAL_TARGET" if technical and approved else ("TECHNICALLY_COMPATIBLE_P6_PENDING" if technical else "PILOT")}


def critical_reasons(prov: Mapping | None = None) -> list[str]:
    return [str(b) for b in evaluate(prov) if b.critical]


def warnings(prov: Mapping | None = None) -> list[str]:
    return [str(b) for b in evaluate(prov) if not b.critical]
