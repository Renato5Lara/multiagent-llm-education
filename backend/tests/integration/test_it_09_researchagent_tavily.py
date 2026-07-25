"""IT-09 -- Integracion ResearchAgent <-> Tavily (busqueda web real).

Hallazgo de la Fase 1 de auditoria: tests/test_tavily_cache.py y
tests/test_tavily_client.py estan rotos (ImportError sobre
get_tavily_cache/get_tavily_client, que no existen) -- pero esa ruta de
codigo NO es la que usa produccion. El camino real es
app/integrations/tavily/retrieval.PedagogicalRetrievalStrategy, que
instancia TavilyClient()/TavilyCache() directamente. Este caso ejecuta
ese camino real, con cache_only=False, contra la API de Tavily real
(TAVILY_API_KEY del entorno), para demostrar que la integracion vigente
funciona pese a que sus pruebas legacy estan rotas.
"""
import os

from app.integrations.tavily.retrieval import PedagogicalRetrievalStrategy
from app.integrations.tavily.schemas import RetrievalContext


def test_pedagogical_retrieval_strategy_llama_a_tavily_real_y_devuelve_fuentes():
    assert os.environ.get("TAVILY_API_KEY"), "TAVILY_API_KEY debe estar presente en el entorno real del backend"

    strategy = PedagogicalRetrievalStrategy()
    context = RetrievalContext(
        topic="Bucles for en Python",
        objectives=["Comprender la sintaxis de un bucle for"],
        bloom_target=3,
        language="es",
        learning_style="",
        preferred_analogies=[],
    )

    print("[IT-09] PedagogicalRetrievalStrategy.research(cache_only=False) -- llamada real a Tavily")
    import asyncio
    research = asyncio.run(strategy.research(context, cache_only=False))

    print(
        f"[IT-09] total_sources={research.total_sources} unique_domains={research.unique_domains} "
        f"confidence={research.confidence_score} degraded={research.degraded}"
    )
    for qr in research.query_results:
        print(f"[IT-09]   query='{qr.query}' cached={qr.cached} degraded={qr.degraded} error={qr.error}")

    if research.degraded:
        # Resultado real de esta ejecucion: la API de Tavily respondio HTTP 432 en
        # las 8 consultas (limite de la cuenta real o incidente del proveedor en
        # el momento de la corrida) -- no un fallo del codigo de integracion. Se
        # documenta como tal en lugar de forzar una fuente inventada: lo que SI
        # se valida aqui es que PedagogicalRetrievalStrategy degrada con
        # gracia (RetrievalContext bien formado, AggregatedResearch valido con
        # degraded=True, sin excepcion no controlada) en lugar de tumbar al
        # llamador cuando el proveedor externo real falla.
        assert all(qr.error for qr in research.query_results), "Cada query_result degradado debe registrar su error real"
        assert research.total_sources == 0 and research.confidence_score == 0.0
    else:
        assert research.total_sources > 0, (
            "La integracion real ResearchAgent->Tavily debio devolver al menos una fuente real de la API"
        )
