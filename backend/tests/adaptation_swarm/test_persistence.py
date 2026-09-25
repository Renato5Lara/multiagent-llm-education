"""Persistencia real en PostgreSQL y trazabilidad completa profile → ciclo → iteración → partícula →
agente → paquete (RF06, RF05). Requiere Postgres y Redis reales."""

import uuid

import pytest
from sqlalchemy import func, select, text

from adaptation_swarm.persistence.repository import PostgresCycleRepository
from adaptation_swarm.stack import SwarmStack
from app.db.session import SessionLocal
from app.models.swarm_adaptation import (
    AgentMessage, MultimodalCandidate, MultimodalPackage, SwarmCycle, SwarmIteration, SwarmProfile,
)
from tests.adaptation_swarm.conftest import WHILE_ID

pytestmark = pytest.mark.integration


@pytest.fixture
def repo(store, profiles, slice_profile):
    label = f"test-{uuid.uuid4().hex[:8]}"
    r = PostgresCycleRepository(run_label=label)
    r.start_run(label, batch_seed=1, config={"t": 1}, config_hash="h", dataset_version="v1", library_version=store.version)
    yield r
    r.delete_run(label)


def test_migration_head_and_tables_exist():
    with SessionLocal() as s:
        assert s.execute(text("select version_num from alembic_version")).scalar() == "b2f4c9d10a02"
        names = {t for (t,) in s.execute(text("select tablename from pg_tables where schemaname='public'"))}
    assert {"swarm_runs", "swarm_profiles", "swarm_cycles", "swarm_iterations", "agent_messages",
            "multimodal_candidates", "multimodal_packages", "sus_participants", "sus_responses", "gold_panel_ratings"} <= names


async def test_cycle_is_persisted_and_fully_reconstructible(store, slice_profile, repo):
    repo.save_profiles([slice_profile], "v1")
    repo.sync_library(store)
    async with SwarmStack(library_version=store.version, prefix=f"swarm-test-{uuid.uuid4().hex[:8]}:", repository=repo) as st:
        r = await st.orchestrator.run_cycle(slice_profile, batch_seed=7)
        await st.bus.purge_prefix()
    assert r.status == "completed"
    with SessionLocal() as s:
        cyc = s.get(SwarmCycle, r.cycle_id)
        assert (cyc.status, cyc.stop_reason, cyc.k_stop) == ("completed", r.stop_reason, r.k_stop)
        assert cyc.t_conv_ms == pytest.approx(r.t_conv_ms) and cyc.seed == str(r.seed) and cyc.correlation_id == r.correlation_id
        assert s.scalar(select(func.count()).select_from(SwarmIteration).where(SwarmIteration.cycle_id == r.cycle_id)) == r.k_stop + 1
        assert s.scalar(select(func.count()).select_from(AgentMessage).where(AgentMessage.cycle_id == r.cycle_id)) == r.metrics.n_messages
        pkg = s.scalars(select(MultimodalPackage).where(MultimodalPackage.cycle_id == r.cycle_id)).one()
        assert all([pkg.code_content_id, pkg.diagram_content_id, pkg.text_content_id, pkg.audio_content_id]) and pkg.chain_valid
        first = s.scalars(select(SwarmIteration).where(SwarmIteration.cycle_id == r.cycle_id, SwarmIteration.k == 0)).one()
        assert len(first.particles) == 20 and {"x", "v", "S", "F", "pbest_F", "pbest_x", "breakdown"} <= set(first.particles[0])
        assert s.scalar(select(func.count()).select_from(MultimodalCandidate).where(
            MultimodalCandidate.library_version == store.version, MultimodalCandidate.concept_id == WHILE_ID)) == \
            sum(store.coverage(WHILE_ID).values())
    tree = repo.reconstruct(r.cycle_id)                          # cadena completa desde Postgres
    assert tree["profile"]["profile_id"] == slice_profile.profile_id and tree["profile"]["gold_label"] == "diagram"
    assert tree["cycle"]["correlation_id"] == r.correlation_id
    assert [i["k"] for i in tree["iterations"]] == list(range(r.k_stop + 1))
    assert {m["type"] for m in tree["messages"]} >= {"PROFILE_REQUEST", "W_READY", "CODE_READY", "AUDIO_READY"}
    assert set(tree["package"]["pieces"]) == {"code", "diagram", "text", "audio"}
    assert {p["agent"] for p in tree["package"]["pieces"].values()} == {"AG2", "AG3", "AG4"}
    assert tree["package"]["pieces"]["audio"]["provider"] == "openai"


async def test_failed_cycle_is_persisted_with_error_and_without_package(store, slice_profile, repo):
    other = slice_profile.model_copy(update={"concept_id": "concepto-sin-biblioteca"})
    async with SwarmStack(library_version=store.version, prefix=f"swarm-test-{uuid.uuid4().hex[:8]}:", repository=repo) as st:
        r = await st.orchestrator.run_cycle(other, batch_seed=7)
        await st.bus.purge_prefix()
    assert r.status == "failed"
    with SessionLocal() as s:
        cyc = s.get(SwarmCycle, r.cycle_id)
        assert cyc.status == "failed" and cyc.stop_reason == "error" and cyc.error["code"] and cyc.g_best_F is None
        assert s.scalars(select(MultimodalPackage).where(MultimodalPackage.cycle_id == r.cycle_id)).first() is None


async def test_rerunning_same_profile_and_replicate_in_a_run_is_rejected(store, slice_profile, repo):
    from sqlalchemy.exc import IntegrityError
    async with SwarmStack(library_version=store.version, prefix=f"swarm-test-{uuid.uuid4().hex[:8]}:", repository=repo) as st:
        await st.orchestrator.run_cycle(slice_profile, batch_seed=7, replicate=0)
        with pytest.raises(IntegrityError):
            await st.orchestrator.run_cycle(slice_profile, batch_seed=7, replicate=0)     # misma (run, perfil, réplica)
        await st.orchestrator.run_cycle(slice_profile, batch_seed=7, replicate=1)         # otra réplica: válido
        await st.bus.purge_prefix()


def test_profiles_and_library_sync_are_idempotent(store, profiles, repo):
    two = list(profiles.values())[:2]
    n1 = repo.save_profiles(two, "vtest-" + repo.run_label)
    n2 = repo.save_profiles(two, "vtest-" + repo.run_label)
    assert (n1, n2) == (2, 0)
    with SessionLocal() as s:
        s.query(SwarmProfile).filter(SwarmProfile.dataset_version == "vtest-" + repo.run_label).delete()
        s.commit()
