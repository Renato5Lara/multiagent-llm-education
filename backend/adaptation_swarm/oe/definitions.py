"""Registro de definiciones operacionales de OE1–OE5 con su ESTADO y su fuente. Regla: si una definición ya está aprobada (asesoría, DECISION-CLOSURE, MASTER-SPEC, addenda del asesor) se reutiliza TAL CUAL; si no
existe, el punto queda `PENDING` (definición pendiente) y ningún módulo la inventa ni la usa para declarar un resultado oficial. Los manifiestos de las corridas incluyen este registro.

Fuentes (carpeta de documentos de tesis, fuera del repositorio): MS = MASTER-SPEC-2026-09-23.md · DC = DECISION-CLOSURE-2026-09-23.md · AD = ADDENDUM-DECISIONES-ASESOR-2026-09-2x.md.
"""

from __future__ import annotations

from adaptation_swarm.gold import rubric_v2, rubric_v3
from adaptation_swarm.pso.space import MODALITIES

APPROVED, PARTIAL, PENDING = "APPROVED", "PARTIAL", "PENDING"
SUPERSEDED = "SUPERSEDED"      # definición retirada por una decisión posterior: ya no es dependencia de ningún objetivo ni se reutiliza
REQUIREMENTS_VERSION = "RF01-RF06+RNF01-RNF05 (MS §RF/RNF, 2026-09-23) + REL-C/REL-D (oe1, propias de este estudio)"

DEFINITIONS: dict[str, dict] = {
    "t_conv": {"status": APPROVED, "source": "DC DEC-10; MS (VD dimensión «Eficiencia T_conv»)", "definition": "T_conv se reporta en iteraciones (k_stop) y en milisegundos (t_convergencia − t_inicio_búsqueda); regla de parada |ΔF|<ε o k_max=15",
               "note": "T_conv es SOLO de la propuesta. No se extiende a los sistemas convencionales ni se declara equivalente entre sistemas (decisión B1, D.3, provisional): el tiempo comparable entre sistemas es el indicador operacional separado `common_time_indicator_oe2` (`time_to_final_config_ms`)."},
    "t_conv_baselines": {"status": SUPERSEDED, "source": "—; reemplazada por la decisión B1-B (Fase D.3, provisional, no aprobada por el asesor)",
                         "definition": "RETIRADA: la idea de equiparar un «tiempo de convergencia» de los sistemas convencionales con T_conv de la propuesta NO se establece (los convencionales no iteran ni tienen criterio |ΔF|<ε)",
                         "note": "su lugar lo ocupa `common_time_indicator_oe2` (indicador operacional separado, no T_conv). Se conserva la clave solo para trazabilidad; no es dependencia de ningún objetivo."},
    "common_time_indicator_oe2": {"status": PENDING, "source": "Fase D.3 (decisión B1-B provisional del tesista; NO aprobada por el asesor)",
                                  "definition": "`time_to_final_config_ms`: tiempo hasta obtener la configuración final S (perfil validado → S decidida; sin ensamblado, HTTP ni persistencia), condición aislada en proceso, ambos sistemas (oe/time_contract.py `TTFC_CONTRACT`)",
                                  "note": "indicador operacional SEPARADO: no es T_conv ni se le asigna equivalencia; su validación metodológica sigue pendiente"},
    "latency_l_resp": {"status": APPROVED, "source": "DC §9.2", "definition": "L_resp = petición HTTP → último byte del JSON con el paquete (incluye RF01, AG1, PSO, Redis, ensamblado y persistencia síncrona mínima; excluye descarga de audio y persistencia asíncrona); P95 con ≤ 25 usuarios",
                       "note": "La latencia EN PROCESO del ejecutor `oe/runner.py` es un sustituto exploratorio, no L_resp; la medición HTTP es Locust/JMeter en el hardware objetivo."},
    "throughput": {"status": PARTIAL, "source": "RNF04 (MS): ≥ 20 req/s con error < 1 %; DC §9.2", "definition": "peticiones correctas por segundo",
                   "note": "El cálculo por lote (n_ok / tiempo de pared del lote, bucle cerrado sin espera) es operativo de este estudio."},
    "quality_f1_adapt": {"definition_version": "v2", "status": APPROVED, "source": "AD 2026-09-26 (P1, P2, P3, R1–R3); MS §F1 vigente desde 26/09", "definition": "F1_i = 2|G_i ∩ P_i|/(|G_i|+|P_i|), P_i = {m : e_m ≥ 1}; por réplica = media de 100 casos; IC95 t sobre K=10",
                         "note": "La regla completa (`full_rule_version`) NO está sellada: pre-registro v3 con 8 campos PENDING_ADVISOR."},
    "usability_sus": {"status": APPROVED, "source": "Asesoría §4.4/§4.5; AD D7/D8", "definition": "SUS 0–100, n ≥ 10, media > 75, Shapiro → t/Wilcoxon contra 75", "note": "versión española publicada del SUS por citar (P7)"},
    "reference_value_75": {"status": APPROVED, "source": "Asesoría §4.4; OE5 aprobado", "definition": "valor de referencia SUS = 75 puntos", "note": ""},
    "statistical_unit_f1": {"status": APPROVED, "source": "AD 2026-09-26 R2", "definition": "la unidad es el perfil: sus F1 de las K réplicas se promedian; la inferencia usa los 100 promedios", "note": ""},
    "statistical_unit_performance": {"status": PENDING, "source": "—; decisión técnica provisional D.3/D.4.1 (no aprobada por el asesor)",
                                     "definition": ("unidad estadística de OE2 por indicador: L_resp = P95 por CORRIDA HTTP; throughput = por CORRIDA HTTP; time_to_final_config_ms = PERFIL (media de las K réplicas), pareado swarm vs baseline, solo condición aislada in-process; "
                                                    "T_conv = solo descriptivo de la propuesta (no se contrasta entre sistemas ni es comparable). Una petición HTTP o una réplica nunca es una observación independiente. OE3/OE4: corrida (campaign_spec)"),
                                     "note": ("coincide con `campaign_spec.oe2.design` y `oe2_confirmatory`; la unidad estadística DEFINITIVA de OE2 sigue PENDING y requiere respaldo del asesor. Pareamiento HTTP, `m` de Holm, errores/timeouts y cold/warm "
                                              "tienen decisión INTERNA de estudio (F.2.3, no aprobada por el asesor); siguen pendientes el estadístico de latencia (P95 vs media) y la hipótesis de H1 con el L_resp literal")},
    "replicate": {"status": PARTIAL, "source": "AD D5 (K=10 réplicas con semillas independientes, para F1)", "definition": "réplica = repetición del perfil con semilla derivada derive_seed(batch_seed, profile_id, replicate)", "note": "su uso en OE2–OE4 (K ≥ 10) es operativo"},
    "efficiency_of_adaptation_oe3": {"status": PARTIAL, "source": "MS (VD dimensión «Eficiencia T_conv»)", "definition": "indicador de eficiencia aprobado = T_conv",
                                     "note": "Se reportan además k_stop, mensajes y brecha al óptimo como indicadores COMPLEMENTARIOS; no existe un índice compuesto aprobado y no se inventa uno."},
    "compliance_score_oe1": {"status": PENDING, "source": "—", "definition": "puntaje de cumplimiento de requisitos", "note": "no existe definición aprobada de cómo agregar RF/RNF en un puntaje; OE1_COMPLIANCE_SCORE = BLOCKED_DEFINITION"},
    "reliability_oe1": {"status": PENDING, "source": "—", "definition": "indicador de confiabilidad", "note": "CR (DC DEC-10) es tasa de convergencia por ε, no confiabilidad; REL-C/REL-D son propuestas propias por confirmar"},
    "conventional_system_oe2": {"status": PARTIAL, "source": "AD 2026-09-25 D11c (línea base fuerza bruta frente a PSO); AD 2026-09-26 D11c (¿reemplaza o complementa el benchmark §2.1 LMS/reglas/LLM?: pregunta abierta al asesor)",
                                "definition": "`bruteforce` aprobado como línea base empírica; `rules` (reglas fijas) corresponde a la categoría «motores basados en reglas» (MS §comparadores) pero su definición empírica es de este estudio",
                                "note": "LMS tradicional y LLM monolítico NO están implementados ni medidos. En el diseño experimental de OE2 (D.3, provisional): el único baseline convencional es `decision_table`; `rules` = ablación del enjambre y `bruteforce` = óptimo de referencia, no convencionales."},
    "precision_multimodal_oe5": {"definition_version": "v3", "status": PARTIAL, "source": "AD 2026-09-26 (F1 4×4 con audio, gold por arquetipo)", "definition": "F1_adapt de la regla v3", "note": "regla completa sin sellar (P4 `panel_protocol_version` PENDING_ADVISOR)"},
}


# ── F1_adapt VERSIONADO ────────────────────────────────────────────────────────────────────────────────────────────
# `DEFINITIONS["quality_f1_adapt"]` (clave histórica, sin cambios de contenido) ES la definición v2. Las dos definiciones conviven aquí con su estado; ninguna reemplaza a la otra y no hay fallback entre ellas.
# Los valores de v2 y v3 se DERIVAN de `rubric_v2` / `rubric_v3` (no se copian a mano) para que no puedan divergir del código que evalúa.
F1_V2, F1_V3 = "v2", "v3"
STATUS_F1_V2 = "HISTORICAL_OFFICIAL_V2"
STATUS_F1_V3 = "PROVISIONAL_NOT_APPROVED"


def _ordered_gold(expected_by_archetype) -> dict[str, list[str]]:
    return {a.value: [m for m in MODALITIES if m in s] for a, s in expected_by_archetype.items()}


_V3_INCL = rubric_v3.INCLUSION_RULES[rubric_v3.INCLUSION_RULE_ID]

F1_DEFINITION_VERSIONS: dict[str, dict] = {
    F1_V2: {
        "definition_version": F1_V2, "status": STATUS_F1_V2, "official": True,
        "formula": "P_i = {m : e_m ≥ 1}", "inclusion_rule_id": "incl-ge1", "inclusion_integer_form": "e_m >= 1",
        "gold_rule_version": "gold-v2-cand-A", "rule_version": rubric_v2.get_rule("gold-v2-cand-A", "incl-ge1").rule_version,
        "gold_expected_by_archetype": _ordered_gold(rubric_v2.GOLD_RULES["gold-v2-cand-A"].expected_by_archetype),
        "associated_runs": ["official_runs/k10_official_2026-09-27 (K10 v2, F1 medio 0.6407)"],
        "source": "AD 2026-09-26 (P1, P2); MS §F1 «vigente desde 26/09»; DECISION-REGISTER DEC-2609-INCL (CLOSED)",
        "approved_in": "rubric_v2.APPROVED_RULE_VERSIONS", "full_rule_version": "gold-v2-cand-A+incl-ge1+samples+panel-arq-ac1-maj-tie0-v2",
        "panel_protocol_version": rubric_v2.PANEL_PROTOCOL_VERSION,
    },
    F1_V3: {
        "definition_version": F1_V3, "status": STATUS_F1_V3, "official": False,
        "formula": "S = {m | e_m ≥ 1 ∧ e_m/Σe ≥ 0.20}", "inclusion_rule_id": rubric_v3.INCLUSION_RULE_ID,
        "inclusion_integer_form": f"{_V3_INCL.share_den}*e_m >= " + (f"{_V3_INCL.share_num}*" if _V3_INCL.share_num != 1 else "") + "sum(e)",
        "min_emphasis": _V3_INCL.min_emphasis, "share": f"{_V3_INCL.share_num}/{_V3_INCL.share_den}", "empty_total": "sum(e) = 0 => S = vacío (F1 = 0)",
        "gold_rule_version": rubric_v3.GOLD_RULE_VERSION, "rule_version": rubric_v3.RULE_VERSION,
        "gold_expected_by_archetype": _ordered_gold(rubric_v3.GOLD_RULES[rubric_v3.GOLD_RULE_VERSION].expected_by_archetype),
        "associated_runs": [],
        "source": "ESPECIFICACION-METODOLOGICA-P1-P2-2026-09-28.md §3–§4 (decisión del asesor del 28/09 comunicada por el tesista; sin original anexado)",
        "approved_in": None, "approved": False, "full_rule_version": None, "panel_protocol_version": None,
        "pending": ["full_rule_version", "panel_protocol_version", "aprobación en rubric_v3.APPROVED_RULE_VERSIONS", "sellado del pre-registro v3"],
    },
}
assert F1_DEFINITION_VERSIONS[F1_V3]["inclusion_integer_form"] == "5*e_m >= sum(e)"      # 5·e_m ≥ Σe (comparación entera exacta de rubric_v3)


def f1_definition(version: str | None = None) -> dict:
    """Definición F1 de la versión pedida. `version=None` = la clave HISTÓRICA `quality_f1_adapt` ⇒ v2 (compatibilidad; documentado). Una versión explícita se devuelve tal cual: «v3» devuelve v3 y una versión
    desconocida lanza `KeyError`; nunca se sustituye una versión por otra."""
    key = F1_V2 if version is None else version
    try:
        return F1_DEFINITION_VERSIONS[key]
    except KeyError:
        raise KeyError(f"versión de la definición F1 no registrada: {version!r}; registradas: {sorted(F1_DEFINITION_VERSIONS)}") from None


def f1_selection_record(version: str | None) -> dict:
    """Lo que una corrida registra en su provenance sobre la definición F1: la versión SELECCIONADA explícitamente y su estado, o `selected = None` si la corrida no usa F1 (el ejecutor `oe/runner.py` no calcula F1)."""
    if version is None:
        return {"selected": None, "note": "no se seleccionó ninguna versión: este ejecutor no calcula F1; la clave histórica `quality_f1_adapt` del registro es v2", "available": sorted(F1_DEFINITION_VERSIONS)}
    d = f1_definition(version)
    return {"selected": version, "status": d["status"], "official": d["official"], "formula": d["formula"], "rule_version": d["rule_version"], "full_rule_version": d["full_rule_version"],
            "panel_protocol_version": d["panel_protocol_version"]}


# Dependencias de DEFINICIÓN de cada objetivo (dependency-aware): una definición PENDING bloquea SOLO a los objetivos que la necesitan; las de otro objetivo no cuentan. Las demás dependencias de OE2
# (alcance del comparador, persistencia/L_resp, provenance, esquema de corrida) las evalúan sus propios guards (`oe/campaign_guards.py`: B13, B5, B12, B11).
OE_DEFINITION_DEPENDENCIES: dict[str, list[str]] = {
    "oe1": ["compliance_score_oe1", "reliability_oe1"],
    "oe2": ["t_conv", "common_time_indicator_oe2", "statistical_unit_performance", "latency_l_resp", "throughput", "conventional_system_oe2"],
    "oe3": ["statistical_unit_performance", "t_conv", "efficiency_of_adaptation_oe3"],
    "oe4": ["statistical_unit_performance", "t_conv", "latency_l_resp", "throughput"],
    "oe5": ["quality_f1_adapt", "statistical_unit_f1", "usability_sus", "reference_value_75"],
}
_RESOLVED = (APPROVED, PARTIAL)


def blocked_for(experiment: str) -> list[str]:
    """Dependencias de definición de `experiment` NO resueltas. FALLA CERRADO: una dependencia PENDING, de estado desconocido o no registrada bloquea; un experimento desconocido bloquea. No mira texto libre."""
    deps = OE_DEFINITION_DEPENDENCIES.get(experiment)
    if deps is None:
        return [f"<experimento desconocido: {experiment!r}>"]
    out = []
    for k in deps:
        d = DEFINITIONS.get(k)
        if d is None:
            out.append(f"{k} (no registrada)")
        elif d.get("status") not in _RESOLVED:
            out.append(k)
    return out
