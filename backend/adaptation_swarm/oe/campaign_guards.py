"""Guards de campaña OE2 DINÁMICOS: cada bloqueo se CALCULA del estado real (constantes de contrato, registro de definiciones, esquema de registros, política de persistencia, provenance), no de un texto fijo.
Modificar un mensaje no desbloquea nada: para desbloquear hay que cambiar el estado que lo origina (p. ej. que el contrato de tiempo pase a VALIDATED, o que la definición de L_resp y la política de persistencia sean
compatibles). Ningún guard decide cuestiones metodológicas: los marcados `frozen` (B1, B5, B13) solo REPRESENTAN la decisión pendiente.

    B1   contrato de tiempo: equivalencia `decision_ms`/T_conv NOT_ESTABLISHED                        (metodológico, congelado)
    B3   la evaluación de 𝓕 de reporte del baseline corre dentro de la petición medida                (técnico)
    B5   política de persistencia incompatible con la definición aprobada de L_resp                    (metodológico, congelado)
    B6   timeout de cliente no configurado (provisional = aviso no crítico)                             (técnico)
    B7   política del generador de carga no definida                                                    (técnico)
    B11  esquema de corrida/análisis HTTP sin integrar (campos requeridos, `inprocess_obs`)            (técnico)
    B12  provenance incompleta (solo con provenance)                                                    (técnico)
    B13  alcance del comparador pendiente de validación (OE2 dice «sistemas convencionales»)           (metodológico, congelado)
    DEF  definiciones PENDING y F1 v3 sin sellar                                                        (definición)
"""

from __future__ import annotations

import inspect
import re
from dataclasses import asdict, dataclass
from typing import Mapping

REQUIRED_RUN_FIELDS = (
    "campaign_id", "system", "system_role", "run_id", "batch_seed", "profile_sequence_hash", "load", "users", "warmup_seconds", "persist_policy", "p95_latency_ms", "throughput_http",
    "error_count", "timeout_count", "decision_ms_mean", "decision_ms_median", "decision_ms_p95", "t_conv_ms_mean", "metric_validation_status", "comparable", "client_timeout_s", "official", "oe2_official",
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


def evaluate(prov: Mapping | None = None) -> list[Blocker]:
    """Todos los bloqueos y avisos vigentes. Sin `prov` se evalúa el estado del CÓDIGO; con `prov` (la provenance de la campaña) también lo registrado para esa ejecución."""
    from adaptation_swarm.baselines import conventional
    from adaptation_swarm.gold import rubric_v3
    from adaptation_swarm.oe import campaign_spec, code_state, definitions as defs, http_campaign as hc, http_window, time_contract
    out: list[Blocker] = [Blocker("DEF", "definition", True, f"definición PENDING: {k}") for k, v in defs.DEFINITIONS.items() if v["status"] == defs.PENDING]
    if not rubric_v3.APPROVED_RULE_VERSIONS:
        out.append(Blocker("DEF", "definition", True, "F1 v3 sin sellar (rubric_v3.APPROVED_RULE_VERSIONS vacío; PENDING_ADVISOR en el pre-registro v3)"))
    spec = campaign_spec.SPEC["oe2"]

    if time_contract.T_CONV_EQUIVALENCE != "ESTABLISHED" or time_contract.VALIDATION_STATUS != "VALIDATED":
        out.append(Blocker("B1", "methodological", True, f"contrato de tiempo {time_contract.CONTRACT_VERSION} sin validar: la equivalencia metodológica entre `decision_ms` y el T_conv de la propuesta "
                           f"({time_contract.T_CONV_EQUIVALENCE}, validación {time_contract.VALIDATION_STATUS}) no está establecida; decision_ms no puede sustituir a T_conv en ningún contraste confirmatorio", frozen=True))

    policy = (prov or {}).get("persist_policy", spec["persist_policy"]["campaign"])
    ps = persistence_status(policy)
    if ps["status"] != "COMPATIBLE":
        out.append(Blocker("B5", "methodological", True, f"política de persistencia {policy!r}: {ps['status']} (la definición vigente de L_resp {'incluye' if ps['l_resp_definition_requires_sync_persistence'] else 'no incluye'} "
                           "la persistencia síncrona mínima; el baseline " + ("soporta" if ps["baseline_supports_persistence"] else "no soporta") + " persistencia); decisión metodológica pendiente", frozen=True))

    scope = spec.get("comparator_scope_validation", {})
    if scope.get("status") != "VALIDATED":
        out.append(Blocker("B13", "methodological", True, f"alcance del comparador pendiente de validación: solo {scope.get('implemented_conventional_systems')} implementado(s) como convencional independiente "
                           "(LMS real y LLM monolítico no implementados) y OE2 habla de «sistemas convencionales»; OE2 solo puede concluir sobre ese comparador", frozen=True))

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


def critical_reasons(prov: Mapping | None = None) -> list[str]:
    return [str(b) for b in evaluate(prov) if b.critical]


def warnings(prov: Mapping | None = None) -> list[str]:
    return [str(b) for b in evaluate(prov) if not b.critical]
