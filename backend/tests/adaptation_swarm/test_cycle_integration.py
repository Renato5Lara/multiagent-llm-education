"""Integración del ciclo completo: perfil → AG0 (LangGraph) → AG1 → W → PSO → AG2+AG3+AG4 (biblioteca M1,
audio real) → 𝓕 → p_best/g_best → convergencia → MultimodalPackage. Redis REAL; sin mocks."""

import asyncio
import io

import pytest
from mutagen.mp3 import MP3

from adaptation_swarm.agents.ag0_swarm_orchestrator import SwarmOrchestrator
from adaptation_swarm.agents.ag1_profil_agent import ProfilAgent
from adaptation_swarm.agents.ag3_diagram_agent import DiagramAgent
from adaptation_swarm.agents.ag4_text_agent import TextAgent
from adaptation_swarm.bus.redis_bus import RedisBus
from adaptation_swarm.gold.rubric import expected_dominant
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.schemas.errors import BusError
from adaptation_swarm.schemas.ids import sha256_bytes, sha256_text
from adaptation_swarm.schemas.messages import AgentId, BusMessage, MessageType
from adaptation_swarm.stack import SwarmStack
from tests.adaptation_swarm.conftest import WHILE_ID

pytestmark = pytest.mark.integration
SEED = 20260923


@pytest.fixture
async def stack(store):
    import uuid
    s = SwarmStack(library_version=store.version, prefix=f"swarm-test-{uuid.uuid4().hex[:8]}:")
    async with s:
        yield s
        await s.bus.purge_prefix()


@pytest.mark.requires_library_audio
async def test_vertical_slice_end_to_end(stack, slice_profile):
    r = await stack.orchestrator.run_cycle(slice_profile, batch_seed=SEED)
    assert r.status == "completed" and r.stop_reason in ("epsilon", "k_max") and 0 <= r.k_stop <= 15
    assert r.t_conv_ms is not None and r.t_conv_ms > 0 and r.total_ms >= r.t_conv_ms
    assert sum(r.W.values()) == pytest.approx(1.0) and len(r.g_best_x) == 8 and len(r.g_best_S) == 8
    assert r.g_best_breakdown["F"] == pytest.approx(r.g_best_F)
    assert len(r.iterations) == r.k_stop + 1                             # iteraciones 0..k_stop realmente ejecutadas
    # paquete multimodal con las 4 modalidades reales
    p = r.package
    assert p["chain_valid"] and p["concept_id"] == WHILE_ID and len(p["S"]) == 8
    assert p["code"]["source"].count("def ") >= 1 and p["diagram"]["mermaid"].startswith("flowchart")
    assert len(p["text"]["text"].split()) >= 15
    assert p["diagram"]["derived_from"] == p["code"]["sha256"] == sha256_text(p["code"]["source"])
    assert p["audio"]["derived_from"] == p["text"]["sha256"]
    audio = (stack.store.dir / p["audio"]["path"]).read_bytes()
    assert sha256_bytes(audio) == p["audio"]["sha256"] and MP3(io.BytesIO(audio)).info.length > 3      # audio REAL
    # métricas exigidas
    m = r.metrics
    assert m.k_stop == r.k_stop and m.stop_reason == r.stop_reason and m.t_conv_ms == r.t_conv_ms and m.gbest_F == r.g_best_F
    assert m.n_messages > 20 and m.comm_overhead_ms is not None
    # la predicción es la modalidad dominante; el gold de este perfil es 'diagram' (tabla preregistrada)
    assert r.predicted_dominant in ("code", "diagram", "text", "audio")
    assert expected_dominant(slice_profile.archetype, slice_profile.difficulty) == "diagram"


@pytest.mark.requires_library_audio
async def test_langgraph_controls_the_cycle(stack, slice_profile):
    graph = stack.orchestrator.graph
    assert type(graph).__name__ == "CompiledStateGraph"
    nodes = set(graph.get_graph().nodes)
    assert {"receive", "profile", "seed", "evaluate", "advance", "finalize", "fail", "persist"} <= nodes
    r = await stack.orchestrator.run_cycle(slice_profile, batch_seed=SEED)
    assert [it["k"] for it in r.iterations] == list(range(r.k_stop + 1))


@pytest.mark.requires_library_audio
async def test_pbest_and_gbest_are_updated_and_never_worsen(stack, slice_profile):
    r = await stack.orchestrator.run_cycle(slice_profile, batch_seed=SEED)
    best_by_particle: dict[int, float] = {}
    prev_g = -1e9
    for it in r.iterations:
        assert it["gbest_F"] >= prev_g
        prev_g = it["gbest_F"]
        for p in it["particles"]:
            assert p["pbest_F"] >= p["F"] - 1e-12                        # p_best ≥ aptitud actual
            assert p["pbest_F"] >= best_by_particle.get(p["idx"], -1e9)
            best_by_particle[p["idx"]] = p["pbest_F"]
    assert any(p["heuristic_seed"] for p in r.iterations[0]["particles"])
    assert r.iterations[0]["particles"][0]["breakdown"]["simil"] > 0
    assert r.g_best_F == max(p["pbest_F"] for p in r.iterations[-1]["particles"])


@pytest.mark.requires_library_audio
async def test_reproducible_with_fixed_seed(stack, slice_profile):
    a = await stack.orchestrator.run_cycle(slice_profile, batch_seed=SEED)
    b = await stack.orchestrator.run_cycle(slice_profile, batch_seed=SEED)
    assert a.cycle_id != b.cycle_id and a.seed == b.seed
    assert (a.g_best_x, a.g_best_S, a.g_best_F, a.k_stop, a.stop_reason, a.config_hash, a.library_version) == \
        (b.g_best_x, b.g_best_S, b.g_best_F, b.k_stop, b.stop_reason, b.config_hash, b.library_version)
    assert [i["gbest_F"] for i in a.iterations] == [i["gbest_F"] for i in b.iterations]
    assert a.package["package_id"] != b.package["package_id"]           # package_id incluye el cycle_id
    assert (a.package["code"]["sha256"], a.package["audio"]["sha256"]) == (b.package["code"]["sha256"], b.package["audio"]["sha256"])
    c = await stack.orchestrator.run_cycle(slice_profile, batch_seed=SEED + 1)
    assert c.seed != a.seed and [i["particles"][1]["x"] for i in c.iterations][0] != [i["particles"][1]["x"] for i in a.iterations][0]


@pytest.mark.requires_library_audio
async def test_correlation_id_reconstructs_the_whole_cycle(stack, slice_profile):
    r = await stack.orchestrator.run_cycle(slice_profile, batch_seed=SEED, correlation_id="corr-slice-1")
    log = await stack.bus.read_log(r.cycle_id)
    assert log and all(m.cycle_id == r.cycle_id and m.correlation_id == "corr-slice-1" for m in log)
    ids = {m.message_id: m for m in log}
    kinds = [m.message_type for m in log]
    assert kinds.index(MessageType.PROFILE_REQUEST) < kinds.index(MessageType.W_READY) < kinds.index(MessageType.CODE_REQUEST)
    routes = {(m.sender, m.receiver) for m in log}
    for a in (AgentId.AG1, AgentId.AG2, AgentId.AG3, AgentId.AG4):
        assert (AgentId.AG0, a) in routes and (a, AgentId.AG0) in routes      # AG0↔cada agente, por Redis
    for m in log:
        if m.in_reply_to:
            assert m.in_reply_to in ids and ids[m.in_reply_to].sender is AgentId.AG0
    delivered = {m.payload["content_id"] for m in log if m.message_type in (MessageType.CODE_READY, MessageType.DIAGRAM_READY, MessageType.TEXT_READY, MessageType.AUDIO_READY)}
    p = r.package
    assert {p["code"]["content_id"], p["diagram"]["content_id"], p["text"]["content_id"], p["audio"]["content_id"]} <= delivered
    assert (await stack.bus.get_state(r.cycle_id))["status"] == "completed"       # memoria compartida en Redis
    n_stream = 0
    async for key in stack.bus.redis.scan_iter(match=f"{stack.bus.prefix}agent:*"):      # agentes + stream de respuestas de AG0
        n_stream += await stack.bus.redis.xlen(key)
    assert n_stream == r.metrics.n_messages                                       # todo pasó por streams de Redis
    assert r.metrics.inflight_overlap is True                                     # RF03: peticiones concurrentes a agentes distintos


@pytest.mark.requires_library_audio
async def test_gbest_is_broadcast_to_all_agents(stack, slice_profile):
    r = await stack.orchestrator.run_cycle(slice_profile, batch_seed=SEED)
    await asyncio.sleep(0.4)
    assert all(a.gbest_broadcasts == r.k_stop + 1 for a in stack.agents)
    assert all(a.last_gbest["k"] == r.k_stop for a in stack.agents)


async def test_cycle_fails_explicitly_when_redis_bus_is_unavailable(stack, slice_profile):
    live = stack.bus._r
    stack.bus._r = None                                                          # el bus deja de estar disponible
    try:
        r = await stack.orchestrator.run_cycle(slice_profile, batch_seed=SEED)
    finally:
        stack.bus._r = live
    assert r.status == "failed" and r.stop_reason == "error" and r.package is None and r.g_best_F is None
    assert r.error["code"] == "BusError"
    with pytest.raises(BusError):
        await RedisBus(url="redis://localhost:6390/0").connect()                # sin Redis no hay sustituto


async def test_cycle_fails_explicitly_when_an_agent_is_down(store, slice_profile, bus):
    stop = asyncio.Event()
    agents = [ProfilAgent(bus), DiagramAgent(bus, store), TextAgent(bus, store)]       # AG2 (Code-Agent) NO arranca
    for a in agents:
        await a.start()
    tasks = [asyncio.create_task(a.run(stop)) for a in agents]
    orch = SwarmOrchestrator(bus, store, request_timeout=1.5)
    await orch.start()
    r = await orch.run_cycle(slice_profile, batch_seed=SEED)
    stop.set()
    await orch.close()
    await asyncio.gather(*tasks)
    assert r.status == "failed" and r.stop_reason == "error" and r.package is None
    assert "timeout" in r.error["message"] and "AG2" in r.error["message"]


async def test_invalid_profile_is_rejected_before_the_swarm_runs(stack):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        await stack.orchestrator.run_cycle({"profile_id": "x", "nivel": 7})


async def test_missing_library_candidate_ends_in_error_not_in_invented_gbest(stack, slice_profile):
    other = slice_profile.model_copy(update={"concept_id": "concepto-sin-biblioteca"})
    r = await stack.orchestrator.run_cycle(other, batch_seed=SEED)
    assert r.status == "failed" and r.stop_reason == "error" and r.g_best_F is None and r.package is None


@pytest.mark.requires_library_audio
async def test_two_orchestrator_instances_do_not_steal_each_others_replies(store, slice_profile, profiles, bus):
    """Despliegue multiproceso: dos AG0 sobre el MISMO Redis y los MISMOS agentes; cada uno recibe solo las
    respuestas de sus propias peticiones (stream de respuestas por instancia)."""
    stop = asyncio.Event()
    agents = [ProfilAgent(bus), DiagramAgent(bus, store), TextAgent(bus, store)]
    from adaptation_swarm.agents.ag2_code_agent import CodeAgent
    agents.append(CodeAgent(bus, store))
    for a in agents:
        await a.start()
    tasks = [asyncio.create_task(a.run(stop)) for a in agents]
    o1, o2 = SwarmOrchestrator(bus, store), SwarmOrchestrator(bus, store)
    await o1.start()
    await o2.start()
    assert o1.instance != o2.instance
    p2 = profiles["syn-visual_dominant-repetitive-r1"]
    p2 = p2.model_copy(update={"concept_id": WHILE_ID})          # mismo concepto de la biblioteca de prueba
    rs = await asyncio.gather(*(o.run_cycle(p, batch_seed=SEED) for o in (o1, o2) for p in (slice_profile, p2)))
    stop.set()
    await asyncio.gather(o1.close(), o2.close(), *tasks)
    assert all(r.status == "completed" for r in rs)
    assert len({r.cycle_id for r in rs}) == 4


@pytest.mark.requires_library_audio
async def test_many_concurrent_cycles_complete_without_connection_exhaustion(stack, profiles):
    """Regresión de la prueba de carga: con el límite por defecto de redis-py, ≥50 ciclos concurrentes agotaban el
    pool ('Too many connections'), mataban el consumidor de AG3 y dejaban ciclos colgados."""
    plist = [profiles[k].model_copy(update={"concept_id": WHILE_ID}) for k in list(profiles)[:100]]
    sem = asyncio.Semaphore(80)

    async def one(i):
        async with sem:
            return await stack.orchestrator.run_cycle(plist[i % 100], batch_seed=SEED, replicate=i)

    rs = await asyncio.gather(*(one(i) for i in range(160)))
    assert [r.status for r in rs].count("completed") == 160
    assert all(a.failures == 0 for a in stack.agents)


async def test_agent_survives_a_failure_while_processing_one_message(bus, store, slice_profile):
    from adaptation_swarm.schemas.errors import BusError
    agent = ProfilAgent(bus)
    real_publish = bus.publish
    state = {"failed": False}

    async def flaky(msg):
        if msg.message_type is MessageType.W_READY and not state["failed"]:
            state["failed"] = True
            raise BusError("fallo inyectado al publicar la respuesta")
        return await real_publish(msg)

    bus.publish = flaky
    await bus.ensure_group(AgentId.AG0)
    stop = asyncio.Event()
    task = asyncio.create_task(agent.run(stop))
    await asyncio.sleep(0.2)
    for i in range(2):
        await real_publish(BusMessage(correlation_id="c", cycle_id=f"cy{i}", sender=AgentId.AG0, receiver=AgentId.AG1,
                                      message_type=MessageType.PROFILE_REQUEST, request_key="profile",
                                      payload={"profile": slice_profile.model_dump(mode="json")}))
    await asyncio.sleep(1.0)
    alive = not task.done()
    stop.set()
    await task
    assert alive and agent.failures == 1                          # el fallo se registró y el agente siguió vivo
    assert len([m for m in await bus.read_log("cy1") if m.message_type is MessageType.W_READY]) == 1   # sirvió el 2.º
