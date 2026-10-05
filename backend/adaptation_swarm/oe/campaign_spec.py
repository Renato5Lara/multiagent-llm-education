"""Especificación experimental INTERNA de las campañas oficiales OE1–OE5 (pre-registro técnico). Fija, ANTES de ejecutar, comparador, pruebas, α, familias de Holm, unidades estadísticas, tamaños de muestra,
agregación, umbrales, exclusiones y versiones de definiciones. NO cambia objetivos, hipótesis, variables ni indicadores: solo operacionaliza.

ESTADO: «decisión técnica interna + justificación metodológica». NINGUNA entrada está «APROBADA POR EL ASESOR» (no existe aprobación explícita): `advisor_approved` es False en todas y `open_blockers()` enumera lo
que impide una campaña oficial. El hash de la especificación (`spec_hash`) se registra en el provenance de cada corrida: cambiarla después de ver datos cambia el hash y queda a la vista.
"""

from __future__ import annotations

import hashlib
import json

SPEC_VERSION = "oe-campaign-spec-v1"
STATUS = "TECHNICAL_INTERNAL_DECISION_NOT_ADVISOR_APPROVED"

SPEC: dict = {
    "version": SPEC_VERSION, "status": STATUS, "advisor_approved": False,
    "alpha": 0.05, "multiplicity": "Holm dentro de cada familia confirmatoria (abajo); sin corrección entre familias",
    "unit_rule": "dato crudo ≠ dato agregado ≠ unidad de inferencia; ninguna petición/caso/réplica interna se usa como observación independiente",
    "oe2": {
        "comparator_primary": "rules", "comparator_secondary": "bruteforce", "comparator_fixed_before_data": True,
        "comparator_note": "rules = categoría «motores basados en reglas» (MS §comparadores); bruteforce = línea base aprobada D11c (referencia de costo/calidad). LMS real y LLM monolítico NO implementados (benchmark §2.1): ver blockers.",
        "t_conv_baseline_operational": "tiempo desde que el sistema empieza a decidir hasta tener S (conventional.py); se reporta siempre con F y brecha al óptimo",
        "design": {"profiles_min": 30, "replicates_per_profile_min": 10, "systems": ["swarm", "rules", "bruteforce"], "unit_t_conv_and_latency": "profile (media de K réplicas), pareado",
                   "unit_throughput": "run (corrida/lote HTTP independiente)", "throughput_runs_per_system_min": 10, "stationary_window_s_min": 60, "warmup_s_min": 10},
        "latency": {"official": "HTTP extremo a extremo", "indicator": "P95 por corrida", "also_reported": ["p50", "mean"], "contrast_regime_max_users": 25,
                    "stress_regime": "> 25 usuarios: estrés; no contrasta el umbral de 2 s", "threshold_ms": 2000},
        "throughput": {"official": "HTTP, peticiones correctas/s en ventana estacionaria", "rnf04": {"min_rps": 20.0, "max_error": 0.01}, "pilot_rps_not_official": "≈10–12 req/s (piloto in-process): diagnóstico",
                       "record": ["requests_total", "requests_ok", "errors", "timeouts", "duration_s", "throughput_rps", "users", "load_generator_cpu_percent"]},
        "tests": {"paired": "Shapiro-Wilk sobre diferencias → t pareada sobre log(tiempo) si razonable; si no Wilcoxon signed-rank", "independent_runs": "Shapiro-Wilk → Welch / Mann-Whitney",
                  "delta": "swarm − conventional", "report": ["effect", "ci95", "difference", "p", "n_effective"]},
        "holm_family": "{T_conv, L_resp P95, throughput} × {swarm vs rules} (comparador primario); bruteforce = secundaria con su propia familia",
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
    """Condiciones de la campaña oficial que HOY no se cumplen (se leen de los registros reales; nada se declara resuelto aquí)."""
    from adaptation_swarm.gold import rubric_v3
    from adaptation_swarm.oe import definitions as defs
    out = [f"definición PENDING: {k}" for k, v in defs.DEFINITIONS.items() if v["status"] == defs.PENDING]
    if not rubric_v3.APPROVED_RULE_VERSIONS:
        out.append("F1 v3 sin sellar (rubric_v3.APPROVED_RULE_VERSIONS vacío; PENDING_ADVISOR en el pre-registro v3)")
    out.append("benchmark §2.1: LMS tradicional y LLM monolítico no implementados; D11c (¿bruteforce reemplaza o complementa?) abierta — requiere decisión del asesor")
    out.append("medición HTTP oficial (ventana estacionaria, CPU del generador) pendiente de ejecutar en el hardware objetivo")
    return out
