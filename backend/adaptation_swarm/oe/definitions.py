"""Registro de definiciones operacionales de OE1–OE5 con su ESTADO y su fuente. Regla: si una definición ya está aprobada (asesoría, DECISION-CLOSURE, MASTER-SPEC, addenda del asesor) se reutiliza TAL CUAL; si no
existe, el punto queda `PENDING` (definición pendiente) y ningún módulo la inventa ni la usa para declarar un resultado oficial. Los manifiestos de las corridas incluyen este registro.

Fuentes (carpeta de documentos de tesis, fuera del repositorio): MS = MASTER-SPEC-2026-09-23.md · DC = DECISION-CLOSURE-2026-09-23.md · AD = ADDENDUM-DECISIONES-ASESOR-2026-09-2x.md.
"""

from __future__ import annotations

APPROVED, PARTIAL, PENDING = "APPROVED", "PARTIAL", "PENDING"
REQUIREMENTS_VERSION = "RF01-RF06+RNF01-RNF05 (MS §RF/RNF, 2026-09-23) + REL-C/REL-D (oe1, propias de este estudio)"

DEFINITIONS: dict[str, dict] = {
    "t_conv": {"status": APPROVED, "source": "DC DEC-10; MS (VD dimensión «Eficiencia T_conv»)", "definition": "T_conv se reporta en iteraciones (k_stop) y en milisegundos (t_convergencia − t_inicio_búsqueda); regla de parada |ΔF|<ε o k_max=15",
               "note": "Extensión a los sistemas convencionales (tiempo desde que deciden hasta tener S) es operativa de este estudio: ver `t_conv_baselines`."},
    "t_conv_baselines": {"status": PENDING, "source": "—", "definition": "tiempo de decisión de la configuración en `rules`/`bruteforce` equiparado a T_conv de la propuesta", "note": "por confirmar con el asesor"},
    "latency_l_resp": {"status": APPROVED, "source": "DC §9.2", "definition": "L_resp = petición HTTP → último byte del JSON con el paquete (incluye RF01, AG1, PSO, Redis, ensamblado y persistencia síncrona mínima; excluye descarga de audio y persistencia asíncrona); P95 con ≤ 25 usuarios",
                       "note": "La latencia EN PROCESO del ejecutor `oe/runner.py` es un sustituto exploratorio, no L_resp; la medición HTTP es Locust/JMeter en el hardware objetivo."},
    "throughput": {"status": PARTIAL, "source": "RNF04 (MS): ≥ 20 req/s con error < 1 %; DC §9.2", "definition": "peticiones correctas por segundo",
                   "note": "El cálculo por lote (n_ok / tiempo de pared del lote, bucle cerrado sin espera) es operativo de este estudio."},
    "quality_f1_adapt": {"status": APPROVED, "source": "AD 2026-09-26 (P1, P2, P3, R1–R3); MS §F1 vigente desde 26/09", "definition": "F1_i = 2|G_i ∩ P_i|/(|G_i|+|P_i|), P_i = {m : e_m ≥ 1}; por réplica = media de 100 casos; IC95 t sobre K=10",
                         "note": "La regla completa (`full_rule_version`) NO está sellada: pre-registro v3 con 8 campos PENDING_ADVISOR."},
    "usability_sus": {"status": APPROVED, "source": "Asesoría §4.4/§4.5; AD D7/D8", "definition": "SUS 0–100, n ≥ 10, media > 75, Shapiro → t/Wilcoxon contra 75", "note": "versión española publicada del SUS por citar (P7)"},
    "reference_value_75": {"status": APPROVED, "source": "Asesoría §4.4; OE5 aprobado", "definition": "valor de referencia SUS = 75 puntos", "note": ""},
    "statistical_unit_f1": {"status": APPROVED, "source": "AD 2026-09-26 R2", "definition": "la unidad es el perfil: sus F1 de las K réplicas se promedian; la inferencia usa los 100 promedios", "note": ""},
    "statistical_unit_performance": {"status": PENDING, "source": "—", "definition": "unidad para T_conv, latencia y throughput", "note": "propuesta técnica de este estudio (por confirmar): media por perfil para T_conv y latencia (diseño pareado); el LOTE para el throughput"},
    "replicate": {"status": PARTIAL, "source": "AD D5 (K=10 réplicas con semillas independientes, para F1)", "definition": "réplica = repetición del perfil con semilla derivada derive_seed(batch_seed, profile_id, replicate)", "note": "su uso en OE2–OE4 (K ≥ 10) es operativo"},
    "efficiency_of_adaptation_oe3": {"status": PARTIAL, "source": "MS (VD dimensión «Eficiencia T_conv»)", "definition": "indicador de eficiencia aprobado = T_conv",
                                     "note": "Se reportan además k_stop, mensajes y brecha al óptimo como indicadores COMPLEMENTARIOS; no existe un índice compuesto aprobado y no se inventa uno."},
    "compliance_score_oe1": {"status": PENDING, "source": "—", "definition": "puntaje de cumplimiento de requisitos", "note": "no existe definición aprobada de cómo agregar RF/RNF en un puntaje; OE1_COMPLIANCE_SCORE = BLOCKED_DEFINITION"},
    "reliability_oe1": {"status": PENDING, "source": "—", "definition": "indicador de confiabilidad", "note": "CR (DC DEC-10) es tasa de convergencia por ε, no confiabilidad; REL-C/REL-D son propuestas propias por confirmar"},
    "conventional_system_oe2": {"status": PARTIAL, "source": "AD 2026-09-25 D11c (línea base fuerza bruta frente a PSO); AD 2026-09-26 D11c (¿reemplaza o complementa el benchmark §2.1 LMS/reglas/LLM?: pregunta abierta al asesor)",
                                "definition": "`bruteforce` aprobado como línea base empírica; `rules` (reglas fijas) corresponde a la categoría «motores basados en reglas» (MS §comparadores) pero su definición empírica es de este estudio",
                                "note": "LMS tradicional y LLM monolítico NO están implementados ni medidos"},
    "precision_multimodal_oe5": {"status": PARTIAL, "source": "AD 2026-09-26 (F1 4×4 con audio, gold por arquetipo)", "definition": "F1_adapt de la regla v3", "note": "regla completa sin sellar (P4 `panel_protocol_version` PENDING_ADVISOR)"},
}


def blocked_for(experiment: str) -> list[str]:
    """Definiciones PENDING que condicionan una corrida oficial del experimento."""
    needs = {"oe1": ["compliance_score_oe1", "reliability_oe1"], "oe2": ["t_conv_baselines", "statistical_unit_performance"], "oe3": ["statistical_unit_performance"],
             "oe4": ["statistical_unit_performance"]}
    return [k for k in needs.get(experiment, []) if DEFINITIONS[k]["status"] == PENDING]
