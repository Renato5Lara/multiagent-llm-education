"""AG0 — Swarm-Orchestrator (asesoría §3.3.1): dirige los ciclos de comunicación, calcula la función de
aptitud global 𝓕 y decreta el punto de convergencia del enjambre.

AG0 es el ÚNICO agente que ejecuta un grafo LangGraph (`graph/cycle_graph.py`, DEC-11). Se comunica
con AG1–AG4 EXCLUSIVAMENTE por el bus REAL de Redis (mensajes `swarm-msg-v1`); si Redis cae, el ciclo
falla con `stop_reason=error` — no hay sustituto.

Estado: el estado autoritativo del ciclo (k, partículas, p_best, g_best) vive en el estado del grafo y
se espeja en Redis (`state:{cycle_id}`) como memoria compartida; AG1–AG4 no tienen estado de ciclo.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from adaptation_swarm.agents.base import SwarmAgent
from adaptation_swarm.config import SETTINGS
from adaptation_swarm.fitness.coher import coher
from adaptation_swarm.fitness.costt import costt
from adaptation_swarm.fitness.fitness import FitnessBreakdown, FitnessWeights, evaluate
from adaptation_swarm.fitness.redund import redund
from adaptation_swarm.gold.rubric import predicted_dominant
from adaptation_swarm.metrics.pso_diagnostics import cycle_diagnostics, swarm_diagnostics
from adaptation_swarm.metrics.cycle import CycleMetrics, comm_overhead_ms, inflight_overlap, parallel_overlap
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.multimodal.package import MultimodalPackage, assemble
from adaptation_swarm.multimodal.validation import validate_package
from adaptation_swarm.profiles.models import ModalityWeights, ProfileRequest
from adaptation_swarm.pso import engine
from adaptation_swarm.pso.decode import decode
from adaptation_swarm.pso.params import PSOParams
from adaptation_swarm.pso.rng import make_rng
from adaptation_swarm.pso.space import Configuration
from adaptation_swarm.schemas.errors import BusError, CycleFailedError, SwarmError
from adaptation_swarm.schemas.ids import derive_seed, new_id
from adaptation_swarm.schemas.messages import AgentId, BusMessage, MessageType
from adaptation_swarm.schemas.states import CycleStatus, StopReason

log = logging.getLogger(__name__)


@dataclass
class CycleResult:
    cycle_id: str
    correlation_id: str
    profile_id: str
    concept_id: str
    status: str
    stop_reason: str
    k_stop: int | None
    t_conv_ms: float | None
    total_ms: float
    seed: int
    config_hash: str
    library_version: str
    W: dict[str, float] | None = None
    g_best_x: list[float] | None = None
    g_best_S: list[int] | None = None
    g_best_F: float | None = None
    g_best_breakdown: dict[str, float] | None = None
    predicted_dominant: str | None = None
    heuristic_seeded: bool = True
    replicate: int = 0
    pso_diagnostics: dict | None = None
    log_messages: list = field(default_factory=list, repr=False)   # log del bus (para persistencia asíncrona)
    package: dict[str, Any] | None = None
    iterations: list[dict[str, Any]] = field(default_factory=list)
    metrics: CycleMetrics | None = None
    error: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id, "correlation_id": self.correlation_id, "profile_id": self.profile_id,
            "concept_id": self.concept_id, "status": self.status, "stop_reason": self.stop_reason,
            "k_stop": self.k_stop, "t_conv_ms": self.t_conv_ms, "total_ms": self.total_ms, "seed": self.seed,
            "config_hash": self.config_hash, "library_version": self.library_version, "W": self.W,
            "g_best": {"x": self.g_best_x, "S": self.g_best_S, "F": self.g_best_F, "breakdown": self.g_best_breakdown},
            "predicted_dominant": self.predicted_dominant, "package": self.package,
            "metrics": self.metrics.to_dict() if self.metrics else None, "error": self.error,
        }


class SwarmOrchestrator(SwarmAgent):
    agent_id = AgentId.AG0

    def __init__(self, bus, store: LibraryStore, *, params: PSOParams | None = None,
                 fitness_weights: FitnessWeights | None = None, repository=None,
                 request_timeout: float | None = None, consumer: str | None = None):
        super().__init__(bus, consumer)
        self.store = store
        self.params = params or PSOParams()
        self.fw = fitness_weights or FitnessWeights()
        self.repository = repository
        self.request_timeout = request_timeout or SETTINGS.request_timeout_seconds
        self.instance = new_id()[:12]                       # identifica a ESTA instancia de AG0 (multiproceso)
        self._waiters: dict[tuple[str, str, str], asyncio.Future] = {}
        self._collector: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._cycles: dict[str, dict[str, Any]] = {}     # cachés y memoria de trabajo por ciclo
        self._costtable = store.calibration()
        self._validation_memo: dict[tuple, Any] = {}
        from adaptation_swarm.graph.cycle_graph import build_cycle_graph
        self.graph = build_cycle_graph(self)

    # ── ciclo de vida ────────────────────────────────────────────────────
    async def start(self) -> None:
        for a in AgentId:
            await self.bus.ensure_group(a)
        await self.bus.ensure_group(AgentId.AG0, self.instance)      # stream privado de respuestas de esta instancia
        self._stop.clear()
        self._collector = asyncio.create_task(self._collect())

    async def close(self) -> None:
        self._stop.set()
        if self._collector:
            await self._collector
            self._collector = None

    async def _collect(self) -> None:
        pending = True
        while not self._stop.is_set():
            try:
                entries = await self.bus.read(AgentId.AG0, self.consumer, pending=pending, instance=self.instance)
            except BusError as exc:
                self._fail_all(exc)
                await asyncio.sleep(0.5)
                continue
            except Exception as exc:
                log.warning("AG0 colector: %s", exc)
                continue
            pending = False
            for entry_id, msg in entries:
                self._route(msg)
                await self.bus.ack(AgentId.AG0, entry_id, self.instance)

    def _route(self, msg: BusMessage) -> None:
        if msg.message_type is MessageType.ERROR:
            for (cyc, rk, _t), fut in list(self._waiters.items()):
                if cyc == msg.cycle_id and rk == msg.request_key and not fut.done():
                    fut.set_exception(CycleFailedError(f"{msg.sender.value}: {msg.error}"))
            return
        fut = self._waiters.get((msg.cycle_id, msg.request_key or "", msg.message_type.value))
        if fut is not None and not fut.done():
            fut.set_result(msg)

    def _fail_all(self, exc: Exception) -> None:
        for fut in self._waiters.values():
            if not fut.done():
                fut.set_exception(exc)

    async def handle(self, msg: BusMessage) -> list[BusMessage]:  # AG0 no atiende peticiones
        raise SwarmError("AG0 no maneja peticiones entrantes")

    # ── petición/respuesta por el bus ────────────────────────────────────
    async def request(self, *, cycle_id: str, correlation_id: str, receiver: AgentId, mtype: MessageType,
                      payload: dict[str, Any], request_key: str, expect: list[MessageType],
                      iteration: int | None = None) -> dict[MessageType, BusMessage]:
        futures = {}
        for t in expect:
            fut = asyncio.get_running_loop().create_future()
            self._waiters[(cycle_id, request_key, t.value)] = fut
            futures[t] = fut
        try:
            await self.bus.publish(BusMessage(
                correlation_id=correlation_id, cycle_id=cycle_id, sender=AgentId.AG0, receiver=receiver,
                message_type=mtype, iteration=iteration, request_key=request_key, instance=self.instance,
                payload=payload))
            done = await asyncio.wait_for(asyncio.gather(*futures.values()), timeout=self.request_timeout)
        except asyncio.TimeoutError as exc:
            raise CycleFailedError(f"timeout esperando {expect} de {receiver.value} ({request_key})") from exc
        finally:
            for t in expect:
                self._waiters.pop((cycle_id, request_key, t.value), None)
        return dict(zip(expect, done))

    async def request_batch(self, *, cycle_id: str, correlation_id: str, iteration: int | None,
                            specs: list[tuple[str, AgentId, MessageType, dict, list[MessageType]]]
                            ) -> list[dict[MessageType, BusMessage]]:
        """Publica TODAS las peticiones de una iteración en un solo pipeline (llegan en paralelo a AG2/AG3/AG4)
        y espera sus respuestas. Mismas garantías que `request`: errores y timeouts explícitos."""
        loop = asyncio.get_running_loop()
        waiting: list[list[tuple[MessageType, asyncio.Future]]] = []
        keys: list[tuple[str, str, str]] = []
        owners: dict[tuple[str, str, str], AgentId] = {}
        msgs: list[BusMessage] = []
        for request_key, receiver, mtype, payload, expect in specs:
            futs = []
            for t in expect:
                fut = loop.create_future()
                k = (cycle_id, request_key, t.value)
                self._waiters[k] = fut
                keys.append(k)
                owners[k] = receiver
                futs.append((t, fut))
            waiting.append(futs)
            msgs.append(BusMessage(
                correlation_id=correlation_id, cycle_id=cycle_id, sender=AgentId.AG0, receiver=receiver,
                message_type=mtype, iteration=iteration, request_key=request_key, instance=self.instance,
                payload=payload))
        try:
            await self.bus.publish_many(msgs)
            done = await asyncio.wait_for(
                asyncio.gather(*(f for futs in waiting for _t, f in futs)), timeout=self.request_timeout)
        except asyncio.TimeoutError as exc:
            missing = sorted({f"{owners[k].value} ({k[1]})" for k in keys
                              if k in self._waiters and (not self._waiters[k].done() or self._waiters[k].cancelled())})
            raise CycleFailedError(f"timeout esperando respuestas de {', '.join(missing[:4])}") from exc
        finally:
            for k in keys:
                self._waiters.pop(k, None)
        out, i = [], 0
        for futs in waiting:
            out.append({t: done[i + j] for j, (t, _f) in enumerate(futs)})
            i += len(futs)
        return out

    # ── pasos del grafo ──────────────────────────────────────────────────
    async def step_receive(self, st: dict) -> dict:
        profile = ProfileRequest.model_validate(st["profile"])      # RF01
        cycle_id = st.get("cycle_id") or new_id()
        self._cycles[cycle_id] = {"pieces": {}, "scores": {}}
        await self.bus.set_state(cycle_id, {"status": CycleStatus.RUNNING.value, "profile_id": profile.profile_id,
                                            "seed": st["seed"], "library_version": self.store.version})
        return {"cycle_id": cycle_id, "status": CycleStatus.RUNNING.value, "profile": profile.model_dump(mode="json"),
                "iteration_log": [], "t_start_ns": time.perf_counter_ns()}

    async def step_profile(self, st: dict) -> dict:
        rep = await self.request(
            cycle_id=st["cycle_id"], correlation_id=st["correlation_id"], receiver=AgentId.AG1,
            mtype=MessageType.PROFILE_REQUEST, payload={"profile": st["profile"]}, request_key="profile",
            expect=[MessageType.W_READY])
        p = rep[MessageType.W_READY].payload
        return {"W": p["W"], "W_meta": p["generation"], "heuristic_start": p["heuristic_start"]}

    async def step_seed(self, st: dict) -> dict:
        rng = make_rng(st["seed"])
        pso = engine.initialize(self.params, rng, np.array(st["heuristic_start"]))
        return {"pso": pso, "rng": rng, "t_search_ns": time.perf_counter_ns()}

    async def _realize(self, cycle_id: str, correlation_id: str, k: int, concept_id: str,
                       configs: list[Configuration]) -> None:
        cache = self._cycles[cycle_id]["pieces"]
        need: dict[str, tuple[AgentId, MessageType, dict, list[MessageType]]] = {}
        for c in configs:
            vc, vd, vt, va = c.variants
            if f"code:{vc}" not in cache:
                need[f"code:{vc}"] = (AgentId.AG2, MessageType.CODE_REQUEST,
                                      {"concept_id": concept_id, "variant": vc}, [MessageType.CODE_READY])
            if f"diagram:{vc}{vd}" not in cache:
                need[f"diagram:{vc}{vd}"] = (AgentId.AG3, MessageType.DIAGRAM_REQUEST,
                                             {"concept_id": concept_id, "code_variant": vc, "diagram_variant": vd},
                                             [MessageType.DIAGRAM_READY])
            if f"text:{vt}{va}" not in cache:
                need[f"text:{vt}{va}"] = (AgentId.AG4, MessageType.TEXT_REQUEST,
                                          {"concept_id": concept_id, "text_variant": vt, "audio_variant": va},
                                          [MessageType.TEXT_READY, MessageType.AUDIO_READY])
        if not need:
            return
        results = await self.request_batch(cycle_id=cycle_id, correlation_id=correlation_id, iteration=k, specs=[
            (key, recv, mt, pl, exp) for key, (recv, mt, pl, exp) in need.items()])
        for key, res in zip(need, results):
            cache[key] = {t.value: m.payload for t, m in res.items()}

    def _scores(self, cycle_id: str, anchor, c: Configuration) -> tuple[float, float, float]:
        vc, vd, vt, va = c.variants
        memo = self._cycles[cycle_id]["scores"]
        if c.variants not in memo:
            pieces = self._cycles[cycle_id]["pieces"]
            code, diagram = pieces[f"code:{vc}"]["CODE_READY"], pieces[f"diagram:{vc}{vd}"]["DIAGRAM_READY"]
            text = pieces[f"text:{vt}{va}"]["TEXT_READY"]
            if diagram["derived_from"] != code["sha256"]:
                raise CycleFailedError("cadena de hashes rota: diagrama ↔ código")
            memo[c.variants] = (
                coher(anchor, code["code"], diagram["mermaid"], text["text"]).value,
                redund(anchor, code["code"], diagram["mermaid"], text["text"]),
                costt(c.variants, self._costtable),
            )
        return memo[c.variants]

    async def step_evaluate(self, st: dict) -> dict:
        t0 = time.perf_counter()
        ps: engine.PSOState = st["pso"]
        concept_id = st["profile"]["concept_id"]
        anchor = self.store.anchor(concept_id)
        W = ModalityWeights(**st["W"]).by_modality()
        configs = [Configuration(tuple(int(v) for v in row)) for row in ps.decoded()]
        await self._realize(st["cycle_id"], st["correlation_id"], ps.k, concept_id, configs)
        F, parts = [], []
        for c in configs:
            co, re_, ct = self._scores(st["cycle_id"], anchor, c)
            b = evaluate(c, W, co, re_, ct, self.fw)
            F.append(b.F)
            parts.append(b)
        prev = ps.gbest_F_history[-1] if ps.gbest_F_history else None
        engine.register(ps, np.array(F))
        recs = []
        for r, b in zip(ps.records(), parts):
            d = r.to_dict()
            d["breakdown"] = b.to_dict()
            recs.append(d)
        entry = {"k": ps.k, "gbest_F": ps.gbest_F, "delta_F": None if prev is None else abs(ps.gbest_F - prev),
                 "gbest_S": list(ps.gbest_S()), "t_iter_ms": (time.perf_counter() - t0) * 1000.0, "particles": recs,
                 "diagnostics": {**swarm_diagnostics(ps.x, ps.decoded(), np.array(F)),
                                 "pbest_updates": ps.pbest_updates[-1], "gbest_updated": ps.gbest_updates[-1]}}
        await self.bus.set_state(st["cycle_id"], {"k": ps.k, "gbest_F": ps.gbest_F, "gbest_S": list(ps.gbest_S()),
                                                  "status": CycleStatus.RUNNING.value})
        for agent in (AgentId.AG1, AgentId.AG2, AgentId.AG3, AgentId.AG4):     # AG0 retroalimenta con g_best
            await self.bus.publish(BusMessage(
                correlation_id=st["correlation_id"], cycle_id=st["cycle_id"], sender=AgentId.AG0, receiver=agent,
                message_type=MessageType.GBEST_BROADCAST, iteration=ps.k,
                payload={"k": ps.k, "gbest_F": ps.gbest_F, "gbest_S": list(ps.gbest_S())}))
        st["iteration_log"].append(entry)
        return {"iteration_log": st["iteration_log"]}

    def route_after_evaluate(self, st: dict) -> str:
        reason = engine.check_stop(st["pso"])
        if reason is None:
            return "advance"
        return "finalize"

    async def step_advance(self, st: dict) -> dict:
        engine.advance(st["pso"], st["rng"])
        return {}

    async def step_finalize(self, st: dict) -> dict:
        ps: engine.PSOState = st["pso"]
        reason = engine.check_stop(ps)
        t_conv_ms = (time.perf_counter_ns() - st["t_search_ns"]) / 1e6
        S_star = decode(ps.gbest_x)
        vc, vd, vt, va = S_star.variants
        pieces = self._cycles[st["cycle_id"]]["pieces"]
        code, diagram = pieces[f"code:{vc}"]["CODE_READY"], pieces[f"diagram:{vc}{vd}"]["DIAGRAM_READY"]
        text, audio = pieces[f"text:{vt}{va}"]["TEXT_READY"], pieces[f"text:{vt}{va}"]["AUDIO_READY"]
        concept_id = st["profile"]["concept_id"]
        self.store.audio(concept_id, vt, va, load=True)          # el archivo de audio existe y su sha256 coincide
        pkg: MultimodalPackage = assemble(
            cycle_id=st["cycle_id"], concept_id=concept_id, library_version=self.store.version, S=S_star.vector,
            code={"content_id": code["content_id"], "sha256": code["sha256"], "concept_id": concept_id,
                  "variant": vc, "source": code["code"], "cpp": code.get("cpp")},
            diagram={"content_id": diagram["content_id"], "sha256": diagram["sha256"], "concept_id": concept_id,
                     "derived_from": diagram["derived_from"], "variant": vd, "mermaid": diagram["mermaid"],
                     "svg": diagram.get("svg")},
            text={"content_id": text["content_id"], "sha256": text["sha256"], "concept_id": concept_id,
                  "variant": vt, "text": text["text"]},
            audio={"content_id": audio["content_id"], "sha256": audio["sha256"], "concept_id": concept_id,
                   "derived_from": audio["derived_from"], "variant": va, "path": audio["path"],
                   "duration_s": audio["duration_s"], "size_bytes": audio["size_bytes"], "provider": audio["provider"]},
        )
        cyc_diag = cycle_diagnostics(st["iteration_log"], ps.pbest_updates, ps.gbest_updates, ps.first_gbest_change_k)
        validation = self._validate_package(pkg.to_dict())
        if not validation.valid:      # un paquete con una modalidad ausente/inválida NO se entrega
            raise CycleFailedError(f"paquete inválido: {validation.errors[:3]}")
        b = evaluate(S_star, ModalityWeights(**st["W"]).by_modality(),
                     *self._scores(st["cycle_id"], self.store.anchor(concept_id), S_star), self.fw)
        return {
            "status": CycleStatus.COMPLETED.value, "stop_reason": reason.value, "k_stop": ps.k,
            "t_conv_ms": t_conv_ms, "package": {**pkg.to_dict(), "validation": validation.to_dict()},
            "pso_diagnostics": cyc_diag, "g_best": {"x": ps.gbest_x.tolist(),
            "S": list(S_star.vector), "F": ps.gbest_F, "breakdown": b.to_dict(),
            "predicted_dominant": predicted_dominant(S_star.emphasis)},
        }

    def _validate_package(self, pkg: dict):
        """Validación común del paquete (memoizada por las piezas: los artefactos de la biblioteca son inmutables)."""
        key = tuple(pkg[m]["content_id"] for m in ("code", "diagram", "text", "audio"))
        hit = self._validation_memo.get(key)
        if hit is None:
            hit = self._validation_memo[key] = validate_package(pkg, self.store)
        return hit

    async def step_fail(self, st: dict) -> dict:
        return {"status": CycleStatus.FAILED.value, "stop_reason": StopReason.ERROR.value}

    async def step_persist(self, st: dict) -> dict:
        """Espeja el estado final en Redis (memoria compartida). Si Redis no está disponible el fallo ya
        quedó en `st["error"]` y el resultado del ciclo lo reporta: aquí no se enmascara ni se relanza."""
        try:
            await self.bus.set_state(st["cycle_id"], {"status": st["status"], "stop_reason": st.get("stop_reason"),
                                                      "k_stop": st.get("k_stop")})
        except BusError as exc:
            log.warning("persist: no se pudo espejar el estado final en Redis: %s", exc)
        return {}

    # ── API pública ──────────────────────────────────────────────────────
    async def run_cycle(self, profile: ProfileRequest | dict, *, batch_seed: int = 0, replicate: int = 0,
                        correlation_id: str | None = None) -> CycleResult:
        prof = profile if isinstance(profile, ProfileRequest) else ProfileRequest.model_validate(profile)
        seed = derive_seed(batch_seed, prof.profile_id, replicate)
        cycle_id = new_id()
        corr = correlation_id or new_id()
        t0 = time.perf_counter()
        final = await self.graph.ainvoke(
            {"cycle_id": cycle_id, "correlation_id": corr, "profile": prof.model_dump(mode="json"), "seed": seed,
             "library_version": self.store.version, "status": CycleStatus.RUNNING.value},
            config={"recursion_limit": 200})
        total_ms = (time.perf_counter() - t0) * 1000.0
        cycle_id = final.get("cycle_id", cycle_id)
        try:
            log_msgs = await self.bus.read_log(cycle_id)
        except BusError:
            log_msgs = []
        gb = final.get("g_best") or {}
        metrics = CycleMetrics(
            cycle_id=cycle_id, correlation_id=corr, profile_id=prof.profile_id, status=final["status"],
            stop_reason=final.get("stop_reason", StopReason.ERROR.value), k_stop=final.get("k_stop"),
            t_conv_ms=final.get("t_conv_ms"), total_ms=total_ms, gbest_F=gb.get("F"), n_messages=len(log_msgs),
            comm_overhead_ms=comm_overhead_ms(log_msgs) if log_msgs else None,
            parallel_overlap=parallel_overlap(log_msgs) if log_msgs else None,
            inflight_overlap=inflight_overlap(log_msgs) if log_msgs else None)
        result = CycleResult(
            cycle_id=cycle_id, correlation_id=corr, profile_id=prof.profile_id, concept_id=prof.concept_id,
            status=final["status"], stop_reason=final.get("stop_reason", StopReason.ERROR.value),
            k_stop=final.get("k_stop"), t_conv_ms=final.get("t_conv_ms"), total_ms=total_ms, seed=seed,
            config_hash=self.params.config_hash(), library_version=self.store.version, W=final.get("W"),
            g_best_x=gb.get("x"), g_best_S=gb.get("S"), g_best_F=gb.get("F"), g_best_breakdown=gb.get("breakdown"),
            predicted_dominant=gb.get("predicted_dominant"), package=final.get("package"),
            iterations=final.get("iteration_log", []), pso_diagnostics=final.get("pso_diagnostics"), metrics=metrics, error=final.get("error"), replicate=replicate,
            log_messages=log_msgs)
        if self.repository is not None:
            await self.repository.save_cycle(result, log_msgs)
        self._cycles.pop(cycle_id, None)
        return result
