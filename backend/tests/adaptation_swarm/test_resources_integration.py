"""Integración (Redis real): muestreo de recursos durante una corrida. Necesita un Redis de pruebas (ver integration_env/README.md) y
`psutil`, que no está en requirements.txt sino en requirements-loadtest.txt: si falta, la prueba se omite."""

import asyncio

import pytest

pytest.importorskip("psutil")
pytestmark = pytest.mark.integration


async def test_resource_sampler_reads_real_process_and_redis_memory(bus):
    import os
    from adaptation_swarm.metrics.resources import sampler, summarize
    async with sampler([os.getpid()], bus.redis, interval_s=0.05) as series:
        await asyncio.sleep(0.3)
    s = summarize(series)
    assert s["samples"] >= 3 and s["proc_rss_mb_max"] > 10 and s["redis_used_memory_mb_max"] > 0.1
    assert 0 <= s["system_cpu_percent_max"] <= 100 * (os.cpu_count() or 1)
