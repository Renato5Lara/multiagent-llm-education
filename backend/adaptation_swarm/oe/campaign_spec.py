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
STATUS = "TECHNICAL_INTERNAL_DECISION_NOT_ADVISOR_APPROVED"

SPEC: dict = {
    "version": SPEC_VERSION, "status": STATUS, "advisor_approved": False,
    "alpha": 0.05, "multiplicity": "Holm dentro de cada familia confirmatoria (abajo); sin corrección entre familias",
    "unit_rule": "dato crudo ≠ dato agregado ≠ unidad de inferencia; ninguna petición/caso/réplica interna se usa como observación independiente",
    "oe2": {
        "proposal_system": "swarm", "conventional_system": "decision_table", "comparator_primary": "decision_table", "comparator_fixed_before_data": True,
        "system_roles": {"swarm": "proposal", "decision_table": "conventional_independent", "rules": "swarm_heuristic_ablation", "bruteforce": "reference_optimum"},
        "auxiliary_contrasts": ["rules", "bruteforce"],
        "comparator_note": ("decision_table = tabla de decisión estática independiente del enjambre (baselines/decision_table.py): decisión técnica interna de este estudio. NO es un LMS real ni un LLM monolítico (no implementados): "
                            "las conclusiones de OE2 se limitan a este comparador. rules (ablación del enjambre) y bruteforce (óptimo de referencia, D11c) NO son comparadores convencionales: son contrastes auxiliares."),
        "time_contract": {"version": time_contract.CONTRACT_VERSION, "status": time_contract.STATUS, "candidate_common_metric": time_contract.COMMON_METRIC, "validation": time_contract.VALIDATION_STATUS,
                          "t_conv_equivalence": time_contract.T_CONV_EQUIVALENCE, "definitions": time_contract.DEFINITIONS,
                          "known_limits": list(time_contract.KNOWN_LIMITS)},
        "design": {"profiles_min": 30, "replicates_per_profile_min": 10, "systems": ["swarm", "decision_table"], "auxiliary_systems_optional": ["rules", "bruteforce"],
                   "unit_decision_ms_and_latency": "profile (media de K réplicas), pareado (decision_ms in-process, exploratorio mientras su validación esté pendiente); L_resp y throughput: corrida HTTP",
                   "unit_throughput": "run (corrida/lote HTTP independiente)", "throughput_runs_per_system_min": 10, "stationary_window_s_min": 60, "warmup_s_min": 10},
        "profile_sequence": {"algorithm": profile_sequence.ALGORITHM, "depends_only_on": ["batch_seed", "worker_index", "user_index", "seq_pos"], "same_sequence_for_all_systems": True,
                             "recorded": "hash de la secuencia esperada en plan/provenance y (user_index, seq_pos, profile_id) por petición en el log HTTP; `profile_sequence_check.mismatches` debe ser 0"},
        "comparator_scope_validation": {"status": "PENDING_METHODOLOGICAL_VALIDATION", "implemented_conventional_systems": ["decision_table"], "oe2_text_requires": "sistemas convencionales (plural)",
                                        "note": "no se implementa un LMS/LLM para satisfacer el plural; decisión de alcance pendiente"},
        "measurement": {"regions": time_contract.MEASUREMENT_REGIONS, "baseline_quality_in_request": False},
        "client_timeout": {"seconds": 30.0, "status": "PROVISIONAL_TECHNICAL", "same_for_all_systems": True, "recorded_in": "provenance.client_timeout_s y cada registro de corrida",
                           "note": "constante de campaña provisional (≫ 2 s del umbral de L_resp); no es un valor metodológico aprobado"},
        "generator_policy": http_window.GENERATOR_POLICY,
        "persist_policy": {"campaign": "off", "applies_to": "swarm y decision_table por igual (SWARM_API_PERSIST=0 en el servidor; el baseline nunca persiste)",
                           "on_supported_for_comparison": False, "verified_via": "GET /api/adaptation/health → persist_policy; campo `persistence` de cada respuesta"},
        "latency": {"official": "HTTP extremo a extremo", "indicator": "P95 por corrida", "also_reported": ["p50", "mean"], "contrast_regime_max_users": 25,
                    "stress_regime": "> 25 usuarios: estrés; no contrasta el umbral de 2 s", "threshold_ms": 2000},
        "throughput": {"official": "HTTP, peticiones correctas/s en ventana estacionaria", "rnf04": {"min_rps": 20.0, "max_error": 0.01}, "pilot_rps_not_official": "≈10–12 req/s (piloto in-process): diagnóstico",
                       "record": ["requests_total", "requests_ok", "errors", "timeouts", "duration_s", "throughput_rps", "users", "load_generator_cpu_percent"]},
        "tests": {"paired": "Shapiro-Wilk sobre diferencias → t pareada sobre log(tiempo) si razonable; si no Wilcoxon signed-rank", "independent_runs": "Shapiro-Wilk → Welch / Mann-Whitney",
                  "delta": "swarm − conventional", "report": ["effect", "ci95", "difference", "p", "n_effective"]},
        "holm_family": "primary:swarm_vs_decision_table = {L_resp P95 HTTP, throughput HTTP} × cargas de contraste (≤ 25 usuarios); decision_ms (candidata, validación PENDIENTE) se calcula aparte como exploratorio y queda FUERA de Holm; auxiliary:swarm_vs_rules y auxiliary:swarm_vs_bruteforce = familias propias, descriptivas (no son comparadores convencionales)",
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
