"""
Smoke test M1 — verifica que LLMService enrichment funciona con la API Key real.

Uso:
    cd backend
    python scripts/smoke_test_m1.py

Salida esperada cuando M1 funciona:
    ✅  LLM activo: prediction_question y reflection_question presentes
    prediction_question: ¿Qué crees que es una base de datos?
    reflection_question: ¿Cómo aplicarías el modelo relacional en un proyecto real?
    explanation[:80]: Imagina que tienes miles de contactos en tu teléfono...

Salida cuando NO hay API Key:
    ⚠  settings.has_openai=False — sistema usará template fallback (prediction=None)
"""

import asyncio
import sys
import os

# Permite ejecutar desde backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.core.config import settings


async def main() -> None:
    print(f"has_openai: {settings.has_openai}")

    if not settings.has_openai:
        print("⚠  settings.has_openai=False — sistema usará template fallback (prediction=None)")
        print("   Agrega OPENAI_API_KEY=sk-... a backend/.env para activar M1.")
        return

    from app.services.module_orchestration_service import ModuleOrchestrationService

    svc = ModuleOrchestrationService()
    blocks = await svc._build_concept_blocks(
        topic="Base de Datos Relacionales",
        concepts=[
            "El modelo relacional organiza datos en tablas con filas y columnas.",
            "Las claves primarias garantizan unicidad de cada registro.",
        ],
        examples_raw=["Ejemplo: tabla Clientes con id, nombre, email."],
        misconceptions_raw=[],
        bloom_target=3,
        orch_id="smoke-test",
    )

    if not blocks:
        print("❌  _build_concept_blocks devolvió lista vacía.")
        return

    b = blocks[0]
    pq = b.get("prediction_question")
    rq = b.get("reflection_question")
    ex = b.get("explanation", "")

    if pq and rq and ex.lower().startswith(("imagina", "¿alguna", "piensa")):
        print("✅  LLM activo: prediction_question y reflection_question presentes")
        print(f"   prediction_question: {pq}")
        print(f"   reflection_question: {rq}")
        print(f"   explanation[:100]:   {ex[:100]}")
    else:
        print("⚠  LLM activo pero contenido inesperado:")
        print(f"   prediction_question: {pq!r}")
        print(f"   reflection_question: {rq!r}")
        print(f"   explanation[:100]:   {ex[:100]!r}")


if __name__ == "__main__":
    asyncio.run(main())
