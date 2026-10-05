"""`SWARM_API_N_PARTICLES` (OE4: tamaño del enjambre por celda) llega a la pila REAL que atiende `POST /api/adaptation`. Usa Redis aislado real (sin mocks); sin la variable se conserva la referencia de `PSOParams`."""

import uuid

import pytest

from adaptation_swarm.api import router as api
from adaptation_swarm.pso.params import PSOParams

REF_N = PSOParams().n_particles


@pytest.fixture(autouse=True)
def _clean_router(monkeypatch):
    monkeypatch.setenv("SWARM_API_PERSIST", "0")                                   # sin PostgreSQL: solo se observa la pila
    monkeypatch.setenv("SWARM_REDIS_PREFIX", f"swarm-npart-{uuid.uuid4().hex[:8]}:")
    monkeypatch.setattr(api, "_stack", None)
    monkeypatch.setattr(api, "_lock", None)
    monkeypatch.setattr(api, "_repo", None)
    yield
    monkeypatch.setattr(api, "_stack", None)


async def _observed_n() -> tuple[int, str]:
    stack = await api.get_stack()
    try:
        return stack.orchestrator.params.n_particles, stack.orchestrator.params.config_hash()
    finally:
        await api.shutdown_stack()


async def test_without_the_variable_the_default_configuration_is_kept(monkeypatch):
    monkeypatch.delenv("SWARM_API_N_PARTICLES", raising=False)
    n, h = await _observed_n()
    assert n == REF_N and h == PSOParams().config_hash()


async def test_a_controlled_value_reaches_the_orchestrator_pso_params(monkeypatch):
    monkeypatch.setenv("SWARM_API_N_PARTICLES", "7")
    n, h = await _observed_n()
    assert n == 7 and h != PSOParams().config_hash()                              # N observable y deterministamente distinto en el hash de configuración
    monkeypatch.setenv("SWARM_API_N_PARTICLES", "7")
    assert (await _observed_n()) == (7, h)                                           # determinista


async def test_removing_or_emptying_the_variable_restores_the_default(monkeypatch):
    monkeypatch.setenv("SWARM_API_N_PARTICLES", "30")
    assert (await _observed_n())[0] == 30
    monkeypatch.delenv("SWARM_API_N_PARTICLES")
    assert (await _observed_n())[0] == REF_N
    monkeypatch.setenv("SWARM_API_N_PARTICLES", "")
    assert (await _observed_n())[0] == REF_N


async def test_a_non_integer_value_fails_explicitly_instead_of_being_ignored(monkeypatch):
    monkeypatch.setenv("SWARM_API_N_PARTICLES", "veinte")
    with pytest.raises(ValueError):
        await api.get_stack()
