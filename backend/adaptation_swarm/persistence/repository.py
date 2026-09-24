"""Persistencia en PostgreSQL del PoC (RF06 + trazabilidad completa):

    profile_id → cycle_id → iteración → partícula → candidato → agente/mensaje → paquete final

Usa SQLAlchemy síncrono (la base del proyecto) en un hilo aparte para no bloquear el bucle de eventos.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.swarm_adaptation import (
    AgentMessage, MultimodalCandidate, MultimodalPackage, SwarmCycle, SwarmIteration, SwarmProfile, SwarmRun,
)

from adaptation_swarm import SPEC_VERSION
from adaptation_swarm.gold.dataset import gold_for
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.profiles.models import ProfileRequest
from adaptation_swarm.schemas.messages import BusMessage

_BIG_KEYS = {"code", "mermaid", "text", "profile", "heuristic_start", "source"}


def summarize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Referencias/hashes/parámetros; el contenido pesado vive en la biblioteca (por hash)."""
    return {k: v for k, v in payload.items() if k not in _BIG_KEYS}


class PostgresCycleRepository:
    def __init__(self, session_factory=SessionLocal, run_label: str | None = None):
        self._sf = session_factory
        self.run_label = run_label

    # ── ciclos ───────────────────────────────────────────────────────────
    async def save_cycle(self, result, log_msgs: Sequence[BusMessage]) -> None:
        """Ciclo completo: fila del ciclo + paquete + iteraciones/partículas + mensajes."""
        await asyncio.to_thread(self._save_cycle_sync, result, list(log_msgs), True, True)

    async def save_cycle_minimal(self, result) -> None:
        """Persistencia SÍNCRONA mínima (ciclo + paquete): la que entra en L_resp (DECISION-CLOSURE §9.2)."""
        await asyncio.to_thread(self._save_cycle_sync, result, [], False, True)

    async def save_cycle_detail(self, result, log_msgs: Sequence[BusMessage]) -> None:
        """Persistencia ASÍNCRONA de trazas detalladas (iteraciones, partículas, mensajes): fuera de L_resp."""
        await asyncio.to_thread(self._save_cycle_sync, result, list(log_msgs), True, False)

    def _save_cycle_sync(self, r, log_msgs: list[BusMessage], detail: bool, base: bool) -> None:
        with self._sf() as s:
            if base:
                self._add_base(s, r)
            if detail:
                self._add_detail(s, r, log_msgs)
            s.commit()

    def _add_base(self, s, r) -> None:
        s.add(SwarmCycle(
            id=r.cycle_id, correlation_id=r.correlation_id, run_label=self.run_label, profile_id=r.profile_id,
            concept_id=r.concept_id, replicate=r.replicate, status=r.status, stop_reason=r.stop_reason,
            k_stop=r.k_stop, t_conv_ms=r.t_conv_ms, total_ms=r.total_ms, seed=str(r.seed),
            config_hash=r.config_hash, library_version=r.library_version, W=r.W, g_best_x=r.g_best_x,
            g_best_S=r.g_best_S, g_best_F=r.g_best_F, g_best_breakdown=r.g_best_breakdown,
            predicted_dominant=r.predicted_dominant, metrics=r.metrics.to_dict() if r.metrics else None,
            pso_diagnostics=r.pso_diagnostics, error=r.error))
        s.flush()      # el ciclo existe antes que sus hijos (FK)
        if r.package is not None:
            p = r.package
            s.add(MultimodalPackage(
                package_id=p["package_id"], cycle_id=r.cycle_id, concept_id=p["concept_id"],
                library_version=p["library_version"], S=p["S"], code_content_id=p["code"]["content_id"],
                diagram_content_id=p["diagram"]["content_id"], text_content_id=p["text"]["content_id"],
                audio_content_id=p["audio"]["content_id"], chain_valid=p["chain_valid"]))

    def _add_detail(self, s, r, log_msgs: list[BusMessage]) -> None:
        for it in r.iterations:
            s.add(SwarmIteration(cycle_id=r.cycle_id, k=it["k"], gbest_F=it["gbest_F"], delta_F=it["delta_F"],
                                 gbest_S=it["gbest_S"], t_iter_ms=it["t_iter_ms"], particles=it["particles"],
                                 diagnostics=it.get("diagnostics")))
        for m in log_msgs:
            s.add(AgentMessage(
                message_id=m.message_id, cycle_id=r.cycle_id, correlation_id=m.correlation_id,
                sender=m.sender.value, receiver=m.receiver.value, message_type=m.message_type.value,
                performative=m.performative.value, iteration=m.iteration, request_key=m.request_key,
                in_reply_to=m.in_reply_to, t_wall_ns=m.t_wall_ns, timestamp=m.timestamp, status=m.status,
                error=m.error, timing=m.timing or None, payload_summary=summarize_payload(m.payload),
                schema_version=m.schema_version))

    # ── datos de referencia ──────────────────────────────────────────────
    def save_profiles(self, profiles: Sequence[ProfileRequest], dataset_version: str) -> int:
        n = 0
        with self._sf() as s:
            known = set(s.scalars(select(SwarmProfile.profile_id).where(SwarmProfile.dataset_version == dataset_version)))
            for p in profiles:
                if p.profile_id in known:
                    continue
                g = gold_for(p)
                s.add(SwarmProfile(
                    profile_id=p.profile_id, dataset_version=dataset_version, archetype=p.archetype.value,
                    difficulty=p.difficulty.value, concept_id=p.concept_id, nivel=p.nivel,
                    tasa_error_previa=p.tasa_error_previa, estilo=p.estilo.model_dump(),
                    seed=str(p.metadata["seed"]), replicate=p.metadata["replicate"], gold_label=g.expected_dominant,
                    gold_rule_version=g.rule_version, payload=p.model_dump(mode="json")))
                n += 1
            s.commit()
        return n

    def sync_library(self, store: LibraryStore) -> int:
        n = 0
        with self._sf() as s:
            known = set(s.scalars(select(MultimodalCandidate.content_id).where(
                MultimodalCandidate.library_version == store.version)))
            for e in store.manifest["entries"]:
                if e["content_id"] in known:
                    continue
                s.add(MultimodalCandidate(
                    library_version=store.version, content_id=e["content_id"], concept_id=e["concept_id"],
                    anchor_version=e["anchor_version"], modality=e["modality"], key=e["key"], variant=e["variant"],
                    sha256=e["sha256"], derived_from=e["derived_from"], path=e["path"], size_bytes=e["size_bytes"],
                    agent=e["generator"]["agent"], agent_version=e["generator"]["agent_version"],
                    prompt_template_version=e["prompt_template_version"], provider=e["provider"],
                    validation=e["validation"], generation_ms=e["generation_ms"], generated_at=e["generated_at"]))
                n += 1
            s.commit()
        return n

    def start_run(self, run_label: str, *, batch_seed: int, config: dict, config_hash: str,
                  dataset_version: str | None, library_version: str | None, git_commit: str | None = None) -> None:
        with self._sf() as s:
            s.add(SwarmRun(run_label=run_label, spec_version=SPEC_VERSION, dataset_version=dataset_version,
                           library_version=library_version, batch_seed=batch_seed, config=config,
                           config_hash=config_hash, git_commit=git_commit))
            s.commit()
        self.run_label = run_label

    def finish_run(self, run_label: str, summary: dict) -> None:
        with self._sf() as s:
            run = s.get(SwarmRun, run_label)
            run.summary, run.finished_at = summary, datetime.now(timezone.utc)
            s.commit()

    # ── trazabilidad ─────────────────────────────────────────────────────
    def reconstruct(self, cycle_id: str) -> dict[str, Any]:
        """perfil → ciclo → iteraciones → partículas → mensajes de agentes → paquete final (desde Postgres)."""
        with self._sf() as s:
            c = s.get(SwarmCycle, cycle_id)
            if c is None:
                raise KeyError(cycle_id)
            prof = s.scalars(select(SwarmProfile).where(SwarmProfile.profile_id == c.profile_id)).first()
            its = list(s.scalars(select(SwarmIteration).where(SwarmIteration.cycle_id == cycle_id).order_by(SwarmIteration.k)))
            msgs = list(s.scalars(select(AgentMessage).where(AgentMessage.cycle_id == cycle_id).order_by(AgentMessage.t_wall_ns)))
            pkg = s.scalars(select(MultimodalPackage).where(MultimodalPackage.cycle_id == cycle_id)).first()
            cands = {}
            if pkg is not None:
                ids = [pkg.code_content_id, pkg.diagram_content_id, pkg.text_content_id, pkg.audio_content_id]
                for row in s.scalars(select(MultimodalCandidate).where(
                        MultimodalCandidate.library_version == pkg.library_version, MultimodalCandidate.content_id.in_(ids))):
                    cands[row.modality] = {"content_id": row.content_id, "agent": row.agent, "sha256": row.sha256,
                                           "provider": row.provider.get("name"), "validation": row.validation.get("status")}
            return {
                "profile": None if prof is None else {"profile_id": prof.profile_id, "archetype": prof.archetype,
                                                      "difficulty": prof.difficulty, "gold_label": prof.gold_label},
                "cycle": {"cycle_id": c.id, "correlation_id": c.correlation_id, "status": c.status,
                          "stop_reason": c.stop_reason, "k_stop": c.k_stop, "t_conv_ms": c.t_conv_ms,
                          "g_best_F": c.g_best_F, "predicted_dominant": c.predicted_dominant, "W": c.W},
                "iterations": [{"k": i.k, "gbest_F": i.gbest_F, "particles": len(i.particles),
                                "best_particle": max(i.particles, key=lambda p: p["F"])["idx"]} for i in its],
                "messages": [{"agent": f"{m.sender}->{m.receiver}", "type": m.message_type, "iteration": m.iteration,
                              "message_id": m.message_id} for m in msgs],
                "package": None if pkg is None else {"package_id": pkg.package_id, "S": pkg.S, "chain_valid": pkg.chain_valid,
                                                     "pieces": cands},
            }

    def delete_run(self, run_label: str) -> None:
        """Limpieza de una corrida (tests): borra ciclos (cascada) y la corrida."""
        with self._sf() as s:
            for c in s.scalars(select(SwarmCycle).where(SwarmCycle.run_label == run_label)):
                s.delete(c)
            run = s.get(SwarmRun, run_label)
            if run is not None:
                s.delete(run)
            s.commit()
