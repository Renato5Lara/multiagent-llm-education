"""Especificación experimental INTERNA de las campañas oficiales OE1–OE5 (pre-registro técnico). Fija, ANTES de ejecutar, comparador, pruebas, α, familias de Holm, unidades estadísticas, tamaños de muestra,
agregación, umbrales, exclusiones y versiones de definiciones. NO cambia objetivos, hipótesis, variables ni indicadores: solo operacionaliza.

ESTADO: «decisión técnica interna + justificación metodológica». NINGUNA entrada está «APROBADA POR EL ASESOR» (no existe aprobación explícita): `advisor_approved` es False en todas y `open_blockers()` enumera lo
que impide una campaña oficial. El hash de la especificación (`spec_hash`) se registra en el provenance de cada corrida: cambiarla después de ver datos cambia el hash y queda a la vista.
"""

from __future__ import annotations

import hashlib
import json

from adaptation_swarm.oe import http_window, profile_sequence, time_contract

SPEC_VERSION = "oe-campaign-spec-v1"

# Condiciones de PERSISTENCIA de OE2 (D.3, decisión B5-C congelada de forma provisional; no aprobada por el asesor). Una corrida pertenece a UNA sola condición y su rol queda registrado:
APPROVED_STATUS = "ADVISOR_APPROVED"                  # estado explícito de aprobación de una decisión (B5-C: `oe2.persist_policy.status`); hoy NINGUNA lo tiene
COMPARISON_PERSISTENCE = "off"                         # condición COMÚN del contraste swarm-vs-decision_table (el baseline nunca persiste). NO es literalmente el L_resp aprobado (que incluye la persistencia síncrona mínima)
PROPOSAL_COST_PERSISTENCE = "on"                       # medición COMPLEMENTARIA de la propuesta (L_resp literal, con persistencia síncrona mínima); NUNCA entra al contraste contra decision_table
ROLE_CONTRAST = "swarm_vs_decision_table_contrast"     # corrida del contraste primario (persistencia común OFF)
ROLE_AUXILIARY = "auxiliary_contrast"                  # rules / bruteforce (persistencia OFF; contrastes auxiliares descriptivos)
ROLE_PROPOSAL_COST = "proposal_persistence_cost"       # propuesta con persistencia ON: costo de la persistencia, fuera del contraste
CONTRAST_ROLES = (ROLE_CONTRAST, ROLE_AUXILIARY)
STATUS = "TECHNICAL_INTERNAL_DECISION_NOT_ADVISOR_APPROVED"

SPEC: dict = {
    "version": SPEC_VERSION, "status": STATUS, "advisor_approved": False,
    "alpha": 0.05, "multiplicity": "Holm dentro de cada familia confirmatoria (abajo); sin corrección entre familias",
    "unit_rule": "dato crudo ≠ dato agregado ≠ unidad de inferencia; ninguna petición/caso/réplica interna se usa como observación independiente",
    "oe2": {
        "proposal_system": "swarm", "conventional_system": "decision_table", "comparator_primary": "decision_table", "comparator_fixed_before_data": True,
        "system_roles": {"swarm": "proposal", "decision_table": "conventional_independent", "rules": "swarm_heuristic_ablation", "bruteforce": "reference_optimum"},
        "auxiliary_contrasts": ["rules", "bruteforce"],
        "scope": {"proposal": "swarm", "conventional_baseline": "decision_table", "additional_conventional_systems": [], "reference_optimum": "bruteforce", "swarm_ablation": "rules",
                  "status": "FROZEN_PROVISIONAL_NOT_ADVISOR_APPROVED", "oe2_text_modified": False,
                  "statement": "propuesta basada en inteligencia de enjambre vs baseline convencional `decision_table` (definido operacionalmente en este estudio)",
                  "generalization_limit": "los resultados NO permiten generalizar a todos los sistemas convencionales existentes (LMS reales, motores de reglas externos, LLM monolíticos); solo valen frente a `decision_table`"},
        "comparator_note": ("decision_table = tabla de decisión estática independiente del enjambre (baselines/decision_table.py): decisión técnica interna de este estudio. NO es un LMS real ni un LLM monolítico (no implementados): "
                            "las conclusiones de OE2 se limitan a este comparador. rules (ablación del enjambre) y bruteforce (óptimo de referencia, D11c) NO son comparadores convencionales: son contrastes auxiliares."),
        "time_contract": {"version": time_contract.CONTRACT_VERSION, "status": time_contract.STATUS, "candidate_common_metric": time_contract.COMMON_METRIC, "validation": time_contract.VALIDATION_STATUS,
                          "t_conv_equivalence": time_contract.T_CONV_EQUIVALENCE, "definitions": time_contract.DEFINITIONS,
                          "common_indicator": time_contract.TTFC_CONTRACT, "legacy_metric": {"name": time_contract.LEGACY_METRIC, "status": time_contract.LEGACY_STATUS},
                          "t_conv_scope": "T_conv es SOLO de la propuesta (definición DEC-10 intacta); el indicador común no es T_conv",
                          "known_limits": list(time_contract.KNOWN_LIMITS)},
        "design": {"profiles_min": 30, "replicates_per_profile_min": 10, "systems": ["swarm", "decision_table"], "auxiliary_systems_optional": ["rules", "bruteforce"],
                   "unit_common_time_indicator_and_latency": "profile (media de K réplicas), pareado (time_to_final_config_ms in-process aislado, exploratorio mientras su validación esté pendiente); L_resp y throughput: corrida HTTP",
                   "unit_throughput": "run (corrida/lote HTTP independiente)", "throughput_runs_per_system_min": 10, "stationary_window_s_min": 60, "warmup_s_min": 10},
        "profile_sequence": {"algorithm": profile_sequence.ALGORITHM, "depends_only_on": ["batch_seed", "worker_index", "user_index", "seq_pos"], "same_sequence_for_all_systems": True,
                             "recorded": "hash de la secuencia esperada en plan/provenance y (user_index, seq_pos, profile_id) por petición en el log HTTP; `profile_sequence_check.mismatches` debe ser 0"},
        "comparator_scope_validation": {"status": "PENDING_METHODOLOGICAL_VALIDATION", "implemented_conventional_systems": ["decision_table"], "oe2_text_requires": "sistemas convencionales (plural)",
                                        "note": "no se implementa un LMS/LLM para satisfacer el plural; alcance = decision_table como baseline convencional operacional (decisión B13-A provisional, no aprobada por el asesor: la validación metodológica sigue PENDING)",
                                        "decision": "B13-A (provisional)"},
        "measurement": {"regions": time_contract.MEASUREMENT_REGIONS, "baseline_quality_in_request": False},
        "client_timeout": {"seconds": 30.0, "status": "PROVISIONAL_TECHNICAL", "same_for_all_systems": True, "recorded_in": "provenance.client_timeout_s y cada registro de corrida",
                           "note": "constante de campaña provisional (≫ 2 s del umbral de L_resp); no es un valor metodológico aprobado"},
        "generator_policy": http_window.GENERATOR_POLICY,
        "persist_policy": {"campaign": COMPARISON_PERSISTENCE, "applies_to": "swarm y decision_table por igual en el CONTRASTE (SWARM_API_PERSIST=0 en el servidor; el baseline nunca persiste)",
                           "on_supported_for_comparison": False, "verified_via": "GET /api/adaptation/health → persist_policy; campo `persistence` de cada respuesta",
                           "comparison_persistence": COMPARISON_PERSISTENCE, "proposal_persistence_cost": PROPOSAL_COST_PERSISTENCE, "status": "FROZEN_PROVISIONAL_NOT_ADVISOR_APPROVED",
                           "roles": {"comparison": ROLE_CONTRAST, "auxiliary": ROLE_AUXILIARY, "proposal_cost": ROLE_PROPOSAL_COST},
                           "comparison_off_is_literal_l_resp": False, "proposal_on_is_literal_l_resp": True, "artificial_persistence_in_baseline": False,
                           "isolation_rule": "una corrida ON de la propuesta NO entra al contraste swarm-vs-decision_table (oe2_confirmatory la excluye y la reporta aparte); L_resp aprobada no se redefine",
                           "note": "la comparación OFF común NO es literalmente el L_resp aprobado (incluye persistencia síncrona mínima); el costo de esa persistencia se mide en la propuesta con la condición ON"},
        "isolation": {"redis": "namespace de campaña `oe2c:<campaign_id>:` + eliminación verificada de las claves por ciclo antes de cada corrida (oe/run_isolation.py); streams de agentes intactos", "postgresql": "las corridas ON se etiquetan con `SWARM_API_RUN_LABEL`",
                      "pending": "política cold/warm de cachés en memoria del servidor (el proceso no se reinicia entre corridas del mismo N y persistencia): decisión metodológica PENDIENTE"},
        # Decisiones metodológicas que D.5 deja SIN CERRAR. Aquí solo se REPRESENTAN (opciones y estado): ningún módulo de análisis lee `chosen`. Una decisión se resuelve únicamente con `status == DECIDED` y `chosen` ∈ `options`
        # (decisión explícita del responsable del estudio, con respaldo del asesor cuando corresponda: `advisor_backing` NO está determinado). El guard `PEND` bloquea la campaña oficial mientras alguna siga PENDING.
        "methodological_decisions": {
            "http_pairing": {"status": "PENDING", "chosen": None, "options": ["independent_runs", "paired_by_run_index_and_load", "paired_by_profile"], "source": "D.5 decisión 1", "implemented_today": "independent_runs"},
            "holm_family_size": {"status": "PENDING", "chosen": None, "options": ["fixed_m_declared_before_data", "dynamic_m", "other"], "source": "D.5 decisión 2", "implemented_today": "dynamic_m", "advisor_backing": "NO DETERMINABLE: la tesis prevé Holm en OE3/OE4, no en OE2"},
            "errors_timeouts_in_l_resp": {"status": "PENDING", "chosen": None, "options": ["exclude_with_validity_rule", "penalize", "separate_indicators"], "source": "D.5 decisión 3", "implemented_today": "p95_of_successful_requests_errors_counted_apart"},
            "l_resp_literal_hypothesis_h1": {"status": "PENDING", "chosen": None, "options": ["not_part_of_oe2", "descriptive_only", "confirmatory_contrast"], "source": "D.5 decisión 4", "implemented_today": "descriptive_only"},
            "cold_warm_policy": {"status": "PENDING", "chosen": None, "options": ["cold_per_run", "controlled_warm", "mixed_registered"], "source": "D.5 decisión 5", "implemented_today": "mixed_registered_implicit"},
            "common_indicator_asymmetry": {"status": "PENDING", "chosen": None, "options": ["keep_documented", "extend_baseline", "reduce_swarm_scope", "drop_common_indicator", "use_total_ms"], "source": "D.5 decisión 6", "implemented_today": "keep_documented"},
            "latency_statistic": {"status": "PENDING", "chosen": None, "options": ["p95", "mean"], "source": "D11b (addendum 26/09): P95 o media pendiente del asesor", "implemented_today": "p95"},
            "execution_order": {"status": "PENDING", "chosen": None, "options": ["sequential", "randomized_blocks"], "source": "tesis 01/10: aleatorización «pendiente de decisión»", "implemented_today": "randomized_blocks_default"},
        },
        "pending_methodological_decisions": [
            "pareamiento del contraste HTTP: corridas independientes (hoy) vs pareadas por índice de corrida (misma semilla y secuencia)",
            "tamaño `m` de la familia de Holm: hoy cuenta solo las hipótesis testables; no está fijado antes de ver datos",
            "tratamiento de errores y timeouts en el estimando de L_resp: hoy P95 solo de las peticiones correctas (posible sesgo de supervivencia)",
            "hipótesis estadística de H1 con el L_resp literal (condición ON de la propuesta): hoy solo descriptiva",
            "política cold/warm de cachés del servidor entre corridas",
            "asimetría del indicador común: obtención/evaluación de artefactos candidatos dentro del swarm y fuera del convencional",
            "aprobación del asesor de B1 (indicador común), B5-C (persistencia) y B13 (alcance)",
        ],
        "latency": {"official": "HTTP extremo a extremo", "indicator": "P95 por corrida", "also_reported": ["p50", "mean"], "contrast_regime_max_users": 25,
                    "stress_regime": "> 25 usuarios: estrés; no contrasta el umbral de 2 s", "threshold_ms": 2000},
        "throughput": {"official": "HTTP, peticiones correctas/s en ventana estacionaria", "rnf04": {"min_rps": 20.0, "max_error": 0.01}, "pilot_rps_not_official": "≈10–12 req/s (piloto in-process): diagnóstico",
                       "record": ["requests_total", "requests_ok", "errors", "timeouts", "duration_s", "throughput_rps", "users", "load_generator_cpu_percent"]},
        "tests": {"paired": "Shapiro-Wilk sobre diferencias → t pareada sobre log(tiempo) si razonable; si no Wilcoxon signed-rank", "independent_runs": "Shapiro-Wilk → Welch / Mann-Whitney",
                  "delta": "swarm − conventional", "report": ["effect", "ci95", "difference", "p", "n_effective"]},
        "holm_family": "primary:swarm_vs_decision_table = {L_resp P95 HTTP, throughput HTTP} × cargas de contraste (≤ 25 usuarios); el indicador común time_to_final_config_ms (decisión provisional, validación PENDIENTE; condición aislada) y el legacy decision_ms se calculan aparte como exploratorios y quedan FUERA de Holm; la condición ON de la propuesta no entra al contraste; auxiliary:swarm_vs_rules y auxiliary:swarm_vs_bruteforce = familias propias, descriptivas (no son comparadores convencionales)",
    },
    "oe3": {
        "design": "factorial completo 2×2×2×2×3 = 48 celdas con los factores/niveles de conditions.py (heuristic_seed, replicas, dispatch, broadcast_gbest, mechanism)", "ofat_role": "piloto/cribado/validación del pipeline (no evidencia confirmatoria)",
        "runs_per_cell_min": 10, "seed_per_batch": True, "unit": "corrida agregada sobre sus perfiles", "primary": "t_conv_ms", "secondary": ["k_stop", "n_messages", "gap_vs_optimum"],
        "quality_context": "F (sin índice compuesto de «eficiencia»)", "tests": "ANOVA factorial con todas las interacciones sobre log(T_conv); si residuos no normales: permutación (Freedman–Lane)",
        "reading_rule": "con interacción significativa, efectos principales condicionales", "holm_family": "términos del ANOVA de T_conv (31)",
    },
    "oe4": {
        "design": "carga {1,5,10,25,50,100} × N {10,20,30}; ≥10 corridas por celda; unidad = corrida", "load_meaning": "concurrency = usuarios virtuales en bucle cerrado sin espera (conditions.py/runner.py)",
        "official_latency": "HTTP P95 por corrida", "official_throughput": "HTTP", "throughput_internal": "campo separado `throughput_internal_rps` (diagnóstico)",
        "contrast_regime_max_users": 25, "stress_users": [50, 100], "warmup_s_min": 10, "stationary_window_s_min": 60, "monitor": "CPU del generador de carga",
        "tests": "ANOVA 2 vías sobre log de métricas positivas; alternativas Kruskal-Wallis/ART/permutación; post hoc Tukey/Holm; Spearman carga–latencia (tendencia)",
    },
    "oe1": {
        "compliance_score": "por requisito: 1 / 0.5 (solo si el criterio de aceptación existente define parcial) / 0; no evaluado excluido del denominador; media de las 4 dimensiones",
        "reliability_oe1": "proporción de peticiones con salida válida (esquema válido, sin error, sin timeout); IC de Wilson; NO es CR; sin MTBF; determinismo = evidencia separada",
        "circularity_rule": "F1 no entra en el compliance que se correlaciona con F1", "unit": "corrida", "test": "Spearman (Kendall alternativa); si compliance es constante → descriptivo",
    },
    "oe5": {
        "f1": {"v2": "histórica/certificada, intocable", "v3": "5·e_m ≥ Σe, e_m ≥ 1; oficial solo tras sellar full_rule_version + panel P4 + hash + fecha", "no_silent_fallback": True},
        "k10": "K = 10 réplicas de la evaluación de F1 (replicas.py / replicas_v3.py); NO es un indicador del panel ni de precisión nuevo",
        "panel": "juicio humano de adecuación, separado de F1; P4 congelado antes de convocar",
        "sus": {"n_min": 10, "reference": 75.0, "rule": "media > 75 NO basta; confirmatorio si el límite inferior del IC95 % > 75", "tests": "Shapiro-Wilk → t de una muestra / Wilcoxon"},
    },
    "h1": {"conjunctive": True, "components": {"f1_adapt": "≥ 0.85", "latency_p95_s": "< 2.0 (≤ 25 usuarios, HTTP)", "sus": "> 75"}, "decision": "H1 solo se declara si se cumplen los TRES"},
    "exclusions": "peticiones fallidas se reportan como error y no entran a métricas de tiempo/calidad; ninguna corrida se excluye post hoc; las excluidas por criterio pre-declarado (hardware, generador saturado) se listan",
}


def _canonical() -> bytes:
    return json.dumps(SPEC, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def spec_hash() -> str:
    return hashlib.sha256(_canonical()).hexdigest()


def identity() -> dict:
    return {"version": SPEC_VERSION, "status": STATUS, "advisor_approved": False, "sha256": spec_hash()}


def open_blockers() -> list[str]:
    """Condiciones de la campaña oficial que HOY no se cumplen, CALCULADAS del estado real (`campaign_guards.evaluate`): un bloqueo desaparece solo si cambia el estado que lo origina, no si se edita un texto."""
    from adaptation_swarm.oe import campaign_guards
    return campaign_guards.critical_reasons(None)
