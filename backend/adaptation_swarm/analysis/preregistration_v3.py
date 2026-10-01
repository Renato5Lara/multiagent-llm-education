"""Pre-registro de K = 10 v3 — BORRADOR BLOQUEADO (capa ADITIVA; funciones puras). Consolida el contrato metodológico (P1, P2, P3, P4, regla estadística, K, semillas, dataset, biblioteca, hardware y restricciones de
ejecución) ANTES de cualquier ejecución oficial. NO ejecuta K = 10 v3, NO sella, NO escribe archivos y NO toca el pre-registro de K = 10 v2 (`analysis/preregistration.py`, `experiments/preregistration_k10_2026-09-26/`).

Cada campo metodológico lleva un ESTADO explícito y una fuente:
    CLOSED           decisión aprobada y técnicamente cerrada (con la fuente documental).
    DERIVED          valor técnico derivado de una decisión cerrada y comprobable en los artefactos existentes (se lee de ellos; no se copia a mano).
    PENDING_ADVISOR  decisión que aún requiere confirmación/documentación del asesor: NO se completa ni se inventa; BLOQUEA el sellado.
Además `pending_integration` lista lo que está decidido pero aún no demostrado en el código v3; también bloquea el sellado, pero no es una decisión pendiente del asesor. El criterio conjunto (`ci_pass AND statistical_pass`) se integra
REUTILIZANDO `inference.combined_criterion` de v2 (sin cambios): el pre-registro registra su salida real y verifica que coincide con la regla; no hay una segunda fórmula. Que esa integración esté cerrada NO hace sellable el borrador.

`panel_protocol_version` y `full_rule_version` (gold + inclusión + agregación + protocolo del panel) son identificadores TÉCNICOS definidos en `rubric_v3` (nombre = decisión de ingeniería, esquema de v2; los componentes del
protocolo siguen siendo los cerrados en DECISION-CLOSURE §15). La versión de la biblioteca solo se cierra si el manifiesto local coincide con el de K = 10 v2. Siguen PENDING los puntos que son personas o infraestructura:
hardware, entorno de software oficial, originales del asesor, declaración del tesista y confirmación de la regla estadística. `rubric_v3.APPROVED_RULE_VERSIONS` no se toca: la aprobación técnica se registra tras el sellado.

La información técnica (hashes de módulos, commit, dataset, biblioteca) se LEE de los artefactos; `code_modules_at_fixing_v3` es una estructura propia que NO altera `replicas.module_fingerprints()` de v2: contiene
las huellas de los 19 módulos que v2 ya huella (sin cambios) y las de los módulos v3. La salida es determinista (sin marcas de tiempo).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import adaptation_swarm
from adaptation_swarm.analysis import inference, replicas as _v2_infra, replicas_v3, statistical_rule_v3
from adaptation_swarm.config import SETTINGS
from adaptation_swarm.gold import rubric_v3
from adaptation_swarm.gold.f1_multilabel import METRIC_VERSION, OFFICIAL_AGGREGATION
from adaptation_swarm.profiles.generator import read_dataset
from adaptation_swarm.pso.space import MODALITIES
from adaptation_swarm.tools import isolated_env as iso

SCHEMA = "preregistration-k10-v3"
BANNER = "PRE-REGISTRO v3 — BORRADOR BLOQUEADO — NO SELLADO — NO EJECUTADO"
CLOSED, DERIVED, PENDING_ADVISOR = "CLOSED", "DERIVED", "PENDING_ADVISOR"
STATES = (CLOSED, DERIVED, PENDING_ADVISOR)
PROPOSED_LIBRARY_VERSION = "lib-v10-5dd83cd4"                      # la que la documentación previa da como «sin cambios»; NO está sellada como la biblioteca oficial de v3
V2_OFFICIAL_MANIFEST = iso.BACK / "official_runs" / "k10_official_2026-09-27" / "manifest.json"       # solo LECTURA (referencia de entorno y biblioteca de K = 10 v2)
_V3_MODULES = ("analysis/statistical_rule_v3.py", "gold/rubric_v3.py", "analysis/replicas_v3.py", "analysis/evaluation_v3.py", "analysis/preregistration_v3.py")

SRC_SPEC = "ESPECIFICACION-METODOLOGICA-P1-P2-2026-09-28.md"
SRC_CLOSURE = "DECISION-CLOSURE-2026-09-23.md §15"
SRC_DRAFT = "BORRADOR-PREREGISTRO-K10-P1P2-2026-09-28.md"
FIDELITY = "respuestas del asesor comunicadas por el tesista; originales por anexar"


class PreregistrationNotSealable(RuntimeError):
    """El pre-registro v3 tiene campos PENDING_ADVISOR o integraciones pendientes: no puede sellarse."""

    def __init__(self, diagnosis: Mapping):
        super().__init__(f"pre-registro v3 no sellable: pendientes del asesor {diagnosis['pending']}; integraciones pendientes {diagnosis['pending_integration']}")
        self.diagnosis = dict(diagnosis)


def _f(value: Any, status: str, source: str | None = None, **extra) -> dict:
    if status not in STATES:
        raise ValueError(f"estado desconocido: {status!r}")
    return {"value": value, "status": status, "source": source, **extra}


def _sha_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def v3_module_fingerprints() -> dict[str, str]:
    """sha256 de los módulos v3 (los cuatro de la capa metodológica más este constructor). No altera `replicas.module_fingerprints()` de v2."""
    root = Path(adaptation_swarm.__file__).parent
    return {f: _sha_file(root / f) for f in _V3_MODULES}


def code_modules_at_fixing_v3() -> dict[str, str]:
    """Estructura PROPIA de v3: las 19 huellas que v2 ya huella (sin cambios: demuestran que el núcleo es el mismo) y las de los módulos v3."""
    return {**_v2_infra.module_fingerprints(), **v3_module_fingerprints()}


# ── componentes ─────────────────────────────────────────────────────────────────────────────────────────────────
def _rule_section() -> dict:
    rule = rubric_v3.get_rule(rubric_v3.GOLD_RULE_VERSION, rubric_v3.INCLUSION_RULE_ID)
    return {
        "P1_inclusion": _f({"rule_id": rule.inclusion.rule_id, "formula": "S = { m | e_m >= 1 AND e_m / sum(e) >= 0.20 }", "integer_form": "e_m >= 1 AND 5 * e_m >= sum(e)",
                            "empty_total": "sum(e) = 0 => S = vacio (F1 = 0)", "domain": "e_m in {0,1,2}", "implementation": rule.inclusion.to_dict()}, CLOSED, f"{SRC_SPEC} §3 (asesor, 28/09)"),
        "P2_gold": _f({"rule_version": rule.gold.rule_version, "matrix": {a.value: [m for m in MODALITIES if m in s] for a, s in rule.gold.expected_by_archetype.items()},
                       "audio": "solo Balanced-Multimodal", "balanced": "siempre las cuatro modalidades; sin desempate", "independence": "ni de W ni de la dificultad",
                       "fingerprint": rule.gold.fingerprint()}, CLOSED, f"{SRC_SPEC} §4 y §12 (matriz explícita normativa, inmutable)"),
        "P3_aggregation": _f({"aggregation": OFFICIAL_AGGREGATION, "case_f1": "F1_i = 2|G_i ∩ P_i| / (|G_i| + |P_i|)", "empty_prediction": "F1_i = 0",
                              "f1_adapt_per_replica": "media de los F1 por caso", "observation_unit": "el caso (profile_id × réplica)",
                              "ovr_matrices": {"modalities": list(MODALITIES), "role": "DESCRIPTIVAS (One-vs-Rest 2x2 por modalidad; no es una métrica multiclase)"},
                              "metric_version": METRIC_VERSION}, CLOSED, f"{SRC_CLOSURE}; P3 (asesor, 26/09); {SRC_SPEC}"),
        "P4_panel": {
            "panel_protocol_version": _f(rubric_v3.PANEL_PROTOCOL_VERSION, CLOSED, "rubric_v3.PANEL_PROTOCOL_VERSION: decisión técnica de nombre (esquema de v2); componentes cerrados en DECISION-CLOSURE §15",
                                         note="el identificador no cambia ningún componente metodológico del panel"),
            "components": {"statistic": _f("Gwet AC1 (binario, multi-evaluador)", CLOSED, f"{SRC_CLOSURE} (C1–C3)"),
                           "ac1_threshold": _f({"value": 0.70, "comparison": ">"}, CLOSED, SRC_CLOSURE),
                           "majority": _f("estricta", CLOSED, SRC_CLOSURE),
                           "archetype_approval": _f("> 50 % de aprobaciones por arquetipo", CLOSED, SRC_CLOSURE),
                           "tie_5_5": _f("inválido (empate = no aprobado; obliga a revisar la rule_version)", CLOSED, SRC_CLOSURE),
                           "denominator": _f("4*n (todos los juicios recolectados)", CLOSED, SRC_CLOSURE),
                           "raw_agreement_threshold": _f({"value": 0.85, "comparison": ">="}, CLOSED, SRC_CLOSURE),
                           "review_rule": _f("si AC1 <= 0.70 OR acuerdo crudo < 0.85 ⇒ revisar la rule_version", CLOSED, SRC_CLOSURE),
                           "min_evaluators": _f(10, CLOSED, f"{SRC_CLOSURE}; D7 (asesor, 25/09)")}},
        "full_rule_version": _f(rubric_v3.FULL_RULE_VERSION, DERIVED, "rubric_v3.FULL_RULE_VERSION = gold + inclusión + agregación + protocolo del panel"),
    }


def _statistical_section() -> dict:
    return {
        "statistical_pass_rule": _f({"version": statistical_rule_v3.STATISTICAL_PASS_RULE_VERSION, "rule": "p < alpha AND media muestral > benchmark"}, CLOSED,
                                    "Consulta 4 (DEC-F1-TEST); DECISION-CLOSURE §15 C4; implementada en statistical_rule_v3"),
        "alpha": _f(inference.ALPHA, CLOSED, "asesoría §4.5"),
        "benchmark": _f(inference.BENCHMARK_F1, CLOSED, "RNF-03 (F1_adapt >= 0.85)"),
        "direction": _f("unilateral: H0: μ <= 0.85; H1: μ > 0.85", CLOSED, "Consulta 4 (asesor, 26/09)"),
        "test_unit": _f({"observations": "100 medias por perfil (media de sus F1 en las 10 réplicas)", "normality": "Shapiro-Wilk, alpha = 0.05",
                         "test": "t de una muestra si hay normalidad; si no, Wilcoxon de rangos con signo"}, CLOSED, "R2 (asesor, 26/09); " + SRC_CLOSURE),
        "ci95": _f({"method": inference.CI_METHOD, "observations": "los 10 F1_adapt (uno por réplica)", "df": inference.K_REPLICAS - 1}, CLOSED, "R1 (asesor, 26/09)"),
        "combined_criterion": _combined_criterion_field(),
    }


def _combined_criterion_truth_table() -> dict[str, Any]:
    """Salida REAL de `inference.combined_criterion` (código de v2, sin cambios y reutilizado; aquí no se escribe ninguna fórmula) para las combinaciones de `ci_pass` y `statistical_pass`.
    `ci_pass` se obtiene con un límite inferior en el borde del benchmark (≥ 0.85 ⇒ True) y justo por debajo (False); `statistical_pass = None` es una prueba indefinida."""
    table = {}
    for ci_lower in (inference.BENCHMARK_F1, inference.BENCHMARK_F1 - 0.01):
        for stat in (True, False, None):
            r = inference.combined_criterion({"lower": ci_lower}, {"test": None, "p_value": None, "statistical_pass": stat})
            table[f"ci_pass={r['ci_pass']},statistical_pass={stat}"] = {"combined_pass": r["combined_pass"], "verdict": r["verdict"], "rule": r["rule"]}
    return table


def _combined_criterion_integrated(table: Mapping[str, Mapping]) -> bool:
    """La integración se da por demostrada SOLO si la implementación existente declara `rule == "AND"` y su salida es True únicamente para `ci_pass=True` con `statistical_pass=True` (y INDETERMINADO, `None`, si la
    prueba es indefinida). Es una VERIFICACIÓN de la salida de `inference.combined_criterion`, no una segunda implementación de la regla."""
    if {v["rule"] for v in table.values()} != {"AND"}:
        return False
    true_rows = sorted(k for k, v in table.items() if v["combined_pass"] is True)
    undefined_rows = sorted(k for k, v in table.items() if v["combined_pass"] is None)
    return true_rows == ["ci_pass=True,statistical_pass=True"] and undefined_rows == ["ci_pass=False,statistical_pass=None", "ci_pass=True,statistical_pass=None"]


def _combined_criterion_field() -> dict:
    table = _combined_criterion_truth_table()
    return _f("RNF-03 ⇔ límite inferior del IC95 >= 0.85 AND prueba superada (statistical_pass)", CLOSED, f"R3 y C5 ({SRC_CLOSURE})",
              implementation={"callable": "adaptation_swarm.analysis.inference.combined_criterion", "reused_without_changes": True, "rule": "ci_pass AND statistical_pass",
                              "ci_pass": "límite inferior del IC95 >= benchmark (0.85)", "statistical_pass_input": "statistical_rule_v3.profile_level_test_v3(...)['statistical_pass']",
                              "ci_input": "inference.student_t_ci(F1_adapt de las 10 réplicas)", "undefined_test": "statistical_pass = None ⇒ INDETERMINADO (nunca PASS)",
                              "truth_table_from_implementation": table, "verified": _combined_criterion_integrated(table)})


def _pending_integration(doc: Mapping) -> list[str]:
    """Integraciones técnicas decididas pero aún no demostradas en el código v3: hoy, solo el criterio conjunto si la implementación existente no se verifica como `ci_pass AND statistical_pass`."""
    impl = doc["statistical"]["combined_criterion"]["implementation"]
    return [] if impl["verified"] else ["statistical.combined_criterion"]


def _experiment_section() -> dict:
    seeds = _v2_infra.derive_batch_seeds(replicas_v3.K10_MASTER_SEED, replicas_v3.K_OFFICIAL)
    return {
        "k": _f(replicas_v3.K_OFFICIAL, CLOSED, "D5b (asesor, 25/09)"),
        "master_seed": _f(replicas_v3.K10_MASTER_SEED, CLOSED, f"{SRC_DRAFT} §10 (opción C): se conservan la semilla maestra y las semillas de lote de K = 10 v2"),
        "seed_derivation": _f("sha256('replicas-v1|<master_seed>|<i>')[:8] big-endian & (2^63 - 1), i = 0..9; semilla de ciclo = sha256('<batch_seed>|<profile_id>|<replicate>')[:8], replicate = 0",
                              CLOSED, "la derivación existente y validada de v2 (sin cambios)"),
        "batch_seeds": _f(seeds, DERIVED, "derive_batch_seeds(master_seed, K) de replicas (v2), sin cambios"),
        "f1_target": _f(inference.BENCHMARK_F1, CLOSED, "RNF-03"),
        "rnf03": _f("PENDIENTE DE EJECUCIÓN FORMAL (no se predice ni se declara)", CLOSED, "este pre-registro no contiene resultados"),
        "h1": _f("PENDIENTE: hipótesis conjuntiva (F1_adapt >= 0.85 AND L_resp < 2.0 s AND SUS > 75); L_resp y SUS se evalúan por separado", CLOSED, "D6 (asesor, 25/09)"),
        "scope": _f(dict(replicas_v3.SCOPE), CLOSED, "R4 (asesor, 26/09): el núcleo mide F1_adapt y convergencia; RNF-01/RNF-04 exigen el experimento full-stack separado"),
        "latency_rnf01": _f("no se mide ni se declara aquí: experimento full-stack separado (Locust/JMeter) en el entorno cloud; este pre-registro no lo incluye", CLOSED, "R4"),
    }


def _dataset_section(profiles_path: Path) -> dict:
    profiles = read_dataset(profiles_path)
    ident = _v2_infra.dataset_identity(profiles_path)
    manifest = json.loads((Path(profiles_path).with_name(f"manifest-{ident['version']}.json")).read_text(encoding="utf-8")) if ident["manifest_file"] else {}
    by_arch, by_diff = {}, {}
    for p in profiles:
        by_arch[p.archetype.value] = by_arch.get(p.archetype.value, 0) + 1
        by_diff[p.difficulty.value] = by_diff.get(p.difficulty.value, 0) + 1
    concepts = {}
    for p in profiles:
        concepts.setdefault(p.concept_id, 0)
        concepts[p.concept_id] += 1
    excluded = list(manifest.get("excluded_modules", []))
    titles = {str(p.metadata.get("concept_title", "")) + "|" + str(p.metadata.get("concept_module", "")) for p in profiles}
    return _f({"file": Path(profiles_path).name, "sha256": _sha_file(profiles_path), "version": ident["version"], "manifest_file": ident["manifest_file"], "manifest_sha256": ident["manifest_sha256"],
               "n_profiles": len(profiles), "n_unique_profile_ids": len({p.profile_id for p in profiles}), "by_archetype": dict(sorted(by_arch.items())), "by_difficulty": dict(sorted(by_diff.items())),
               "profile_concept_relation": {"one_concept_per_profile": all(bool(p.concept_id) for p in profiles), "n_distinct_concepts": len(concepts), "max_profiles_per_concept": max(concepts.values())},
               "excluded_modules": excluded, "recursion_excluded": "Recursividad" in excluded and not any("ecursi" in t for t in titles)},
              DERIVED, "leído de profiles-v1.jsonl y manifest-v1.json (sin regenerar ni copiar a mano)")


def _library_section(library_root: Path | None) -> dict:
    root = Path(library_root or SETTINGS.library_root)
    manifest = root / PROPOSED_LIBRARY_VERSION / "manifest.json"
    exists = manifest.exists()
    v2 = json.loads(V2_OFFICIAL_MANIFEST.read_text(encoding="utf-8")) if V2_OFFICIAL_MANIFEST.exists() else None
    sha = _sha_file(manifest) if exists else None
    same_v2 = None if v2 is None or sha is None else v2["library"]["manifest_sha256"] == sha and v2["library"]["version"] == PROPOSED_LIBRARY_VERSION
    extra = dict(proposed=PROPOSED_LIBRARY_VERSION, exists_locally=exists, manifest_sha256_local=sha, same_as_k10_v2=same_v2)
    # Decisión técnica: la biblioteca de v3 es la de K = 10 v2 (§10.4: la única diferencia experimental es la regla de evaluación). Se CIERRA solo si el manifiesto local existe y coincide en versión y sha256 con el
    # de v2; en cualquier otro caso queda pendiente (nunca se asume).
    version = (_f(PROPOSED_LIBRARY_VERSION, DERIVED, f"{SRC_DRAFT} §10.4 (solo cambia la regla de evaluación) + manifiesto local idéntico al de K = 10 v2", **extra) if same_v2
               else _f(None, PENDING_ADVISOR, f"{SRC_DRAFT} §4: la biblioteca propuesta no se verificó idéntica a la de K = 10 v2 (manifiesto local ausente, distinto o referencia v2 no disponible)", **extra))
    return {"version": version,
            "explicit_version_required": _f(True, CLOSED, "no se asume ninguna versión de forma silenciosa (replicas_v3 exige library_version explícita)")}


def _environment_section() -> dict:
    v2 = json.loads(V2_OFFICIAL_MANIFEST.read_text(encoding="utf-8")) if V2_OFFICIAL_MANIFEST.exists() else None
    return {"hardware": _f(None, PENDING_ADVISOR, "D10 (asesor): el entorno cloud de 8 vCPU / 32 GB RAM rige la medición full-stack (RNF-01/04); no hay cierre formal de un entorno oficial para la ejecución de F1 de K = 10 v3",
                           target_hardware="8 vCPU / 32 GB RAM", hardware_status=PENDING_ADVISOR),
            "software_environment": _f(None, PENDING_ADVISOR, f"{SRC_DRAFT} §9.4: declarar el entorno oficial (intérprete, numpy, scipy, imagen de contenedor) y el commit base",
                                       k10_v2_reference=None if v2 is None else dict(v2["environment"]), observed_now=_v2_infra.environment())}


def _constraints_section() -> dict:
    return {"physical_execution_mandatory": _f(True, CLOSED, f"{SRC_DRAFT} §10.1 (opción C)"),
            "same_seeds_as_k10_v2": _f(True, CLOSED, f"{SRC_DRAFT} §10.5"),
            "only_experimental_change": _f("la regla de evaluación P1/P2 (y su rule_version); PSO, φ, fitness, dataset y biblioteca no cambian", CLOSED, f"{SRC_DRAFT} §10.4"),
            "k10_v2_untouched": _f("íntegro, congelado e histórico; no se reinterpreta ni se recalcula", CLOSED, f"{SRC_DRAFT} §10.6"),
            "validity_conditions": _f(["rule_version definida antes del sellado", "pre-registro sellado antes de ejecutar", "el nuevo F1 no se calcula ni se usa antes del sellado (acreditable solo por declaración)",
                                      "K = 10 v2 no se reinterpreta", "ejecución nueva posterior al sellado"], CLOSED, f"{SRC_DRAFT} §10.11"),
            "output_root": _f("backend/official_runs/k10_v3/ (directorio nuevo; nunca dentro de los artefactos de v2)", DERIVED, "replicas_v3.V3_OUTPUT_ROOT"),
            "declaration_f1_not_computed_before_sealing": _f(None, PENDING_ADVISOR, f"{SRC_DRAFT} §10.10: solo acreditable por declaración del tesista en el momento del sellado", note="no se hace aquí"),
            "advisor_originals_annexed": _f(None, PENDING_ADVISOR, f"{SRC_DRAFT} §9.5 y {FIDELITY}"),
            "tesista_confirmation_statistical_rule": _f(None, PENDING_ADVISOR, "NOTA-PREANALISIS-K10-2026-09-27 §4.1: «conviene que el tesista lo confirme»; ahora la regla v3 es explícita en código")}


def build_preregistration_v3(*, library_root: Path | None = None, profiles_path: Path = replicas_v3.DEFAULT_PROFILES) -> dict:
    """Construye el borrador del pre-registro v3 leyendo los artefactos. No ejecuta nada, no escribe nada y no contiene resultados."""
    doc = {"schema": SCHEMA, "banner": BANNER, "contains_results": False, "executed": False, "fidelity": FIDELITY,
           "rule": _rule_section(), "statistical": _statistical_section(), "experiment": _experiment_section(), "dataset": _dataset_section(Path(profiles_path)),
           "library": _library_section(library_root), "environment": _environment_section(), "execution_constraints": _constraints_section(),
           "pending_integration": [],
           "traceability": {"git_at_fixing": _v2_infra.code_version(), "code_modules_at_fixing_v3": code_modules_at_fixing_v3(), "v3_modules": v3_module_fingerprints(),
                            "approval_registry_v3": sorted(rubric_v3.APPROVED_RULE_VERSIONS), "library_manifest_sha256": None}}
    doc["pending_integration"] = _pending_integration(doc)
    lib_sha = doc["library"]["version"]["manifest_sha256_local"]
    doc["traceability"]["library_manifest_sha256"] = lib_sha
    doc["sealing"] = sealing_diagnosis(doc)
    doc["status"] = "DRAFT_BLOCKED" if not doc["sealing"]["sealable"] else "DRAFT_SEALABLE"
    return doc


# ── sellado ────────────────────────────────────────────────────────────────────────────────────────────────────
def _walk(obj: Any, path: str = ""):
    if isinstance(obj, dict):
        if obj.get("status") in STATES and "value" in obj:
            yield path, obj
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                yield from _walk(v, f"{path}.{k}" if path else k)


def pending_fields(doc: Mapping) -> list[str]:
    """Rutas de los campos PENDING_ADVISOR (las que bloquean el sellado por falta de una decisión/documento del asesor)."""
    return sorted(p for p, field in _walk(doc) if field["status"] == PENDING_ADVISOR)


def sealing_diagnosis(doc: Mapping) -> dict:
    """Qué bloquea el sellado. `sealable` solo es True sin campos PENDING_ADVISOR ni integraciones pendientes."""
    fields = list(_walk(doc))
    pending, integration = pending_fields(doc), sorted(doc.get("pending_integration", []))
    return {"sealable": not pending and not integration, "pending": pending, "pending_integration": integration,
            "n_closed": sum(1 for _, f in fields if f["status"] == CLOSED), "n_derived": sum(1 for _, f in fields if f["status"] == DERIVED), "n_pending": len(pending)}


def is_sealable(doc: Mapping) -> bool:
    return sealing_diagnosis(doc)["sealable"]


def require_sealable(doc: Mapping) -> None:
    d = sealing_diagnosis(doc)
    if not d["sealable"]:
        raise PreregistrationNotSealable(d)


def full_rule_version(doc: Mapping) -> str | None:
    """`<gold>+<inclusión>+<agregación>+<protocolo del panel>` (el mismo esquema que v2), o None mientras `panel_protocol_version` no esté cerrada: nunca se inventa."""
    panel = doc["rule"]["P4_panel"]["panel_protocol_version"]
    if panel["status"] == PENDING_ADVISOR or not panel["value"]:
        return None
    return f"{rubric_v3.RULE_VERSION}+{doc['rule']['P3_aggregation']['value']['aggregation']}+{panel['value']}"


def canonical_bytes(doc: Mapping) -> bytes:
    return json.dumps(doc, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def content_hash(doc: Mapping) -> str:
    return hashlib.sha256(canonical_bytes(doc)).hexdigest()
