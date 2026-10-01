"""Sistemas CONVENCIONALES de adaptación de contenidos — líneas base de OE2 (comparación estadística frente a la propuesta basada en enjambre).

DEFINICIÓN OPERATIVA (de este estudio): un sistema convencional es un adaptador monolítico, SECUENCIAL y en un solo proceso (sin agentes, sin bus de mensajes, sin enjambre) que, para
el mismo perfil, la misma biblioteca de artefactos, el mismo ensamblado y la misma validación del paquete, decide la configuración S por un procedimiento no basado en enjambre:

    rules        reglas fijas perfil → configuración: S = φ(punto heurístico derivado de W) (énfasis e_m = 2·w_m/max(w), variantes en nivel medio), sin búsqueda. Es la adaptación por
                 reglas típica de un LMS; no optimiza 𝓕.
    bruteforce   búsqueda exhaustiva de 𝓕 sobre las 6.561 configuraciones (óptimo global; la línea base que fijó el asesor, D11c).

Condiciones equivalentes con la propuesta: mismo perfil de entrada, misma `W` (regla de AG1), mismos términos de 𝓕 (Coher/Redund/CostT calculados desde los mismos artefactos), mismos pesos
α/β/γ/δ, mismo paquete de 4 modalidades (con el audio real abierto y validado) y la misma validación de paquete. La caché de términos de 𝓕 es POR PETICIÓN (en la propuesta: por ciclo);
la validación de paquetes se memoiza entre peticiones en ambos sistemas.

Definición de los indicadores (idéntica en los dos sistemas, para que sean comparables):
    t_conv_ms   tiempo desde que el sistema empieza a decidir la configuración hasta que la tiene decidida (propuesta: inicio de la búsqueda → convergencia de g_best);
    total_ms    latencia de la petición en proceso: perfil recibido → paquete validado listo (sin HTTP).

No es un sistema de la literatura reproducido: es la implementación convencional que este estudio define para la comparación. El LLM monolítico y los LMS reales quedan fuera (no se mide ni se inventa).
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
from adaptation_swarm.schemas.ids import new_id

SYSTEMS = ("rules", "bruteforce")
BASELINE_VERSION = "conventional-v1"


@dataclass
class ConventionalResult:
    system: str
    profile_id: str
    status: str
    S: list[int] | None = None
    F: float | None = None
    predicted_dominant: str | None = None
    t_conv_ms: float | None = None
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

    def adapt(self, profile: ProfileRequest | dict) -> ConventionalResult:
        t0 = time.perf_counter()
        pid = profile.get("profile_id", "?") if isinstance(profile, dict) else profile.profile_id
        try:
            prof = profile if isinstance(profile, ProfileRequest) else ProfileRequest.model_validate(profile)
            W = compute_weights(prof)
            t_s = time.perf_counter()
            S, F, n_eval = self._decide(prof, W)
            t_conv_ms = (time.perf_counter() - t_s) * 1000.0
            pkg = self._validated_package(prof.concept_id, S, new_id())
            total_ms = (time.perf_counter() - t0) * 1000.0
        except Exception as exc:                                                  # error explícito, no silencioso
            return ConventionalResult(self.system, pid, "failed", total_ms=(time.perf_counter() - t0) * 1000.0,
                                      error=f"{type(exc).__name__}: {str(exc)[:300]}")
        cfg = Configuration(S)
        if F is None:        # reglas: 𝓕 no se optimiza; se informa su valor (para comparar calidad) FUERA de los cronómetros
            F = evaluate(cfg, W.by_modality(), *variant_terms(self.store, prof.concept_id, cfg.variants, {}), self.fw).F
        return ConventionalResult(self.system, prof.profile_id, "completed", list(S), F, predicted_dominant(cfg.emphasis),
                                  t_conv_ms, total_ms, n_eval, pkg)
