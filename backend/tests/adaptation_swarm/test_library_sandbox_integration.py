"""Integración (sandbox real): cada variante de código de la biblioteca M1 cumple el comportamiento de referencia. DIFERIDA: el sandbox
crea contenedores podman (`SWARM_SANDBOX_BIN`) y no forma parte del entorno aislado de PostgreSQL + Redis."""

import pytest

from adaptation_swarm.agents.ag2_code_agent import CodeAgent
from tests.adaptation_swarm.conftest import DATASET
from adaptation_swarm.profiles.generator import read_dataset

pytestmark = pytest.mark.integration


def _concepts():
    return {p.concept_id: p.metadata["concept_title"] for p in read_dataset(DATASET)}


async def test_all_code_variants_pass_reference_behavior_in_real_sandbox(store):
    from app.services.cmg_concept_catalog import obtener_plantilla
    ag2 = CodeAgent(None, store)
    for cid, title in _concepts().items():
        tests = obtener_plantilla(title).tests
        for v in range(3):
            status, _ms, detail = await ag2.validate_in_sandbox(store.code(cid, v).text, tests)
            assert status == "success", (title, v, detail)
