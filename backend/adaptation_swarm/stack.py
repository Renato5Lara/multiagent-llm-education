"""SwarmStack — arranca AG0..AG4 sobre un bus Redis real (cada agente es una tarea asyncio con su
propio consumidor; en producción podrían ser procesos separados: la única vía de comunicación
es Redis)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from adaptation_swarm.agents.ag0_swarm_orchestrator import SwarmOrchestrator
from adaptation_swarm.agents.ag1_profil_agent import ProfilAgent
from adaptation_swarm.agents.ag2_code_agent import CodeAgent
from adaptation_swarm.agents.ag3_diagram_agent import DiagramAgent
from adaptation_swarm.agents.ag4_text_agent import TextAgent
from adaptation_swarm.bus.redis_bus import RedisBus
from adaptation_swarm.config import SETTINGS
from adaptation_swarm.fitness.fitness import FitnessWeights
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.pso.params import PSOParams


class SwarmStack:
    def __init__(self, *, library_root: Path | None = None, library_version: str | None = None,
                 prefix: str | None = None, params: PSOParams | None = None,
                 fitness_weights: FitnessWeights | None = None, repository=None, redis_url: str | None = None):
        self.store = LibraryStore.open(library_root or SETTINGS.library_root, library_version)
        self.bus = RedisBus(url=redis_url, prefix=prefix)
        self._params, self._fw, self._repo = params, fitness_weights, repository
        self.agents: list = []
        self.orchestrator: SwarmOrchestrator | None = None
        self._tasks: list[asyncio.Task] = []
        self._stop = asyncio.Event()

    async def __aenter__(self) -> "SwarmStack":
        await self.bus.connect()
        self.agents = [ProfilAgent(self.bus), CodeAgent(self.bus, self.store),
                       DiagramAgent(self.bus, self.store), TextAgent(self.bus, self.store)]
        for a in self.agents:
            await a.start()                     # crea el grupo de consumidores antes de aceptar tráfico
        self._tasks = [asyncio.create_task(a.run(self._stop)) for a in self.agents]
        self.orchestrator = SwarmOrchestrator(self.bus, self.store, params=self._params,
                                              fitness_weights=self._fw, repository=self._repo)
        await self.orchestrator.start()
        return self

    async def __aexit__(self, *exc) -> None:
        self._stop.set()
        if self.orchestrator:
            await self.orchestrator.close()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self.bus.close()
