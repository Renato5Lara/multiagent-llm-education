"""Sistemas de adaptación de contenidos para la comparación de OE2: el convencional INDEPENDIENTE y dos sistemas de contraste/referencia, todos ejecutables detrás del mismo servidor y del mismo ensamblado de paquete.

CLASIFICACIÓN (`SYSTEM_ROLES`; única, y es la que devuelve el endpoint baseline en `system_role`):
    decision_table   convencional INDEPENDIENTE: tabla de decisión estática sobre los campos declarados del perfil (baselines/decision_table.py); sin enjambre, sin PSO, sin búsqueda, sin la heurística de AG1.
    rules            ablación/contraste del enjambre: decodifica el punto de arranque heurístico que AG1 entrega a la partícula 0 (S = φ(e_m = 2·w_m/max(w), variantes en nivel medio)), es decir, la propuesta SIN búsqueda.
                     NO es un sistema convencional independiente.
    bruteforce       referencia/óptimo: enumera las 6.561 configuraciones con el mismo 𝓕 y devuelve el óptimo global (línea base empírica D11c). Sirve de referencia de calidad y costo; NO es un sistema
                     convencional independiente de adaptación.

EQUIVALENCIA DE ENTRADA Y PROBLEMA: los tres reciben el mismo tipo de perfil (`ProfileRequest`), usan la misma biblioteca de artefactos, el mismo espacio de configuración, el mismo ensamblado y la misma validación del paquete
de 4 modalidades (con el audio real abierto y validado), y la misma función de evaluación 𝓕 (mismos términos Coher/Redund/CostT y pesos α/β/γ/δ, `W` de la regla de AG1) para informar la calidad. La caché de términos de 𝓕 es POR
PETICIÓN (en la propuesta: por ciclo); la validación de paquetes se memoiza entre peticiones en ambos lados. Esto NO significa que las métricas de tiempo sean metodológicamente equivalentes (ver abajo).

INDICADORES DE TIEMPO (en proceso, sin HTTP):
    decision_ms   tiempo desde que el sistema empieza a decidir la configuración hasta que tiene S (sin ensamblar el paquete).
    t_conv_ms     SIEMPRE `None` en estos sistemas: T_conv (AG0) es de la propuesta y aquí no hay convergencia iterativa; no se le llama así (contrato `oe/time_contract.py`, Fase B).
    decision_ms   tiempo OPERACIONAL de decisión de S (métrica común CANDIDATA de OE2, validación pendiente): perfil y W disponibles → S final decidida, sin ensamblar el paquete. En la propuesta el mismo campo copia el `t_conv_ms` de AG0 (sin cambios).
                  Su equivalencia metodológica con T_conv NO está validada (límites en `time_contract.KNOWN_LIMITS`). Este módulo no redefine ni modifica el T_conv de la propuesta.
    total_ms      latencia de la petición en proceso: perfil recibido → paquete validado listo.

ALCANCE: `decision_table` es la implementación convencional por reglas estáticas que este estudio define para la comparación; no reproduce un LMS real ni un LLM monolítico (no se miden ni se inventan).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from adaptation_swarm.analysis.baseline_bruteforce import bruteforce_search
from adaptation_swarm.analysis.core_replay import Terms, variant_terms
from adaptation_swarm.fitness.fitness import FitnessWeights, evaluate
from adaptation_swarm.gold.rubric import predicted_dominant
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.multimodal.package import assemble
from adaptation_swarm.multimodal.validation import validate_package
from adaptation_swarm.profiles.models import ProfileRequest
from adaptation_swarm.profiles.w_mapping import compute_weights, heuristic_start
from adaptation_swarm.pso.decode import decode
from adaptation_swarm.pso.space import Configuration
from adaptation_swarm.baselines import decision_table
from adaptation_swarm.schemas.ids import new_id

SYSTEMS = ("rules", "bruteforce", "decision_table")
BASELINE_VERSION = "conventional-v1"
# Clasificación EXPLÍCITA de cada sistema (no mezclar semánticas; el endpoint baseline la devuelve en `system_role`):
#   conventional_independent   sistema convencional de adaptación independiente del enjambre (OE2): `decision_table` (baselines/decision_table.py).
#   swarm_heuristic_ablation   `rules`: decodifica el punto de arranque heurístico de AG1 (el enjambre SIN búsqueda). NO es un convencional independiente; se conserva como ablación.
#   reference_optimum          `bruteforce`: óptimo global de 𝓕 por enumeración. Referencia de calidad/costo (D11c); NO es un sistema convencional de adaptación.
BASELINE_REPORTS_QUALITY_IN_REQUEST = False       # B3: el endpoint baseline NO evalúa 𝓕 de reporte dentro de la petición medida (única fuente de verdad: la usan el router, el health y los guards)
SYSTEM_ROLES = {"decision_table": "conventional_independent", "rules": "swarm_heuristic_ablation", "bruteforce": "reference_optimum"}


@dataclass
class ConventionalResult:
    system: str
    profile_id: str
    status: str
    S: list[int] | None = None
    F: float | None = None
    predicted_dominant: str | None = None
    t_conv_ms: float | None = None   # SIEMPRE None: T_conv es de la propuesta (AG0); estos sistemas no convergen iterativamente (se conserva el campo solo por compatibilidad de estructura)
    decision_ms: float | None = None  # tiempo OPERACIONAL de decisión (candidata a métrica común; validación pendiente): tiempo, en proceso, desde que el sistema empieza a decidir S hasta que la tiene (sin ensamblado del paquete)
    total_ms: float = 0.0
    n_evaluations: int = 0
    package: dict[str, Any] | None = field(default=None, repr=False)
    error: str | None = None


class ConventionalAdapter:
    def __init__(self, store: LibraryStore, system: str, fw: FitnessWeights | None = None):
        if system not in SYSTEMS:
            raise ValueError(f"system debe ser uno de {SYSTEMS}: {system!r}")
        self.store, self.system, self.fw = store, system, fw or FitnessWeights()
        self._validation_memo: dict[tuple, Any] = {}

    def _decide(self, prof: ProfileRequest, W) -> tuple[tuple[int, ...], float | None, int]:
        if self.system == "decision_table":                                          # independiente: solo lee el perfil (no W, no heurística del enjambre, no PSO)
            return decision_table.decide(prof).vector, None, 0
        if self.system == "rules":
            S = decode(np.array(heuristic_start(W))).vector
            return S, None, 0
        memo: dict[tuple[int, ...], Terms] = {}                                    # caché POR PETICIÓN (frío)
        best = bruteforce_search(self.store, prof.concept_id, W, self.fw, memo=memo)
        return tuple(best["S"]), best["F"], best["evals"]

    def _validated_package(self, concept_id: str, S: tuple[int, ...], cycle_id: str) -> dict[str, Any]:
        vc, vd, vt, va = decode(np.array(S, dtype=float)).variants
        code, dia = self.store.code(concept_id, vc), self.store.diagram(concept_id, vc, vd)
        svg, cpp = self.store.svg(concept_id, vc, vd), self.store.cpp(concept_id, vc)
        text, audio = self.store.text(concept_id, vt), self.store.audio(concept_id, vt, va, load=True)
        pkg = assemble(
            cycle_id=cycle_id, concept_id=concept_id, library_version=self.store.version, S=S,
            code={"content_id": code.entry["content_id"], "sha256": code.entry["sha256"], "concept_id": concept_id, "variant": vc, "source": code.text,
                  "cpp": None if cpp is None else {"content_id": cpp.content_id, "sha256": cpp.sha256, "source": cpp.text,
                                                   "validation": cpp.entry["validation"], "path": cpp.entry["path"]}},
            diagram={"content_id": dia.entry["content_id"], "sha256": dia.entry["sha256"], "concept_id": concept_id, "derived_from": dia.entry["derived_from"],
                     "variant": vd, "mermaid": dia.text,
                     "svg": None if svg is None else {"content_id": svg.content_id, "sha256": svg.sha256, "size_bytes": svg.entry["size_bytes"],
                                                      "path": svg.entry["path"], "nodes": svg.entry["validation"].get("nodes_in_svg")}},
            text={"content_id": text.entry["content_id"], "sha256": text.entry["sha256"], "concept_id": concept_id, "variant": vt, "text": text.text},
            audio={"content_id": audio.entry["content_id"], "sha256": audio.entry["sha256"], "concept_id": concept_id, "derived_from": audio.entry["derived_from"],
                   "variant": va, "path": audio.entry["path"], "duration_s": audio.entry["metadata"].get("duration_s"),
                   "size_bytes": audio.entry["size_bytes"], "provider": audio.entry["provider"]},
        ).to_dict()
        key = tuple(pkg[m]["content_id"] for m in ("code", "diagram", "text", "audio"))
        validation = self._validation_memo.get(key)
        if validation is None:
            validation = self._validation_memo[key] = validate_package(pkg, self.store)
        if not validation.valid:
            raise ValueError(f"paquete inválido: {validation.errors[:3]}")
        return {**pkg, "validation": validation.to_dict()}

    def evaluate_quality(self, profile: ProfileRequest, S) -> float:
        """𝓕 de la configuración `S` con el MISMO 𝓕 que la propuesta (términos Coher/Redund/CostT, pesos y W). Es solo REPORTE de calidad: NO forma parte de la decisión del convencional ni de ninguna región de
        tiempo comparable, así que nunca debe ejecutarse dentro de la petición medida (ver `adapt(report_quality=False)`). Determinista: se puede reconstruir fuera de línea desde `S`."""
        cfg = Configuration(tuple(S))
        return evaluate(cfg, compute_weights(profile).by_modality(), *variant_terms(self.store, profile.concept_id, cfg.variants, {}), self.fw).F

    def adapt(self, profile: ProfileRequest | dict, *, report_quality: bool = True) -> ConventionalResult:
        """Regiones de tiempo: `decision_ms` = solo la decisión; `total_ms` = perfil recibido → paquete validado listo. La evaluación de 𝓕 NO está en ninguna de ellas. Con `report_quality=True` (por defecto, uso
        directo) 𝓕 se calcula DESPUÉS de cerrar ambas, pero aún dentro de esta llamada; quien mida la latencia de la llamada (endpoint HTTP, ejecutor in-process) debe pasar `report_quality=False` y reconstruir 𝓕
        fuera de la región medida con `evaluate_quality`. `bruteforce` conserva su 𝓕 (es el resultado de la propia búsqueda, parte de su decisión)."""
        t0 = time.perf_counter()
        pid = profile.get("profile_id", "?") if isinstance(profile, dict) else profile.profile_id
        try:
            prof = profile if isinstance(profile, ProfileRequest) else ProfileRequest.model_validate(profile)
            W = compute_weights(prof)
            t_s = time.perf_counter()
            S, F, n_eval = self._decide(prof, W)
            decision_ms = (time.perf_counter() - t_s) * 1000.0
            pkg = self._validated_package(prof.concept_id, S, new_id())
            total_ms = (time.perf_counter() - t0) * 1000.0
        except Exception as exc:                                                  # error explícito, no silencioso
            return ConventionalResult(self.system, pid, "failed", total_ms=(time.perf_counter() - t0) * 1000.0,
                                      error=f"{type(exc).__name__}: {str(exc)[:300]}")
        cfg = Configuration(S)
        if F is None and report_quality:        # 𝓕 no se optimiza en estos sistemas; se informa solo si se pide, DESPUÉS de cerrar las regiones de tiempo
            F = evaluate(cfg, W.by_modality(), *variant_terms(self.store, prof.concept_id, cfg.variants, {}), self.fw).F
        return ConventionalResult(self.system, prof.profile_id, "completed", list(S), F, predicted_dominant(cfg.emphasis), decision_ms=decision_ms,
                                  total_ms=total_ms, n_evaluations=n_eval, package=pkg)
