"""Frontera arquitectónica: subsistema independiente del Kernel histórico, cinco agentes reales,
Redis y LangGraph como dependencias efectivas."""

import ast
from pathlib import Path

import adaptation_swarm
from adaptation_swarm.agents.ag0_swarm_orchestrator import SwarmOrchestrator
from adaptation_swarm.agents.ag1_profil_agent import ProfilAgent
from adaptation_swarm.agents.ag2_code_agent import CodeAgent
from adaptation_swarm.agents.ag3_diagram_agent import DiagramAgent
from adaptation_swarm.agents.ag4_text_agent import TextAgent
from adaptation_swarm.schemas.messages import AgentId

PKG = Path(adaptation_swarm.__file__).parent
BACKEND = PKG.parent


def _imports():
    for f in PKG.rglob("*.py"):
        for n in ast.walk(ast.parse(f.read_text())):
            if isinstance(n, ast.Import):
                yield f, [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom) and n.module:
                yield f, [n.module]


def test_does_not_import_the_historic_kernel_or_legacy_agents():
    for f, mods in _imports():
        for m in mods:
            assert not m.startswith("runtime"), (f, m)
            assert not m.startswith("app.agents") and not m.startswith("app.swarm"), (f, m)


def test_five_real_agents_exist_with_distinct_ids():
    classes = {AgentId.AG0: SwarmOrchestrator, AgentId.AG1: ProfilAgent, AgentId.AG2: CodeAgent,
               AgentId.AG3: DiagramAgent, AgentId.AG4: TextAgent}
    for aid, cls in classes.items():
        assert cls.agent_id is aid and callable(cls.handle) and cls.version
    assert len({c.agent_id for c in classes.values()}) == 5


def test_redis_langgraph_and_numpy_are_declared_dependencies():
    req = (BACKEND / "requirements.txt").read_text()
    assert "redis==" in req and "langgraph==" in req and "numpy==" in req
    assert "redis" in (BACKEND.parent / "docker-compose.yml").read_text()
    src = "\n".join(f.read_text() for f in PKG.rglob("*.py"))
    assert "redis.asyncio" in src and "langgraph.graph" in src and "StateGraph" in src


def test_no_kernel_file_was_modified_by_this_subsystem():
    assert not list(PKG.rglob("*runtime*"))
