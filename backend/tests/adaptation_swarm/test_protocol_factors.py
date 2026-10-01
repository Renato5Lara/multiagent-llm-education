"""Factores experimentales de OE3 (`protocol.py`): cada nivel es una variante REAL del mismo ciclo (Redis real, biblioteca real, sin mocks).

Invariantes que protegen las corridas históricas y la validez del diseño experimental:
  · el protocolo por defecto reproduce el comportamiento histórico (misma salida con la misma semilla);
  · cambiar solo el protocolo de comunicación (despacho, difusión de g_best) NO cambia la trayectoria del PSO: cambia el tráfico y el tiempo, no la solución;
  · el nivel «sequential» elimina el solapamiento de peticiones en vuelo (RF03) y el nivel «batch» lo conserva;
  · `heuristic_seed=False` y el mecanismo de enjambre sí cambian el arranque / la dinámica del PSO.
"""

import uuid

import pytest

from adaptation_swarm.protocol import ProtocolConfig
from adaptation_swarm.pso.params import PSOParams
from adaptation_swarm.schemas.messages import MessageType
from adaptation_swarm.stack import SwarmStack

pytestmark = [pytest.mark.integration, pytest.mark.requires_library_audio]
SEED = 20260923


async def _run(store, profile, **kw):
    s = SwarmStack(library_version=store.version, prefix=f"swarm-test-{uuid.uuid4().hex[:8]}:", **kw)
    async with s:
        try:
            return await s.orchestrator.run_cycle(profile, batch_seed=SEED)
        finally:
            await s.bus.purge_prefix()


def test_protocol_validation_and_defaults():
    assert ProtocolConfig().to_dict() == {"dispatch": "batch", "broadcast_gbest": True, "heuristic_seed": True}
    with pytest.raises(ValueError):
        ProtocolConfig(dispatch="otro")
    with pytest.raises(ValueError):
        SwarmStack(replicas=0)


async def test_default_protocol_reproduces_historical_behaviour(store, slice_profile):
    a = await _run(store, slice_profile)
    b = await _run(store, slice_profile, protocol=ProtocolConfig(), replicas=1)
    assert (a.g_best_S, a.g_best_F, a.k_stop) == (b.g_best_S, b.g_best_F, b.k_stop)
    assert a.heuristic_seeded is True and a.metrics.inflight_overlap is True


async def test_sequential_dispatch_changes_traffic_not_solution(store, slice_profile):
    batch = await _run(store, slice_profile)
    seq = await _run(store, slice_profile, protocol=ProtocolConfig(dispatch="sequential"))
    assert seq.status == "completed" and (seq.g_best_S, seq.g_best_F, seq.k_stop) == (batch.g_best_S, batch.g_best_F, batch.k_stop)
    assert batch.metrics.inflight_overlap is True and seq.metrics.inflight_overlap is False
    assert seq.package["chain_valid"]


async def test_gbest_broadcast_can_be_disabled(store, slice_profile):
    on = await _run(store, slice_profile)
    off = await _run(store, slice_profile, protocol=ProtocolConfig(broadcast_gbest=False))
    kinds_on = {m.message_type for m in on.log_messages}
    kinds_off = {m.message_type for m in off.log_messages}
    assert MessageType.GBEST_BROADCAST in kinds_on and MessageType.GBEST_BROADCAST not in kinds_off
    assert off.metrics.n_messages < on.metrics.n_messages
    assert (off.g_best_S, off.g_best_F, off.k_stop) == (on.g_best_S, on.g_best_F, on.k_stop)


async def test_heuristic_seed_off_starts_all_particles_random(store, slice_profile):
    r = await _run(store, slice_profile, protocol=ProtocolConfig(heuristic_seed=False))
    assert r.status == "completed" and r.heuristic_seeded is False
    assert not any(p["heuristic_seed"] for p in r.iterations[0]["particles"])


async def test_swarm_mechanism_is_controlled_by_pso_coefficients(store, slice_profile):
    full = await _run(store, slice_profile)
    cognitive = await _run(store, slice_profile, params=PSOParams(c2=0.0))
    social = await _run(store, slice_profile, params=PSOParams(c1=0.0))
    assert cognitive.status == social.status == "completed"
    assert cognitive.config_hash != full.config_hash != social.config_hash


async def test_agent_replicas_start_extra_consumers(store, slice_profile):
    s = SwarmStack(library_version=store.version, prefix=f"swarm-test-{uuid.uuid4().hex[:8]}:", replicas=2)
    async with s:
        try:
            assert len(s.agents) == 8 and len({a.consumer for a in s.agents}) == 8
            r = await s.orchestrator.run_cycle(slice_profile, batch_seed=SEED)
            assert r.status == "completed"
        finally:
            await s.bus.purge_prefix()
