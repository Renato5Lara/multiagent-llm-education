"""Consumo de recursos durante las corridas (asesoría §4.3: % CPU, RAM del proceso y memoria de Redis).
`psutil` es dependencia de las pruebas de carga (requirements-loadtest.txt)."""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any

import psutil


async def sample_once(pids: list[int], redis) -> dict[str, Any]:
    procs = []
    for pid in pids:
        try:
            p = psutil.Process(pid)
            procs.append({"pid": pid, "cpu_percent": p.cpu_percent(interval=None), "rss_mb": p.memory_info().rss / 1e6})
        except psutil.Error:
            continue
    info = await redis.info("memory")
    return {
        "t": time.time(), "system_cpu_percent": psutil.cpu_percent(interval=None),
        "system_mem_used_mb": (psutil.virtual_memory().total - psutil.virtual_memory().available) / 1e6,
        "processes": procs, "redis_used_memory_mb": info["used_memory"] / 1e6,
    }


@asynccontextmanager
async def sampler(pids: list[int], redis, interval_s: float = 0.5):
    """Uso:  async with sampler([os.getpid()], bus.redis) as series: ...  → `series` es una lista de muestras."""
    series: list[dict[str, Any]] = []
    stop = asyncio.Event()
    for pid in pids:
        try:
            psutil.Process(pid).cpu_percent(interval=None)          # inicializa el contador
        except psutil.Error:
            pass

    async def loop() -> None:
        while not stop.is_set():
            series.append(await sample_once(pids, redis))
            try:
                await asyncio.wait_for(stop.wait(), timeout=interval_s)
            except asyncio.TimeoutError:
                pass

    task = asyncio.create_task(loop())
    try:
        yield series
    finally:
        stop.set()
        await task


def summarize(series: list[dict[str, Any]]) -> dict[str, Any]:
    if not series:
        return {}
    cpu = [max((p["cpu_percent"] for p in s["processes"]), default=0.0) for s in series]
    rss = [sum(p["rss_mb"] for p in s["processes"]) for s in series]
    return {
        "samples": len(series), "proc_cpu_percent_max": max(cpu), "proc_cpu_percent_mean": sum(cpu) / len(cpu),
        "proc_rss_mb_max": max(rss), "system_cpu_percent_max": max(s["system_cpu_percent"] for s in series),
        "redis_used_memory_mb_max": max(s["redis_used_memory_mb"] for s in series),
    }
