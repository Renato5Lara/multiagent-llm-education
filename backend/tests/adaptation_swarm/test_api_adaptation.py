"""Endpoint HTTP `POST /api/adaptation` (seguro por defecto, Redis+Postgres reales)."""

import os

import httpx
import pytest

import adaptation_swarm.api.router as router_mod
from app.main import app

pytestmark = pytest.mark.integration
KEY = "test-key-123"


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setenv("SWARM_API_KEY", KEY)
    monkeypatch.setenv("SWARM_API_PERSIST", "0")            # este test no ensucia la BD; la persistencia se prueba aparte
    monkeypatch.setenv("SWARM_REDIS_PREFIX", "swarm-apitest:")
    router_mod._stack = None
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c
    await router_mod.shutdown_stack()
    if router_mod._stack is None:
        from adaptation_swarm.bus.redis_bus import RedisBus
        b = await RedisBus(prefix="swarm-apitest:").connect()
        await b.purge_prefix()
        await b.close()


async def test_endpoint_is_disabled_without_key_configured(monkeypatch, slice_profile):
    monkeypatch.delenv("SWARM_API_KEY", raising=False)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/api/adaptation", json=slice_profile.model_dump(mode="json"))
    assert r.status_code == 503


async def test_wrong_or_missing_key_is_rejected(client, slice_profile):
    body = slice_profile.model_dump(mode="json")
    assert (await client.post("/api/adaptation", json=body)).status_code == 401
    assert (await client.post("/api/adaptation", json=body, headers={"X-Swarm-Key": "x"})).status_code == 401


@pytest.mark.requires_library_audio
async def test_adaptation_returns_complete_multimodal_package(client, slice_profile):
    r = await client.post("/api/adaptation?batch_seed=20260923", json=slice_profile.model_dump(mode="json"),
                          headers={"X-Swarm-Key": KEY})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["status"] == "completed" and out["stop_reason"] in ("epsilon", "k_max") and out["k_stop"] <= 15
    pkg = out["package"]
    assert pkg["chain_valid"] and pkg["code"]["source"] and pkg["diagram"]["mermaid"] and pkg["text"]["text"]
    assert pkg["audio"]["url"].startswith("/api/adaptation/audio/")
    assert out["metrics"]["k_stop"] == out["k_stop"] and out["metrics"]["t_conv_ms"] > 0
    audio = await client.get(pkg["audio"]["url"], headers={"X-Swarm-Key": KEY})
    assert audio.status_code == 200 and audio.headers["content-type"] == "audio/mpeg" and len(audio.content) > 10_000


async def test_invalid_profile_is_422(client):
    r = await client.post("/api/adaptation", json={"profile_id": "x", "nivel": 5}, headers={"X-Swarm-Key": KEY})
    assert r.status_code == 422


async def test_unknown_audio_is_404_and_health_reports_agents(client):
    assert (await client.get("/api/adaptation/audio/no-existe", headers={"X-Swarm-Key": KEY})).status_code == 404
    h = await client.get("/api/adaptation/health", headers={"X-Swarm-Key": KEY})
    assert h.status_code == 200 and h.json()["redis"] == "ok" and set(h.json()["agents"]) == {"AG0", "AG1", "AG2", "AG3", "AG4"}


@pytest.mark.requires_library_audio
async def test_package_exposes_svg_and_cpp_when_the_library_has_them(client, slice_profile, store):
    r = await client.post("/api/adaptation?batch_seed=20260923", json=slice_profile.model_dump(mode="json"), headers={"X-Swarm-Key": KEY})
    pkg = r.json()["package"]
    assert pkg["validation"]["valid"] is True
    if store.svg(slice_profile.concept_id, pkg["code"]["variant"], pkg["diagram"]["variant"]) is not None:
        url = pkg["diagram"]["svg"]["url"]
        svg = await client.get(url, headers={"X-Swarm-Key": KEY})
        assert svg.status_code == 200 and svg.headers["content-type"] == "image/svg+xml" and svg.content.startswith(b"<svg")
    if store.cpp(slice_profile.concept_id, pkg["code"]["variant"]) is not None:
        assert "int main" in pkg["code"]["cpp"]["source"]
